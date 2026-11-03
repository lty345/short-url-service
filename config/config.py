# =============================================================================
# config/config.py —— 全局配置中心
# =============================================================================
# 【作用】集中管理会变的东西：数据库地址、密钥。其它文件都从这里取。
#
# 【★ 注意这跟聊天室项目里的配置几乎一字不差】
#   两个项目是同一套模板拷过来的，连 TOKEN_SIGN_SECRET 都一样。
#   好处是复习时看到这个文件就能回忆起整套路子；
#   坏处是真实项目里两个服务共用同一个密钥 = 一个泄露全网通，
#   而且数据库都是同一个 short.db 文件（都写死在这个配置里）。
#
# 【这个项目实际用的数据库】
#   sqlite+aiosqlite → 本地文件库，不用装 MySQL。
#   ★ 所以简历/文档里别写"这个项目用 MySQL"。
# =============================================================================
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 异步数据库连接串（SQLite + aiosqlite 异步驱动）
    ASYNC_DATABASE_URL: str = ("sqlite+aiosqlite:///short.db")
    # JWT 签名密钥。★ 硬编码在代码里，生产环境必须改成读环境变量
    TOKEN_SIGN_SECRET: str = 'ZcjT6RcplyIFQoS7'


@lru_cache()
def get_Settings():
    # 带缓存：只真正创建一次 Settings，之后复用同一个对象
    return Settings()