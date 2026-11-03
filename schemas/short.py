# =============================================================================
# schemas/short.py —— 创建短链请求的数据格式
# =============================================================================
# 【它在链路里的位置】
#   api/short.py 的 create_single(create_info: SingleShortUrlCreate, ...)
#   → FastAPI 用这个类校验请求体
#   → 校验通过后 create_info.model_dump() 展开成 dict，直接喂给 ShortServices.create_short_url
#     （所以这个类的字段名必须和 ShortUrl 表的列名一致）
#
# 【为什么字段都有默认值】
#   long_url 由用户填（必填），其余都由服务端自动生成：
#     short_url / short_tag → utils/short.py 生成
#     create_by            → 从 token 里解出来
#     msg_context          → 用 long_url 拼出来
#   给默认值是为了"构造对象时可以只传 long_url"。
#
# ★ create_by 和 models/model.py 里的列名对不上！
#   schema 里叫 create_by，但 api/short.py 里写的是 create_info.create_by = username，
#   而 model 里也确实叫 create_by —— 这里一致，没问题。
#   但要注意 api/user.py 的批量创建里用的是 created_by（多了个 d）→ 那是另一处 bug。
# =============================================================================
from pydantic import BaseModel


class SingleShortUrlCreate(BaseModel):
    long_url: str                                              # 必填：要缩短的长链接
    short_url: str = "https://127.0.0.1:8000/"                  # 服务端后续会覆盖
    visit_count: int = 0                                        # 初始访问次数
    short_tag: str = ""                                         # 服务端后续会生成
    create_by: str = ""                                         # 服务端后续填入用户名
    msg_context: str = ""                                       # 服务端后续拼装