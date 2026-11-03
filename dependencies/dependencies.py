# =============================================================================
# dependencies/dependencies.py —— 依赖注入：每个请求一个数据库会话
# =============================================================================
# 【它在链路里的位置】
#   路由函数参数写 db_session: AsyncSession = Depends(get_db_session)，
#   FastAPI 会自动调这个生成器，把 yield 出来的会话注入进来。
#
# 【为什么用 yield 而不是 return】
#   这样才有"用完收拾"的机会：请求结束后回到这里执行 finally → 自动 close()。
#   不用 yield 的话，连接就得靠调用方手动关，漏一次就是连接泄漏。
#
# 【★ 注意：这里没有自动 commit / rollback】
#   所以业务层（servies/*.py）必须自己 await async_session.commit()。
#   预约挂号项目里那份做得更完善（自动提交/回滚），可以对照看两种风格。
# =============================================================================
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from db.database import SessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    db_session = None
    try:
        db_session = SessionLocal()
        yield db_session          # 借给路由函数，函数在这里暂停
    finally:
        await db_session.close()  # 不管成功失败都关掉