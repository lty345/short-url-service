# =============================================================================
# db/database.py —— 数据库连接层
# =============================================================================
# 【它在链路里的位置】
#   最底层：所有 models/*.py 继承这里的 Base；
#   dependencies/dependencies.py 用这里的 SessionLocal 生产会话。
#
# 【三个核心对象】
#   async_engine : 连接池。全局一个就够。
#   Base         : ORM 模型基类，SQLAlchemy 靠它收集"有哪些表"。
#   SessionLocal : 会话工厂，调一次得到一个会话（一次数据库操作）。
#
# ★ expire_on_commit=False 很关键：
#   否则 commit 之后再访问对象属性会触发额外查询，在异步上下文里极易报错。
# =============================================================================
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

from config.config import get_Settings

# echo=False 不打印 SQL；调试时改 True 能看到实际执行的语句
async_engine = create_async_engine(get_Settings().ASYNC_DATABASE_URL, echo=False)

# 所有模型类都继承它
Base = declarative_base()

# 会话工厂：绑定引擎 + 指定异步会话类型
SessionLocal = sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)