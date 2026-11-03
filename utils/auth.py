# =============================================================================
# utils/auth.py —— JWT 签发与校验
# =============================================================================
# 【它在链路里的位置】
#   1) 登录：api/user.py 的 login() → token_encode() → 返回 access_token
#   2) 鉴权：api/user.py 的 create_batch() / api/short.py 的 create_single()
#      参数写 token: str = Depends(oauth2_scheme)
#      → FastAPI 自动从 Authorization: Bearer xxx 里取出 token
#      → 手动调 token_decode() 解析出 username
#
# 【和聊天室项目的区别】
#   聊天室：token 只能塞在 URL 参数里（因为浏览器 WebSocket 不支持自定义头）
#   本项目：标准 HTTP 接口，走 Authorization 头，这才是正常姿势。
#   两个项目对照看，能体会"同一套 JWT 在不同场景下怎么传"。
#
# 【OAuth2PasswordBearer 是什么】
#   它是 FastAPI 提供的"鉴权依赖"，作用是：
#     - 自动从请求头 Authorization: Bearer <token> 里取出 token
#     - 在 /docs 页面上生成一个"Authorize"按钮，方便你手动填 token 调试
#   它只负责"取 token"，不负责"验证 token"——验证还是下面的 token_decode 干。
# =============================================================================
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from jose import jwt, JWTError
from fastapi import HTTPException, status

# 密钥 / 算法 / 过期时间
# ★ 注意：这里的 SECRET_KEY 和 config/config.py 里的 TOKEN_SIGN_SECRET 是两套，
#   实际生效的是这个硬编码值，配置文件不参与。
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"          # 对称签名：签发和校验用同一个密钥
ACCESS_TOKEN_EXPIRE_MINUTES = 15


class AuthTokenHelper:

    @staticmethod
    def token_encode(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
        """生成 JWT（登录成功后调用）"""
        to_encode = data.copy()
        # exp=过期时间、iat=签发时间，都用 UTC（跨时区才不出错）
        expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
        # ★ 这里的 update 会覆盖调用方自己塞的 exp。
        #   api/user.py 里写了 exp=15 分钟，跟这里默认值一致，所以看不出问题。
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def token_decode(token: str) -> Optional[Dict[str, Any]]:
        """解析并校验 JWT（每次需要鉴权的接口调用）"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法验证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            # decode 会验签名 + 验过期，任一失败就抛 JWTError
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise credentials_exception