# =============================================================================
# api/app.py —— 组装 FastAPI 应用（只有 5 行）
# =============================================================================
# 【它和 main.py 的关系（容易混）】
#   这个文件：创建 app + 挂路由，纯组装
#   main.py  ：再把它包一层（加 lifespan 建表）+ 作为 uvicorn 启动入口
#
#   实际运行的是 main.py（uvicorn main:app），app.py 只是被 main.py import 进来。
#   两套文件并存是教材演进留下的痕迹，真实项目一般合成一个。
#
# 【为什么单独抽一个 app.py】
#   好处：写测试时可以 from api.app import app，不用连带跑 lifespan（不用建表/连库）。
#   这其实是 FastAPI 项目里很常见的做法（app 工厂模式）。
# =============================================================================
from api.short import router_short
from api.user import router_user
from fastapi import FastAPI

app = FastAPI()

# 两组路由：短链访问 + 用户相关
# include_router 只是把别的文件的 APIRouter 合并进来，prefix 已经在各自的 APIRouter 里定义
app.include_router(router_short)
app.include_router(router_user)