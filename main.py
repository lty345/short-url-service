# =============================================================================
# main.py —— 服务入口（uvicorn 启动的目标）
# =============================================================================
# 【它在链路里的位置】
#   启动命令：uvicorn main:app
#   → 执行 lifespan 的启动部分：建表（app 里有 app，但那边的 app 没建表逻辑）
#   → 再 include api.app 里的 app
#
# 【建表逻辑说明】
#   Base.metadata.create_all 只会创建"不存在的表"，已存在的表不动。
#   ★ 它不会改表结构！如果你给模型加了字段，已有的表不会自动加列
#     —— 那是数据库迁移工具（Alembic）的活。
#   本项目没有迁移工具，所以改字段只能删库重启（short.db 删掉即可）。
#
# 【★ 一个小问题】
#   yield 之后什么都没写，没有 await async_engine.dispose()。
#   优雅关闭时连接池不会被主动释放（进程退出时操作系统会回收，所以不算严重）。
#   对比：聊天室项目和预约挂号项目的 lifespan 里都有 dispose。
# =============================================================================
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app):
    pass    # ← 这行 pass 是残留，下面才是真正逻辑
    # 局部 import：避免在模块顶层就触发数据库连接（也让 import 更快）
    from db.database import async_engine, Base
    from models.model import User, ShortUrl   # ★ 必须 import 模型，否则 Base.metadata 里没有这两张表

    async def init_create_table():
        # begin() 开启一个事务，run_sync 把同步的 create_all 桥接到异步连接上执行
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    await init_create_table()
    yield
    # ← 这里缺 await async_engine.dispose()


app = FastAPI(description='一个基于FastAPI的短链服务', lifespan=lifespan)

# 挂路由。注意这两个 import 放在创建 app 之后，
# 是为了让上面的 lifespan 先定义好再被引用（其实 Python 不要求这个顺序，属于风格问题）
from api.short import router_short
from api.user import router_user

app.include_router(router_short)
app.include_router(router_user)


if __name__ == '__main__':
    from servies.user import UserServeries    # 没用到
    import uvicorn
    uvicorn.run(app='main:app', host="127.0.0.1", port=8000)