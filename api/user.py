# =============================================================================
# api/user.py —— 用户接口：登录 / 注册 / 批量创建短链
# =============================================================================
# 【它在链路里的位置】
#   登录：POST /api/v1/oauth2/authorize
#      → 按用户名查用户 → bcrypt 校验密码 → 签 JWT 返回 access_token
#      → 之后所有需要登录的接口都在 Header 带 Authorization: Bearer <token>
#
#   注册：POST /api/v1/create/user
#      → 判重 → UserServeries.create_user（内部做 bcrypt 哈希）→ 入库
#
#   批量创建：POST /api/v1/create/batch/short
#      → 上传一个 txt 文件，每行 "渠道名#文案模板#长链接"
#      → 逐行生成短码和文案 → add_all 一次性入库
#
# 【OAuth2PasswordRequestForm 是什么】
#   FastAPI 自带的表单解析器，自动从 form-data 里取 username / password。
#   注意它要求 Content-Type: application/x-www-form-urlencoded，
#   不是 JSON。用 /docs 页面上的 Authorize 按钮测试时，FastAPI 会自动按这个格式发。
#
# ★★ 这段代码里有几个真实 bug，复习时重点看 ★★
#   1) create_batch 里调用了 generate_short_tag()，但文件顶部没有 import 它
#      → NameError: name 'generate_short_tag' is not defined（一调用就炸）
#   2) created_by=username  —— 字段名多了个 d，schemas 里叫 create_by
#      → pydantic v2 默认忽略未知字段，所以这个值被静默丢弃，存进去是空字符串
#   3) user_info.dict() —— Pydantic v1 写法，v2 应该用 model_dump()
#   4) f"http://127.0.0.1:8000{short_tag}" 少了一个斜杠
#      → 生成的地址是 http://127.0.0.1:8000abc12345（错的）
#   5) split_item[2] / split_item[1] 没做长度校验
#      → 文件里某行格式不对就直接 IndexError，整个批量任务挂掉
#   6) 一个函数里混了"登录、批量建链、注册"三件事，职责不清
#      真实项目应该拆成 auth.py（登录注册）+ short.py（建链）
# =============================================================================

from schemas.short import SingleShortUrlCreate
from schemas.user import UserRegister
from servies.short import ShortServices
from utils.auth import AuthTokenHelper
from urllib.request import HTTPErrorProcessor      # 没用到
import datetime

from fastapi import APIRouter, UploadFile, HTTPException
from fastapi.params import Depends, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from requests import status_codes                  # 没用到
from sqlalchemy.ext.asyncio import AsyncSession, result      # result 没用到
from sqlalchemy.sql.operators import add           # 没用到
from starlette.status import HTTP_401_UNAUTHORIZED

from dependencies.dependencies import get_db_session
from servies.user import UserServeries
from utils.password import PasslibHelper

router_user = APIRouter(prefix="/api/v1", tags=["用户创建短链管理"])

# OAuth2PasswordBearer 的两个作用：
#   1) 从请求头 Authorization: Bearer xxx 里取出 token 交给接口
#   2) 在 /docs 生成 Authorize 按钮
# tokenUrl 指向登录接口，点 Authorize 时 /docs 会引导你先去那里拿 token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/oauth2/authorize")


# ---- 登录：校验密码 + 签发 JWT --------------------------------------------
@router_user.post("/oauth2/authorize", summary="登录用户")
async def login(user_data: OAuth2PasswordRequestForm = Depends(),
                db_session: AsyncSession = Depends(get_db_session)):
    if not user_data:
        raise HTTPException(status_code=400, detail="请输入用户账号密码")

    # 先按用户名查人（查不到直接 401，不要提示"密码错"，避免泄露账号是否存在）
    userinfo = await UserServeries.get_user_by_name(db_session, user_data.username)
    if not userinfo:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED,
                            detail="不存在此用户的信息",
                            headers={"WWW-Authenticate": "Basic"})

    # ★ 关键一步：用 bcrypt 校验密码（不是直接比对字符串）
    if not PasslibHelper.verify_password(user_data.password, userinfo.password):
        raise HTTPException(status_code=400, detail="用户密码不对")

    # 校验通过 → 组装 token 内容
    data = {
        'iss': userinfo.username,
        'sub': 'xiaolongtongxue',
        'username': userinfo.username,   # 后面建短链时靠它填 create_by
        'admin': True,                   # ★ 权限写死在 token 里，所有用户都是 admin
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    }
    token = AuthTokenHelper.token_encode(data=data)
    # 返回格式必须是 {"access_token": ..., "token_type": "bearer"}
    # 这是 OAuth2 规范要求的，否则 /docs 的 Authorize 按钮认不出来
    return {"access_token": token, "token_type": "bearer"}


# ---- 批量创建短链（上传 txt 文件）----------------------------------------
@router_user.post("/create/batch/short", summary="通过上传文件方式批量创建短链请求")
async def create_batch(*, file: UploadFile = File(...),
                       token: str = Depends(oauth2_scheme),
                       db_session: AsyncSession = Depends(get_db_session)):
    payload = AuthTokenHelper.token_decode(token=token)
    username = payload.get('username')

    # 读出上传文件内容 → 按行切成列表
    contents = await file.read()
    short_msg = contents.decode(encoding='utf-8').split("\n")

    def make_short_url(item):
        # 每行约定格式：渠道名#文案模板#长链接
        split_item = item.split("#")
        short_tag = generate_short_tag()          # ★ BUG：文件顶部没 import，这里会 NameError
        shoort_url = f"http://127.0.0.1:8000{short_tag}"   # ★ 少了斜杠；变量名也拼错（shoort）

        return SingleShortUrlCreate(
            long_url=split_item[2],                # ★ 没做长度校验，格式错就 IndexError
            short_url=shoort_url,
            short_tag=short_tag,
            created_by=username,                   # ★ 字段名应为 create_by，这个被静默丢弃
            msg_context=f"{split_item[1].replace('channename', split_item[0]).replace('url', 'short_url')}"
        )

    result = await ShortServices.create_batch_short_url(db_session, [make_short_url(item) for item in short_msg])
    return {"code": 200, "msg": "批量创建短链成功", "data": None}


# ---- 注册 ----------------------------------------------------------------
@router_user.post("/create/user", summary="注册用户")
async def create_user(*, user_info: UserRegister, db_session: AsyncSession = Depends(get_db_session)):
    if await UserServeries.get_user_by_name(db_session, user_info.username):
        raise HTTPException(status_code=400, detail="用户已存在")
    # ★ .dict() 是 Pydantic v1 的写法；v2 应该用 .model_dump()
    await UserServeries.create_user(db_session, **user_info.dict())
    return {"code": 200, "msg": "注册成功", "data": None}