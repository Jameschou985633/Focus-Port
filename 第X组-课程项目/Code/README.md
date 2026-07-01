# FocusPort 专注星港代码运行说明

## 一、项目环境

本项目主要使用 Vue 3 + Vite 构建前端页面，使用 Node.js 本地脚本提供开发接口服务。

运行前需要安装：

- Node.js 18 或更高版本
- npm 包管理工具

## 二、目录说明

- `focusport-frontend/`：前端项目代码，包含页面、组件、路由和状态管理。
- `local-dev-api.mjs`：本地开发后端接口，用于登录、任务、成长数据、算力数据、商店等功能。
- `.dev-api-state.json`：本地开发数据文件，保存用户、任务、算力、背包等测试数据。
- `static/`：静态资源目录。

## 三、安装依赖

在项目根目录执行：

```bash
npm install
cd focusport-frontend
npm install
```

## 四、启动后端

在项目根目录执行：

```bash
node local-dev-api.mjs
```

默认后端地址：

```text
http://127.0.0.1:8010
```

## 五、启动前端

进入前端目录：

```bash
cd focusport-frontend
npm run dev -- --host 0.0.0.0 --port 5174
```

浏览器访问：

```text
http://127.0.0.1:5174/
```

## 六、构建项目

在 `focusport-frontend` 目录执行：

```bash
npm run build
```

构建后的文件会生成在：

```text
focusport-frontend/dist/
```

## 七、注意事项

- 请先启动后端，再启动前端。
- 前端开发服务器会将 `/api` 请求代理到 `http://127.0.0.1:8010`。
- 如果端口被占用，可以修改 `local-dev-api.mjs` 中的端口，或通过环境变量 `PORT` 指定后端端口。
- 本项目当前使用本地开发数据文件，不需要额外数据库即可运行演示。
