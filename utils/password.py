# =============================================================================
# utils/password.py —— 密码哈希（bcrypt）
# =============================================================================
# 【为什么密码必须哈希，不能存明文】
#   存明文 = 数据库一泄露，所有用户密码直接暴露（而且用户往往多处复用密码）。
#   bcrypt 是"加盐 + 慢哈希"：
#     - 加盐：同样的密码每次哈希结果都不同，防止彩虹表
#     - 慢：故意算得慢（约 0.1 秒），让暴力破解的成本高到不可行
#
# 【它和聊天室项目的对比（重要）】
#   聊天室：密码明文存、明文比对（models/User.py）
#   本项目：密码 bcrypt 哈希存、用 verify 校验  ← 这才是正确做法
#   同一个作者两个项目，一个错一个对，正好可以当"我知道正确做法"的证据。
#
# 【★ 本项目里的一个真 bug（在 models/model.py，这边说明）】
#   bcrypt 生成的哈希是 60 个字符，但 models/model.py 里
#   password = Column(String(32)) 只有 32 位 → 存进去会被截断！
#   截断后 verify_password 永远失败 = 长密码用户永远登不上。
#   正确做法：Column(String(60)) 或 Column(String(255))。
#
# 【用法】
#   hash_password("123456")                    → 存库用的哈希
#   verify_password("123456", 库里的哈希)       → 登录时校验，返回 True/False
# =============================================================================

# ★ 下面这几个 import 全部没被用到，是从别处拷代码带过来的残留。
#   删掉不影响运行：from subprocess import run
#                   from pydantic import deprecated
#                   from pydantic_settings.sources.providers import aws
#                   from sqlalchemy import func
from subprocess import run

from passlib.context import CryptContext
from pydantic import deprecated
from pydantic_settings.sources.providers import aws
from sqlalchemy import func


# CryptContext 是 passlib 的入口：说明用 bcrypt 方案，deprecated="auto" 表示
# 允许校验旧方案哈希（将来换算法时可以平滑过渡）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasslibHelper:
    @staticmethod
    def verify_password(plain_password: str, hash_password: str):
        # 登录时用：把用户输入的明文和库里的哈希比对（passlib 内部会处理加盐）
        return pwd_context.verify(plain_password, hash_password)

    @staticmethod
    def hash_password(password: str):
        # 注册/改密时用：生成哈希（每次结果都不同，因为盐是随机的）
        return pwd_context.hash(password)


# ---- 下面这段是"写库脚本"（用于手动创建一个 admin 账号）--------------------
# ★ 这段跑不起来，有两个问题：
#   1) get_db_session_asynccont 这个函数在 dependencies 里并不存在
#      （那边叫 get_db_session，而且是异步生成器，不能 async with 直接用）
#   2) 双重哈希：create_user 内部自己会调 PasslibHelper.hash_password，
#      这里又先哈希了一遍 → 存进去的是"哈希的哈希"，永远登不上
# 正确写法是直接传明文：await UserServeries.create_user(s, username='admin', password='123456')
if __name__ == '__main__':
    import asyncio
    from servies.user import UserServeries
    from dependencies.dependencies import get_db_session_asynccont

    async def create_admin_user():
        async with get_db_session_asynccont() as async_session:
            await UserServeries.create_user(
                async_session,
                username='admin',
                password=PasslibHelper.hash_password("123456"),   # ← 双重哈希，应传明文
                created_at=func.now()                             # ← create_user 也不接受这个参数
            )
    asyncio.run(create_admin_user())