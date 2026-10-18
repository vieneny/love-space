# Love Space

Single repository: Python API in backend/, Vue management app in apps/admin/, uni-app WeChat app in apps/miniapp/. API contract: docs/API_CONTRACT.md.

Preserve personal/private vs current couple-space access boundaries in records, parent IDs, files, queries, statistics and unbinding. No production dev login, public photo directories, embedded keys or fabricated production data. Auth must be checked server-side. The map and timeline use the same memories. Store original coordinate system; never label site-order lines GPS tracks. Historical occurrence dates are not upload dates.

Use UTF-8. Keep credentials, build artifacts and user media out of git. Do not overwrite other agents' files. Run meaningful isolation/concurrency tests and both frontend production builds before release. Real WeChat upload requires a formal AppID, appropriate upload authorization and a reachable HTTPS Python backend. No claim of upload or overseas map validation without evidence.

从本次开源起，所有新 Git 提交使用 `type(scope): 中文主题` 或 `type: 中文主题`，允许 feat、fix、docs、refactor 等英文标签，主题必须含中文。安装仓库 Git hooks 后执行提交检查，不改全局 Git 配置。

项目整体技术与部署文档、产品需求文档分别维护在维护者指定的飞书知识库，按本次用户明确要求拆分为两份。更新前读取相应文档，区分目标需求、当前实现和已验证范围；更新后回读正文并记录变更。维护者本机的 `artifacts/feishu-project-map.json` 保存文档定位信息，不上传公开仓库。公开仓库 docs 仅保留开源运行、接口契约和通用说明，不复制真实凭据或私人环境资料。

开源主分支仅推送经过敏感数据检查的代码；`local-history/*` 分支和带 `-local` 的本地标签保留内部历史，不推送。Git 作者使用 GitHub noreply 邮箱。任何 `VITE_*` 值都可能编译到客户端，禁止放入密钥。疑似凭据泄露时先撤销并轮换，不把删除当前文件等同于清理历史。
