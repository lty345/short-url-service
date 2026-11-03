# =============================================================================
# api/short.py —— 短链服务对外的两个接口（跳转 + 创建）
# =============================================================================
# 【它在链路里的位置】
#   创建：POST /create/single/short
#      → 从 token 里取用户名
#      → generate_short_tag() 生成 8 位短码
#      → 拼 short_url 和推广文案
#      → ShortServices.create_short_url 入库
#
#   访问：GET /{short_tag}
#      → ShortServices.get_short_url 按短码查
#      → RedirectResponse 302 跳转到 long_url
#      → BackgroundTasks 异步给访问次数 +1（不阻塞跳转）
#
# 【★ 三个真实问题，复习重点】
#   1) 跳转接口的参数写错了（硬 bug，见下方注释）
#      → 实际永远拿不到用户的短码，跳转必然失败
#   2) 访问计数是先"读出旧值 +1 再写回"，并发时会丢失计数
#      （两个人同时访问，都是读到 5、都写 6，实际应该是 7）
#      正确做法：UPDATE ... SET visit_count = visit_count + 1（交给数据库做原子自增）
#   3) BackgroundTasks 传的是 db_session，但请求结束后 FastAPI 会把会话关掉
#      → 后台任务里用的可能是个已关闭的会话（时序竞争）
# =============================================================================
from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession, result
from starlette.background import BackgroundTasks
from starlette.responses import PlainTextResponse
from starlette.responses import RedirectResponse

from utils.auth import AuthTokenHelper
from api.user import oauth2_scheme
from dependencies.dependencies import get_db_session
from schemas.short import SingleShortUrlCreate
from servies.short import ShortServices
from utils.short import generate_short_tag

router_short = APIRouter(tags=["短链访问"])


# ---- 访问短链：/abc12345 → 302 跳到长链接 ----------------------------------
# 注意这个路由放在 /create/single/short 之前定义很重要：
# 如果 /{short_tag} 在前面，它会把 /create 也当成短码吃掉。
@router_short.get('/{short_tag}')
async def short_redierct(*, short_tag=str, db_session: AsyncSession = Depends(get_db_session), taks: BackgroundTasks):
    # ★★★ 这里的参数有 bug ★★★
    #   short_tag=str 里的 =str 是"默认值"，不是类型标注。
    #   所以不管用户访问 /abc12345 还是 /xyz，这个参数拿到的永远是那个 str 类本身，
    #   而不是路径里的真实短码 → 查库永远查不到 → 永远返回"没有对应的短链记录"。
    #   正确写法：short_tag: str      （用冒号，不要 = 号，也不要前面那个 *）
    #
    #   这个 bug 和聊天室项目 servies/UserServeries.py 里 phone_number=str 是同一类错误：
    #   「把类型对象当默认值」，SQLAlchemy/FastAPI 都不会帮你报错，只会静默用错值。

    data = await ShortServices.get_short_url(db_session, short_tag)
    if not data:
        return PlainTextResponse("没有对应的短链记录")

    # ★ 并发安全问题：先读后写，两个人同时访问会互相覆盖（丢计数）
    data.visit_count += 1
    # 把"更新计数"丢进后台任务：先返回跳转，再慢慢更新数据库
    #   好处：跳转不用等写库，用户体验快
    #   taks 是形参名打错了（应为 tasks），因为位置传参所以不影响运行
    taks.add_task(ShortServices.update_short_url, db_session, short_url_id=data.id, visit_count=data.visit_count)
    # 302 重定向到原始长链接（RedirectResponse 默认就是 307，这里实测是临时跳转）
    return RedirectResponse(data.long_url)


# ---- 创建单条短链（需要登录）----------------------------------------------
@router_short.post("/create/single/short", summary="创建单一短链请求")
async def create_single(create_info: SingleShortUrlCreate,
                        token: str = Depends(oauth2_scheme),
                        db_session: AsyncSession = Depends(get_db_session)):
    # oauth2_scheme 只负责从 Authorization 头把 token 取出来，不验证；
    # 这里手动 decode 才能拿到用户名，并顺便验证签名/过期
    payload = AuthTokenHelper.token_decode(token)
    username = payload.get("username")

    # 服务端生成短码，不信任前端传的
    create_info.short_tag = generate_short_tag()
    # 拼成可直接复制的短链
    create_info.short_url = f"http://127.0.0.1:8000/{create_info.short_tag}"
    create_info.create_by = username
    # 拼推广文案：原来的 msg_context + 附件说明
    create_info.msg_context = f"{create_info.msg_context},欲了解详情，请点击{create_info.short_url}"

    # model_dump() 把 pydantic 对象转 dict，** 展开后正好对应 ShortUrl 的列名
    result = await ShortServices.create_short_url(db_session, **create_info.model_dump())
    return {
        "code": 100,
        "message": "创建成功",
        "data": {"short_url": result.short_url}
    }


# 补充：RedirectResponse 状态码说明
#   302 Found     = 临时跳转（浏览器不缓存，每次都来问服务器）← 短链服务一般都想要这个
#   301 Moved     = 永久跳转（浏览器会缓存，之后直接跳，你就统计不到访问了）
#   307 Temporary = 临时跳转且保持原请求方法（POST 也保持 POST）
#   短链统计场景要用 302/307，不能用 301，否则访问量会越来越不准。