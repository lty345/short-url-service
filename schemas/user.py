# =============================================================================
# schemas/user.py —— 注册请求的数据格式
# =============================================================================
# 【它在链路里的位置】
#   api/user.py 的 create_user(user_info: UserRegister, ...)
#   → FastAPI 校验 body 里有 username 和 password
#   → user_info.dict() 展开传给 UserServeries.create_user
#
# ★ 这里用的是 .dict()，那是 Pydantic v1 的写法。
#   你项目装的是 Pydantic v2，正确方法是 .model_dump()（.dict() 已废弃但还能用）。
#   同一项目的 api/short.py 里用的是 model_dump()，两处风格不统一。
#
# ★ 没有任何约束：密码长度、用户名格式都没校验。
#   实际项目应该写 password: str = Field(min_length=6)。
#   注意：不校验长度还叠加了 models 里 password 列只有 32 位的问题（见 models/model.py）。
# =============================================================================
from pydantic import BaseModel


class UserRegister(BaseModel):
    username: str
    password: str