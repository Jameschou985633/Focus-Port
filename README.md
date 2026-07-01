# FocusPort 专注星港

FocusPort 是一个以学习专注为核心的游戏化自律平台。项目把番茄钟、待办任务、AI 学习规划、成长奖励、3D/2D 星港建造、好友社交、协作专注室、考试练习和小游戏整合在同一个应用里。

当前仓库包含一个 FastAPI 后端、一个 Vue 3 前端、静态资源、3D/等距城市资产、Blender 生成脚本，以及旧版 HTML 页面。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3, Vite, Pinia, Vue Router, Tailwind CSS, TresJS, Three.js, Chart.js |
| 后端 | FastAPI, Uvicorn, SQLite, Pydantic, python-multipart |
| AI | OpenAI SDK compatible client, Qwen/DashScope compatible API |
| 实时通信 | FastAPI WebSocket |
| 资源 | 静态 PDF/音频文件、前端公开资源 |

## 目录结构

```text
.
├── main.py                         # FastAPI 主后端，数据库初始化、REST API、WebSocket、SPA 托管
├── local-dev-api.mjs               # 轻量本地 mock API，用于前端快速调试
├── ai_teacher.py                   # 旧版/辅助 AI 阅卷脚本
├── fix_db_init.py                  # 历史数据库初始化修复脚本
├── index.html                      # 旧版静态首页
├── admin.html                      # 旧版静态管理页
├── static/                         # PDF、音频、静态 UI 资源、城市槽位配置
├── Blender/                        # 城市、地形、建筑生成和导出脚本
├── pygame_assets/                  # 等距资源预览图
├── focusport-frontend/             # Vue 3 前端工程
│   ├── src/
│   │   ├── api/                    # axios API 封装、Qwen 服务封装
│   │   ├── components/             # 页面和业务组件
│   │   ├── composables/            # AI 规划、任务拆解、手势逻辑
│   │   ├── constants/              # 资产清单、世界名称
│   │   ├── router/                 # 路由和登录守卫
│   │   ├── stores/                 # Pinia 状态管理
│   │   ├── styles/                 # 设计变量、基础样式、过渡
│   │   └── main.js                 # 前端入口
│   ├── public/                     # 前端公开资源和 3D 模型
│   └── vite.config.js              # Vite 配置和本地代理
└── render.yaml                     # Render 部署配置
```

## 核心功能

| 功能 | 说明 | 主要代码 |
| --- | --- | --- |
| 登录与用户档案 | 注册、登录、修改密码、头像、昵称、个人资料 | `main.py`, `src/stores/user.js`, `LoginPage.vue`, `MorePage.vue` |
| FocusHub 首页 | 任务队列、番茄钟、日历、自律指数、AI 任务拆解 | `FocusHubPage.vue`, `src/stores/focusHub.js` |
| 番茄钟和专注奖励 | 开始/暂停/完成专注，记录时长、奖励经验/货币/能量 | `focusApi`, `/api/focus/*`, `useFocusHubStore` |
| 待办任务 | 创建、按日期查看、完成/取消完成、删除、任务评分 | `/api/todo/*`, `taskApi`, `FocusHubPage.vue` |
| AI 学习规划 | 长期计划、阶段拆解、AI 对话、首页任务拆解 | `/api/plans/*`, `useAIPlanning.ts`, `useGoalDecomposer.ts` |
| 手机使用审计 | 上传屏幕使用时间截图、AI 识别、提交自律记录 | `/api/phone-usage/*`, `PhoneUsageReport.vue` |
| 成长系统 | 经验、等级、金币、钻石、连续天数、统计图表 | `/api/growth/*`, `/api/stats/*`, `StatsPanel.vue` |
| 成就和排行榜 | 成就定义、用户成就、排行榜 | `/api/achievements/*`, `/api/leaderboard`, `AchievementPanel.vue`, `Leaderboard.vue` |
| 星港城市 | 3D 物理视界和 2D 盖亚拓扑，支持摆放已购资产 | `CityDimensionShell.vue`, `RealIsland3D.vue`, `IsometricCity.vue` |
| 商城和背包 | 统一商城、物品购买、收藏、库存、放置和移除 | `/api/unified-shop/*`, `UnifiedShop.vue`, `BlueprintVaultPage.vue` |
| 社交 | 好友、站内信、动态圈子、PK 挑战 | `/api/friends/*`, `/api/messages/*`, `/api/circle/*`, `/api/pk/*` |
| 协作专注室 | 自习室创建、加入、座位、开始/结束、WebSocket 同步 | `/api/greenhouse/*`, `/ws/greenhouse/{room_id}` |
| 考试系统 | 试卷列表、提交、AI 主观题分析、批改状态 | `/api/exams`, `/api/submit_exam`, `ExamPage.vue` |
| 游戏大厅 | 五子棋、井字棋、四子棋、黑白棋，部分支持在线房间 | `/api/arcade/*`, `/api/gomoku/*`, `/ws/arcade/*`, `/ws/gomoku/*` |

## 快速启动

### 1. 后端

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

后端启动后可访问：

```text
http://127.0.0.1:8000/api/health
```

`main.py` 会自动初始化 SQLite 数据库。默认优先使用根目录下的 `focusport.db`，如果只存在旧库 `focuscrossing.db`，会回退使用旧库。

### 2. 前端

```powershell
cd focusport-frontend
npm install
npm run dev
```

默认开发地址：

```text
http://127.0.0.1:5174
```

Vite 已配置代理，开发环境下 `/api` 和 `/ws` 会转发到 `http://127.0.0.1:8000`。

### 3. 可选：只跑前端 mock API

如果暂时不想启动完整 Python 后端，可以在根目录启动轻量 mock API：

```powershell
node local-dev-api.mjs
```

它只覆盖登录、成长、头像、待办、消息未读和专注完成等首页常用接口，适合快速调试 FocusHub 首页。

## 环境变量

| 变量 | 用途 |
| --- | --- |
| `QWEN_API_KEY` | 后端调用 Qwen/DashScope compatible API 的首选密钥 |
| `DASHSCOPE_API_KEY` | Qwen API 密钥的兼容别名 |
| `VITE_QWEN_API_KEY` | 后端也会读取的兼容密钥名，不建议在真实前端暴露密钥 |
| `VITE_API_BASE_URL` | 前端请求 API 的基础地址；为空时使用同源或 Vite 代理 |

本地前端如果要连接公网后端，可在 `focusport-frontend/.env.development` 中配置：

```env
VITE_API_BASE_URL=https://your-api-domain.example.com
```

## 常用命令

| 命令 | 说明 |
| --- | --- |
| `npm run build` | 从根目录安装前端依赖并构建前端 |
| `npm run test` | 从根目录运行 Vitest |
| `cd focusport-frontend && npm run dev` | 启动前端开发服务器 |
| `cd focusport-frontend && npm run build` | 构建前端到 `focusport-frontend/dist` |
| `cd focusport-frontend && npm run preview` | 预览前端构建产物 |
| `cd focusport-frontend && npm run sync:twin-assets` | 同步双维度城市资产 |
| `python ai_teacher.py` | 执行辅助 AI 阅卷脚本 |

## 路由概览

| 路径 | 页面 |
| --- | --- |
| `/login` | 登录/注册 |
| `/` | FocusHub 首页 |
| `/island` | 3D/2D 星港城市 |
| `/shop` | 统一商城 |
| `/vault` | 工程装配仓/背包 |
| `/stats` | 成长统计 |
| `/leaderboard` | 排行榜 |
| `/achievements` | 成就墙 |
| `/friends` | 好友 |
| `/mail` | 站内信 |
| `/ai` | AI 助手 |
| `/plans` | 学习计划 |
| `/exam` | 考试练习 |
| `/collab` | 协作专注室 |
| `/pk` | PK 挑战 |
| `/playground` | 游戏大厅 |
| `/admin` | 管理面板 |

`src/router/index.js` 中的全局守卫会检查 `localStorage.username`。除 `/login` 外，大多数页面都需要登录状态。

## 后端接口分组

`main.py` 集中了主要后端能力，接口大致分为：

| 分组 | 路径前缀 |
| --- | --- |
| 健康检查 | `/api/health` |
| 认证和用户 | `/api/register`, `/api/login`, `/api/change-password`, `/api/user/*` |
| 成长和专注 | `/api/growth/*`, `/api/focus/*` |
| 待办和任务评分 | `/api/todo/*`, `/api/tasks/*` |
| AI | `/api/ai/*`, `/api/plans/ai/*` |
| 学习计划 | `/api/plans/*` |
| 手机使用审计 | `/api/phone-usage/*` |
| 好友、消息、圈子 | `/api/friends/*`, `/api/messages/*`, `/api/circle/*` |
| 商城、库存、城市摆放 | `/api/unified-shop/*`, `/api/island/*`, `/api/inventory/*` |
| 成就、统计、排行榜 | `/api/achievements/*`, `/api/stats/*`, `/api/leaderboard` |
| 自习室 | `/api/greenhouse/*`, `/api/sunshine/*`, `/ws/greenhouse/*` |
| 游戏 | `/api/arcade/*`, `/api/gomoku/*`, `/ws/arcade/*`, `/ws/gomoku/*` |
| 考试 | `/api/exams`, `/api/submit_exam`, `/api/exam/*` |

## 前端代码导览

| 文件/目录 | 作用 |
| --- | --- |
| `src/main.js` | 创建 Vue app，注册 Pinia、Router、TresJS |
| `src/App.vue` | 全局壳层、浮动菜单、维度过渡、背景音乐 |
| `src/router/index.js` | 页面路由、登录守卫、标题设置 |
| `src/api/index.js` | 所有后端 REST/WebSocket API 的前端封装 |
| `src/stores/user.js` | 登录用户和成长数据 |
| `src/stores/focusHub.js` | 首页番茄钟、任务、倒计时、本地持久化 |
| `src/stores/dimension.js` | 3D/2D 维度切换和本地持久化 |
| `src/stores/inventory.js` | 商城库存、已放置资产、收藏 |
| `src/stores/mail.js` | 站内信未读轮询 |
| `src/stores/masterTimeline.js` | 主时间线任务和 AI 阶段管理 |
| `src/composables/useAIPlanning.ts` | AI 计划生成、JSON 解析、规则兜底 |
| `src/composables/useGoalDecomposer.ts` | 将目标拆解为阶段任务 |
| `src/components/FocusHubPage.vue` | 当前主页面，实现首页大部分 UI 和交互 |
| `src/components/CityDimensionShell.vue` | 城市维度容器，切换 3D 和 2D 视图 |
| `src/components/RealIsland3D.vue` | TresJS/Three.js 3D 星港 |
| `src/components/IsometricCity.vue` | 2D 等距星港 |
| `src/components/shop/UnifiedShop.vue` | 统一商城 |
| `src/components/collab/*` | 协作专注室、圈子动态 |
| `src/components/base/*` | 通用空间风格基础组件 |

## 数据和持久化

- 后端使用 SQLite，数据库文件位于项目根目录。
- 后端启动时会执行 `init_db()`，自动创建/迁移表、初始化成就、考试、商城和城市资产数据。
- 前端部分状态会存在 `localStorage`，例如登录用户名、FocusHub 番茄钟状态、首页任务缓存、维度偏好。
- 商城和城市资产来自数据库、`static/city_layout_slots.json`、`focusport-frontend/public/models` 和 `src/constants/assets.js`。

## 构建与部署

本项目已包含 Render 配置：

```yaml
buildCommand: pip install -r requirements.txt && cd focusport-frontend && npm install --no-audit --no-fund && npm run build
startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
healthCheckPath: /api/health
```

生产模式下，后端会托管：

- `/static` 指向根目录 `static/`
- `/assets` 指向 `focusport-frontend/dist/assets`
- 未匹配路由回退到前端 SPA

## 测试

前端包含 Vitest 测试，覆盖任务、番茄钟、AI 规划、邮件、时间线、部分组件等逻辑。

```powershell
cd focusport-frontend
npm run test
```

根目录也提供：

```powershell
npm run test
```

## 注意事项

- `ai_teacher.py` 中存在历史硬编码 API Key 写法，正式使用前应移除硬编码密钥并轮换已暴露密钥。
- 当前部分旧文档和历史页面存在乱码，建议后续统一为 UTF-8。
- `main_corrupt_backup.py` 是历史备份文件，不应作为当前主后端入口。
- `focusport-frontend/dist`、`.npm-cache`、`node_modules`、`.venv` 都是构建或依赖产物，不需要人工维护。
- 根目录旧版 `index.html` 和 `admin.html` 与当前 Vue 前端并存，当前主应用以 `focusport-frontend/src` 为准。
