# FocusPort 专注星港软件运行说明

## 一、运行环境

本软件运行需要：

- Windows、macOS 或 Linux 操作系统
- Node.js 18 或更高版本
- npm
- 现代浏览器，例如 Chrome、Edge 或 Firefox

## 二、运行方式

1. 打开项目根目录。
2. 安装根目录依赖：

```bash
npm install
```

3. 安装前端依赖：

```bash
cd focusport-frontend
npm install
```

4. 回到项目根目录并启动本地后端：

```bash
node local-dev-api.mjs
```

5. 进入前端目录并启动前端：

```bash
cd focusport-frontend
npm run dev -- --host 0.0.0.0 --port 5174
```

6. 在浏览器打开：

```text
http://127.0.0.1:5174/
```

## 三、主要功能

系统包含账号登录、任务管理、专注计时、成长数据、算力记录、商店购买、场景装扮、AI 助手和协作学习等功能。

## 四、说明

本目录用于放置可执行文件、部署包、运行说明或软件演示材料。如无单独可执行程序，保留本 README 文件即可满足提交要求。
