# =============================================================================
# servies/short.py —— 短链的业务逻辑层（CRUD）
# =============================================================================
# 【它在链路里的位置】
#   api/short.py（接口层）→ 本文件（业务层）→ models/model.py（表）
#
#   好处：接口层不写 SQL，将来加个"批量删除短链"的接口能复用这里的函数。
#
# 【这个类就是标准的 CRUD 五行】
#   get_short_url        : 按短码查（跳转时用）          ← Read
#   create_short_url     : 新增一条                     ← Create
#   update_short_url     : 按 id 改字段                 ← Update
#   delete_short_url     : 按 id 删                     ← Delete
#   create_batch_short_url: 批量插入（上传文件时用）
#
# 【SQLAlchemy 2.x 的写法规律（背下来）
#   查询：select(X).where(条件) → await session.execute(stmt) → .scalars().first() / .fetchall()
#   更新：Update(X).where(条件) → await session.execute(stmt.values(**kwargs))
#   删除：delete(X).where(条件) → await session.execute(...)
#   ★ 所有操作后面都要 await session.commit()，否则不落库
# =============================================================================
from typing import List

from pydantic_extra_types.uuid_types import uuid7      # 没用到，残留 import
from sqlalchemy import Update, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.model import ShortUrl


class ShortServices:

    @staticmethod
    async def get_short_url(async_session: AsyncSession, short_tag: str):
        # 按短码查。跳转接口（api/short.py 的 short_redierct）靠它拿 long_url
        result = await async_session.execute(select(ShortUrl).where(ShortUrl.short_tag == short_tag))
        return result.scalars().first()      # 查不到返回 None

    @staticmethod
    async def create_short_url(async_session: AsyncSession, **kwargs):
        # 用 **kwargs 直接展开成模型字段，所以 dict 的 key 必须和列名完全一致
        new_short_url = ShortUrl(**kwargs)
        async_session.add(new_short_url)     # 加进会话（还没落库）
        await async_session.commit()         # 提交落库
        return new_short_url

    @staticmethod
    async def update_short_url(async_session: AsyncSession, short_url_id: int, **kwargs):
        # SQLAlchemy 2.x 的 UPDATE 写法：先建 Update 语句，再 .values() 给新值
        # ★ 注意点：这里用了独立 UPDATE 语句，不会触发 ORM 的对象更新事件，
        #   也不会更新内存里已有的对象（所以跳转接口里 data.visit_count += 1 是改内存，
        #   而本次 update 是改数据库，两边各走各的）。
        response = Update(ShortUrl).where(ShortUrl.id == short_url_id)
        result = await async_session.execute(response.values(**kwargs))
        await async_session.commit()
        return result

    @staticmethod
    async def delete_short_url(async_session: AsyncSession, short_url_id: int):
        response = await async_session.execute(delete(ShortUrl).where(ShortUrl.id == short_url_id))
        await async_session.commit()
        return response

    @staticmethod
    async def create_batch_short_url(async_session: AsyncSession, short_urls: List):
        # 批量插入：add_all 一次性把一批对象塞进会话，一次 commit 全部落库
        # → 比 for 循环一条条 commit 快得多（少了 N 次网络往返/事务开销）
        async_session.add_all(short_urls)
        await async_session.commit()
        return short_urls