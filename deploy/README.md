# 单服务器公网部署

API、管理后台、PostgreSQL 和私有照片卷共用一台 Linux 主机，Caddy 提供 HTTPS。这套文件适用于标准 HTTPS 后端；微信云托管需要另外适配。仓库内没有可核验的现有公网服务器、域名或 SSH 部署目标，不能据此认定已有可复用资源。本说明与静态检查不代表已经上线或通过恢复演练。

## 准备生产配置

需要持续运行的 Linux 主机、Docker Engine 与 Compose、指向主机的实际域名，以及微信要求的备案和服务器域名配置。先确认现有主机的可用内存、磁盘、带宽和 80/443 是否已被其他服务使用；不要覆盖现有反向代理或数据库。公网仅开放 80/443；SSH 限制为管理来源，PostgreSQL 的 5432 和 API 的 18100 不发布宿主端口。

1. 将 deploy/.env.example 复制为 deploy/.env，配置域名、正式 AppID/AppSecret，以及分别生成的数据库密码、JWT 密钥和后台密码。在 Linux 设置 `chmod 600 deploy/.env`，不复用本地开发配置、不提交环境文件。数据库密码至少 24 位，使用 URL-safe 字符；JWT 至少 32 字节，后台密码至少 12 个字符。建议使用独立随机值。
2. 在仓库根运行 `node deploy/check-production.mjs --config-only`，仅检查配置格式。脚本不会联网或启动服务，也不会显示配置值；shell 中同名变量按 Compose 规则优先，请清除过期覆盖值。脚本接受简单的单行字面配置，拒绝 `$` 插值和明显占位值，不验证微信密钥真实性或随机数强度。
3. 在 apps/admin/.env.production.local 设置 `VITE_API_BASE_URL=https://你的实际域名`，不带 /api 路径。运行 `pnpm install --frozen-lockfile` 和 `pnpm build:admin`。后台构建在本地或 CI 完成，服务器不必安装 Node.js。
4. 在构建机运行 `node deploy/check-production.mjs`，确认后台产物含对应 HTTPS 地址、没有本机 API 地址。它不能证明产物来源、完整运行行为或已获备案。
5. 小程序的 apps/miniapp/.env.production.local 使用同一正式 API 域名与本小程序 AppID，并关闭开发登录。完成正式发布预检、微信 request/uploadFile/downloadFile 域名配置和开发者工具核验。

不要把任何秘密放入 `VITE_*`，这些值会进入客户端。预检只做本地格式判断；即使通过，也要在部署前确认账号授权、域名和实际生产环境。

## 部署与验收

将源码、锁文件和已经构建的 apps/admin/dist 安全传到服务器，生产环境文件单独配置。不要上传本地数据库、照片、二维码或其他项目的文件。

从仓库根运行：

```sh
docker compose --env-file deploy/.env -f deploy/compose.yml config --quiet
docker compose --env-file deploy/.env -f deploy/compose.yml up -d --build
docker compose --env-file deploy/.env -f deploy/compose.yml ps
```

使用 `config --quiet`；完整 `docker compose config` 会展开配置，可能将秘密显示到终端或日志。第一次启动 API 会执行数据库迁移。Caddy 申请证书需要正确 DNS、可达的 80/443 和出站联网；其证书保存在 caddy_data 卷。数据库与照片分别保存在 postgres_data、private_media 卷，不在容器临时层。不要使用 `down -v` 或清理这些卷。

检查 HTTPS 证书及 `/health`；公网 `/health` 是进程存活检查。容器内 `/ready` 检查数据库和媒体目录权限，供 API 健康探针使用，不由 Caddy 公开代理；web 在 API 健康后启动。就绪检查不能代替真实登录和持久化写入验证。用两个真实测试账号验证上传/展示、私人及共同记录隔离、邀请码、解绑后访问撤销；重启容器后再读取同一条记录和图片。微信体验版需要另行上传并添加体验成员，公网 API 可达不等于小程序已公开发布。

管理后台只面向维护者。上线前通过反向代理、来源 IP 或可信私网限制后台入口，避免将后台登录直接开放给无关访问者；应用用户接口保持所需公网可达性。当前 Caddy 对照片上传请求体限制为 12 MB，其余 API 为 256 KB；应用再限制照片内容最多 10 MiB。三个服务配置每份 10 MB、最多 3 份的 Docker 日志轮转。仍需按实际主机配置登录尝试限额和磁盘告警；API 文档不能仅依赖“不显示链接”隐藏，应确认反向代理的实际路由。

2026-10-18 已在本地隔离容器中构建和启动生产镜像，验证 uid 10001 的 API 可以写入媒体持久卷，以及 Caddy 的照片上传和超限 413 行为。该验证未使用公网域名申请证书，也不等于公网服务器、真实微信链路或恢复演练通过。

## 数据库与照片的一致备份

Linux Bash 脚本 deploy/backup.sh 会短暂停止当前 Compose 的 API，依次导出 PostgreSQL、自现有 API 镜像只读归档照片，然后恢复原 API。此期间客户端暂时不可用。脚本要求恰好一个正在运行的 API 和 PostgreSQL，不会启动原本停止的服务；不会运行 API 的迁移命令或使用其他项目数据。

```sh
bash deploy/backup.sh --quiesce-api
```

可用 `--env-file PATH` 指定生产文件、`--output DIR` 指定备份目录。默认输出到被 Git 忽略的 deploy/backups。备份包含 database.dump、media.tar.gz、manifest.txt、SHA256SUMS，文件仅当前用户可读。锁固定在本仓库 deploy/backups/.backup.lock，与输出目录无关，防止同一仓库的备份并发；它不能替代部署锁或阻止另一份克隆、其他工具写入。备份期间不要更新、迁移、删除卷或从其他工具写库。

一致性成立的前提是所有数据库和照片写入均来自这个单 API，且没有外部写入者或其他副本。停止 API 后，数据库快照与照片才处于同一个不变窗口。脚本验证 pg_restore 能读取目录、照片压缩包可列出、校验和正确；**这些检查没有实际恢复数据，不代表恢复验证通过**。失败时会尝试恢复 API，留下的 .partial-* 不视为完整备份。正常退出也需检查容器与 HTTPS 恢复；断电或强制杀进程可能绕过恢复处理，需要人工启动原 API。

本机备份不防整机故障。每次将完整备份加密复制到另一台设备或独立存储，并核验校验和；环境文件及必要密钥另行加密保存，不上传公开 Git。建议体验期每天及每次迁移前备份；只在确认离机副本与恢复能力后，按明确保留期处理旧副本。脚本不会自动删除历史备份或产生云存储费用。

## 在隔离环境演练恢复

恢复有覆盖风险，只在全新的隔离项目或专用测试主机操作。以下命令使用 `love-space-restore` 项目名，不启动 web 或生产 API。不要删去 `-p love-space-restore`，不要指向生产卷；先核对主机、项目名与备份来源。只恢复自己生成并信任的归档。

```sh
LOVE_BACKUP_DIR=/absolute/path/to/backup-directory
(cd "$LOVE_BACKUP_DIR" && sha256sum --check SHA256SUMS)
docker compose -p love-space-restore --env-file deploy/.env -f deploy/compose.yml up -d postgres
# 等待上述独立 PostgreSQL 健康后恢复；仅使用全新隔离库。
docker compose -p love-space-restore --env-file deploy/.env -f deploy/compose.yml exec -T postgres \
  pg_restore --exit-on-error --no-owner --no-acl -U love_space -d love_space < "$LOVE_BACKUP_DIR/database.dump"
```

照片需同时恢复到这个隔离项目的 private_media 卷，不能只恢复数据库。下面的镜像 ID 必须替换为本机已构建、带 tar 的 API 镜像；命令只运行 tar 和权限设置，不运行应用：

```sh
LOVE_API_IMAGE=替换为本机API镜像ID
docker run --rm --network none --read-only -i --user 0 \
  --mount type=volume,src=love-space-restore_private_media,dst=/restore \
  --entrypoint sh "$LOVE_API_IMAGE" \
  -c 'tar -xzf - -C /restore && chown -R 10001:10001 /restore' < "$LOVE_BACKUP_DIR/media.tar.gz"
```

之后在隔离网络中验证迁移版本、用户/记录/媒体数量与关联、文件可读及两账号权限；配置独立测试入口，禁止误接生产流量。只有数据库和照片都实际恢复并能经应用读取，才记录恢复成功。本次没有运行上述恢复命令。

升级前先备份并保留上一 API 镜像；数据库迁移不一定可逆，只回退镜像不等于回退数据库。先在隔离环境验证迁移与恢复，再更新正式实例。
