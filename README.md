# 短链服务

基于 **FastAPI** 的短链接生成与跳转服务，支持自定义短码、访问量异步统计与 JWT 鉴权。

## 技术栈

| 分类 | 选型 |
|---|---|
| Web | FastAPI |
| 数据 | SQLAlchemy + MySQL |
| 短码 | `secrets` 密码学安全随机 + 62 字符集 |
| 跳转 | HTTP 302 重定向 |
| 统计 | `BackgroundTasks` 异步累计 |
| 密码 | passlib + bcrypt |

## 核心实现

### 1. 短码生成

```python
alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"  # 62 字符
short_tag = "".join(secrets.choice(alphabet) for _ in range(8))
```

用 `secrets` 而非 `random`：`random` 是可预测的伪随机，短码被猜中等于站点被开放重定向滥用；`secrets` 基于操作系统熵源。

62 的 8 次方 ≈ **2.18 × 10^14** 种组合，兼顾长度与碰撞概率。

### 2. 跳转与计数解耦

跳转路径上只做两件事：查短码 → 返回 302。**访问量累加放到 `BackgroundTasks`**：

```python
@router.get("/{short_tag}")
async def redirect(short_tag: str, background_tasks: BackgroundTasks, db=Depends(get_db)):
    link = await get_by_tag(db, short_tag)
    background_tasks.add_task(increase_visit, link.id)   # 响应返回后再执行
    return RedirectResponse(link.origin_url, status_code=302)
```

好处：用户不必等待 UPDATE 语句完成，跳转更快；计数失败也不影响跳转本身。

### 3. 密码保护

可选为短链设置密码，用 bcrypt 哈希存储（自带 salt、可调 cost factor，比 md5/sha 更适合存密码）。

## 快速开始

```bash
uv sync
cp .env.example .env      # 填 SECRET_KEY / MySQL 连接
uv run uvicorn main:app --reload
```

访问 http://127.0.0.1:8000/docs 查看接口文档。

## 项目结构

```
├── main.py           应用入口
├── api/              短链创建 / 跳转接口
├── models/           ORM 模型（短链表、用户表）
├── schemas/          出入参模型
├── servies/          业务逻辑
├── dependencies/     依赖注入
└── utils/            JWT / 密码工具
```