# =============================================================================
# servies/user.py —— 用户的业务逻辑层（CRUD + 密码哈希）
# =============================================================================
# 【它在链路里的位置】
#   api/user.py 的 login / create_user
#     → 本文件
#     → models/model.py 的 User 表
#     → utils/password.py（哈希/校验密码）
#
# 【和聊天室项目的对比】
#   聊天室：UserServeries 是"一堆散函数"，没有类
#   本项目：用 class + @staticmethod 组织，更像真实项目的 service 层
#   两种写法都行，但类的好处是名字空间清晰（UserServeries.get_user_by_name）
#
# ★★ 两个真实 bug ★★
#   1) create_user：如果用户名已存在，直接跳过 if 块 → 后面的 return new_user
#      会引用未定义的变量 → UnboundLocalError（运行时报错，不是返回 None）
#   2) update_user 的 Update() 用法是对的，但没做"用户不存在"的判断
# =============================================================================
import datetime

from sqlalchemy import Update, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.model import User
from utils.password import PasslibHelper


class UserServeries:

    @staticmethod
    async def get_user(async_session: AsyncSession, user_id: int):
        result = await async_session.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    @staticmethod
    async def get_user_by_name(async_session: AsyncSession, username: str):
        # 登录和注册判重都靠它
        result = await async_session.execute(select(User).where(User.username == username))
        return result.scalars().first()

    @staticmethod
    async def get_users(async_session: AsyncSession):
        # fetchall() 返回全部结果（first() 只返回第一条）
        result = await async_session.execute(select(User).order_by(User.id))
        return result.scalars().fetchall()

    @staticmethod
    async def create_user(async_session: AsyncSession, username: str, password: str):
        # ★ 注意：这里的 password 参数应该传【明文】，
        #   下面会用 PasslibHelper.hash_password 哈希后再存。
        #   （utils/password.py 的 __main__ 里先哈希了一遍再传进来 = 双重哈希，错的）
        if not await UserServeries.get_user_by_name(async_session, username):
            new_user = User(username=username, password=PasslibHelper.hash_password(password))
            async_session.add(new_user)
            await async_session.commit()
            await async_session.refresh(new_user)     # 拿回自增 id 等数据库生成的值
        # ★ BUG：如果用户已存在，if 不执行，下面的 return new_user 会炸
        #   UnboundLocalError: cannot access local variable 'new_user'
        #   正确写法：如果存在就 return None 或抛 BusinessError。
        return new_user

    @staticmethod
    async def update_user(async_session: AsyncSession, user_id: int, **kwargs):
        # 按 id 批量更新字段（**kwargs 里传什么列就改什么列）
        # ★ 安全隐患：没有白名单，如果上层把 {'id': xxx} 或随意字段传进来也会被塞进 SQL。
        #   真实项目应该只允许改特定字段（比如 password、nickname）。
        response = Update(User).where(User.id == user_id)
        result = await async_session.execute(response.values(**kwargs))
        await async_session.commit()
        return result

    @staticmethod
    async def delete_user(async_session: AsyncSession, user_id: int):
        result = await async_session.execute(delete(User).where(User.id == user_id))
        await async_session.commit()
        return result