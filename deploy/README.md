# 单服务器部署

这是备用的自建域名路线；云托管路线不直接使用此 Compose。先完成域名/备案和服务器选型，再实际部署。本次只准备文件，未购买、未公开部署。

API、管理后台、PostgreSQL 和私有照片卷共用一台 Linux 主机，Caddy 自动申请和续期 HTTPS 证书。80/443 对外开放；数据库和 API 不直接发布宿主端口。不要使用本地开发 .env 运行公网服务。

1. 在 apps/admin/.env.production.local 设置 `VITE_API_BASE_URL=https://你的域名`（不附加 /api 前缀），运行 `pnpm install --frozen-lockfile` 和 `pnpm build:admin`。
2. 将 deploy/.env.example 复制为 deploy/.env，填入实际域名、正式 AppID/Secret，以及独立随机密钥。数据库密码使用 URL-safe 字符，避免连接串转义错误。
3. 域名 A 记录指向主机；按微信规定完成备案和服务器域名配置。保留小程序 request/uploadFile/downloadFile 所需域名。
4. 从仓库根运行 `docker compose --env-file deploy/.env -f deploy/compose.yml config --quiet`，然后 `docker compose --env-file deploy/.env -f deploy/compose.yml up -d --build`。
5. 检查容器状态、HTTPS、微信登录、图片上传和两账号隔离；管理后台应只展示运营元数据。API 文档不由反向代理公开。

第一次部署会自动执行数据库迁移。更新前先备份，保留上一镜像版本；不要使用 `down -v`，它会删除持久卷。

数据库可用 `docker compose --env-file deploy/.env -f deploy/compose.yml exec -T postgres pg_dump -U love_space -d love_space -Fc` 导出；在 Linux 使用重定向写入仅管理员可读的备份目录，另备份 private_media 卷。备份应离机保存并实际做恢复演练。删除数据库时不要遗漏照片备份的保留期限。

上线后再根据真实用量评估对象存储、独立数据库、限流和备份自动化。生产数据不能存于容器临时文件系统。
