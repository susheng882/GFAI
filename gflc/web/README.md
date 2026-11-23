# GFLC Web · React 19 + Ant Design 5 + Vite

GFLC 前端重构版，替代 `gflc/backend/frontend/index.html`（2849 行原生单文件）。对应 14 号开发约束中的 **S1 / D12 / S4 前端 / D10 前端**。

## 技术栈与版本

| 依赖 | 版本 | 说明 |
|---|---|---|
| React / ReactDOM | 19.3.1 | 报告锁定版本 |
| Ant Design | 5.29.3 | `npm view antd@5 version` 最大值，锁定 5.x |
| Vite | 7.3.8 | 构建工具 |
| react-router-dom | 6.30.6 | BrowserRouter 深链接（后端 `SPAStaticFiles` 已支持回退） |
| react-markdown / rehype-katex | 10.1.0 / 7.0.1 | 答案与笔记的 GFM + LaTeX 渲染 |

## 快速开始

```bash
cd gflc/web
npm install
npm run dev        # 开发：http://127.0.0.1:5173，/api 代理到 127.0.0.1:8010
npm run build      # 构建产物：gflc/web/dist
npm run preview    # 本地预览构建产物
```

> 自测边界内**不启动 8010**（按 14 号约束），`npm run dev` 仅供集成方联调。

## 构建产物与后端接线

- 本工程构建产物输出目录：**`gflc/web/dist`**（`vite.config.js` 的 `build.outDir`）。
- 集成方二选一接线：
  1. 将 `app/core/config.py` 的 `FRONTEND_DIR`（及 `.env`）指向 `gflc/web/dist` 的绝对路径；
  2. 或将 `gflc/web/dist` 内容复制到 `gflc/backend/frontend/dist`，并设置 `FRONTEND_DIR=./frontend/dist`。
- 后端 `app/main.py:125` 已有 `SPAStaticFiles`，非 `/api` 的未知路径回退 `index.html`，React Router 深链接可直接用。
- **不要**覆盖 `gflc/backend/frontend/index.html`（旧版原型保留作对照）。

## API 契约

- 统一 base `/api`，全部请求带 `credentials: 'include'`（HttpOnly Cookie），见 `src/api.js`。
- 成功取响应 `data` 字段；失败统一抛 `ApiError`（含 status/code/message）。
- `/api/qa/stream` 为 NDJSON 流，事件：`status → sources → delta* →（notice）→ done / error`，见 `src/api.js:streamQA`。
- 单文件规模：最大源码 254 行，全部 ≤600 行（`find src -type f -exec wc -l {} +` 可复核）。
- 设计 token（纸墨色/圆角/动效/暗色）集中在 `src/theme.css`，页面样式在 `src/app.css`。

## 差异收敛说明

- **S1 前端 React**：所有旧页面均已迁移 —— 登录/注册、指挥台（概览 + AI 看板）、资料、问答、笔记、卡包、学习/刷题、复习、计划、任务、视频。
- **D12 模块化**：`src/pages/**` 按页面拆文件，`src/components/**` 放共享组件，`src/api.js` 集中请求；无 2849 行巨文件。
- **S4 来源跳转**：`src/components/SourceChips.jsx` 读取 `chunk_id/page/ts_start`：
  - 视频来源（`ts_start > 0`）跳 `/video?doc=<id>&ts=<秒>`，`VideoPage.seek()` 在 `loadedmetadata` 后设置 `currentTime` 并播放，偏差由浏览器精确定位（目标 ≤2s）；
  - 文档来源跳 `/docs?doc=<id>&page=<n>`，`DocumentJumpModal` 打开对应页；若资料带 `file_url/url` 则内嵌 PDF `#page=N`，否则以应用内页码定位器展示。
  - 解析文档 id 优先用 `source.document_id`，其次当前问答限定文档，最后按标题匹配 `/documents`。
- **D10 今日待办**：`src/components/TodayQueue.jsx` 合并 `/review/due` 的到期卡片与 `/plans` → `/plans/{id}` 的当天任务，统一展示并可勾选计划任务完成。

## 新增环境变量

**无。** 本工程不新增环境变量；后端地址在 `vite.config.js` 的 dev proxy 中固定为 `127.0.0.1:8010`，生产由同源 `/api` 提供。

## 需要后端配合（写入集成方待办，不在本工程内修改）

1. `_kb_sources` 已由 `qa-retrieval` Agent 增补 `source_type`，但**仍缺 `document_id`**（`app/routers/qa.py:171`）。前端已按标题匹配兜底，建议后续增补 `document_id`（只增不改），使来源跳转 100% 精确。
2. 文档类跳转缺少原文文件接口：建议集成方在 `app/routers/documents.py` 增加 `GET /api/documents/{id}/file`（或 `DocumentOut.file_url`），前端 `DocumentJumpModal` 会自动切换为内嵌 PDF 并跳到对应页。当前以页码定位器兜底。
3. `PlanTask` 已由 `gov-loop` Agent 增补 `due` 字段并在 `/plans/{id}` 返回，前端 `isTodayTask()` 已优先消费该字段（缺省才回退 `day_index === 1`）。

## 已知取舍

- AI 看板的卡片拖拽/缩放交互简化为响应式 flex 布局 + 双击编辑，保留生成、日周月切换与单卡内容保存。
- 构建产物 JS 约 1.6MB（gzip ~500KB，含 antd 与 KaTeX），Vite 给出 chunk 体积提示但不影响构建；如需首屏极致优化可后续做路由级懒加载。
