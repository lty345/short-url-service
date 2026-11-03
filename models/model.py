# =============================================================================
# models/model.py —— 两张表：用户 + 短链
# =============================================================================
# 【它在链路里的位置】
#   最底层的数据结构，servies/*.py 里的所有查询都基于这两个类。
#
# 【表 1：user —— 用户表】
#   id       : 自增主键（比聊天室用 username 当主键更规范）
#   username : 用户名
#   password : ★ 密码哈希列，但这里有个真 bug ↓
#   create_at: 创建时间，default=func.now() 由数据库自动填
#
# 【表 2：short_url —— 短链表】
#   short_tag  : 8 位短码（访问 /{short_tag} 时靠它查长链接）
#   short_url  : 完整短链地址（给用户复制用的）
#   long_url   : 原始长链接
#   visit_count: 访问次数（每次跳转 +1，用 BackgroundTasks 异步更新）
#   create_by  : 谁创建的
#   msg_context: 拼好的推广文案（"详情请点击 xxx"）
#
# ★★ 三个真实问题，复习时重点看 ★★
#   1) password = Column(String(32))  ← 硬 bug
#      bcrypt 哈希固定 60 个字符，32 位装不下 → 存进去被截断
#      → verify_password 永远失败 → 用户永远登不上（或只有短哈希能对上）
#      改法：Column(String(60)) 或 String(255)
#
#   2) short_tag 没有 unique=True  ← 隐患
#      短码是随机生成的，理论上可能撞车。没有唯一约束就会存进两条一样的，
#      跳转时 select 取 first() 就取到哪条算哪条。
#
#   3) 没有索引
#      查询都是 where short_tag = ?，但 short_tag 上没有 index
#      → 数据量大时每条跳转都全表扫描。（对比：预约挂号项目里加了 index=True）
# =============================================================================

from db.database import Base
from sqlalchemy import Column, String, DateTime, func, Integer


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)   # 自增主键
    username = Column(String(20))
    # ★ 严重问题：bcrypt 哈希是 60 位，这里只有 32 位，会被截断
    password = Column(String(32))
    # default=func.now() 表示插入时由数据库自动填当前时间（不用在代码里赋值）
    create_at = Column(DateTime(), default=func.now())


class ShortUrl(Base):
    __tablename__ = 'short_url'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # ★ 建议加 unique=True + index=True
    short_tag = Column(String(20), nullable=False)
    # 完整短链地址。★ String(20) 偏短：http://127.0.0.1:8000/ 就 22 个字符了，
    # 本地能存是因为 SQLite 不严格校验长度，换 MySQL 会截断/报错
    short_url = Column(String(20))
    long_url = Column(String, nullable=False)          # 原始长链接，不限制长度
    visit_count = Column(Integer, nullable=False, default=0)   # 访问计数
    create_at = Column(DateTime(), default=func.now())
    create_by = Column(String(20))                      # 创建人（用户名）
    msg_context = Column(String, nullable=False)        # 推广文案模板拼好的结果