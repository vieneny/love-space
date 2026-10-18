# 微信同 WiFi 开发预览

需要手机通过移动网络或其他 Wi-Fi 体验时，使用 [免费外网预览](PUBLIC_PREVIEW.md)。它复用本地隔离后端，通过受限网关与临时 HTTPS 隧道连接；电脑仍需持续运行。下文保留同 Wi-Fi 方式，方便离线开发。

用于手机连接本机 Python API 的开发预览，不是上传正式体验版。电脑与手机需要连接同一 WiFi；后端监听局域网接口，例如 `192.168.1.100:18101`，并保持运行。手机无法通过电脑的 `127.0.0.1` 访问后端。

本次验证（2026-10-18）：用户已确认使用自己的正式 AppID，在手机上通过真实微信登录并进入地图页面，微信 CLI 报告包体为 **203409 字节**。照片上传与展示、双账号绑定与共同空间、境外原生地图尚未验证。本文的 `192.168.1.100` 均为示例，应替换为你自己的电脑私网地址；真实 AppID 保存在被忽略的本地配置，不写入公开文档。

准备：安装并登录微信开发者工具，开启「设置 → 安全设置 → 服务端口」；命令使用 `C:\Program Files (x86)\Tencent\微信web开发者工具\cli.bat`。正式 AppID 继续保存在 `apps/miniapp/.env.production.local` / `.env.development.local`，不要提交环境文件或密钥。账号需要具有该小程序的开发权限。

维护者验证时的后端已经运行，不要重复启动。后续自行使用或重启时，在仓库根目录打开终端，按自己的 IP 启动隔离的手机预览服务：

```powershell
Set-Location backend
$env:DEV_LOGIN_ENABLED = 'false'
$env:DATABASE_URL = 'sqlite:///./data/phone-preview.db'
$env:MEDIA_ROOT = 'data/phone-preview-media'
$env:PUBLIC_BASE_URL = 'http://192.168.1.100:18101'
$env:ADMIN_PASSWORD = ''
uv run uvicorn app.main:app --host 192.168.1.100 --port 18101 --no-access-log
```

该服务使用独立数据库与图片目录，并关闭开发身份登录、管理员登录；真实微信登录所需配置继续从后端被忽略的 `.env` 读取。电脑必须保持开机，服务终端保持运行。若局域网 IP 变化，需要同时更新上述 `--host`、`PUBLIC_BASE_URL` 和下方预览命令的 `--api-base-url`，再重新编译生成二维码；旧包不会自动切换 API 地址。

在仓库根目录运行，地址必须显式填写为当前电脑的私网 IPv4：

```powershell
# 只校验地址和工具路径，不构建、不调用微信 CLI
pnpm preview:wechat --api-base-url http://192.168.1.100:18101 --check

# 构建并通过官方 CLI 生成手机扫码二维码
pnpm preview:wechat --api-base-url http://192.168.1.100:18101
```

仅接受 `10.*`、`172.16.*` 至 `172.31.*`、`192.168.*` 的 HTTP 源地址及有效端口。地址不带接口路径、账号、查询参数或片段；拒绝公网、回环、主机名和非标准 IPv4 写法。`--check` 不检测手机连通性或后端状态。

命令强制关闭 `VITE_ENABLE_DEV_LOGIN`，以 `build:mp-weixin:preview --mode development` 编译，并仅修改被 Git 忽略的生成目录中 `project.config.json` 的 `setting.urlCheck=false`。源配置、环境文件和正式发布预检不变。手机扫码后需要在该小程序的开发调试设置中关闭域名校验；使用真实微信登录，后端应配置匹配的 AppID/Secret，并关闭开发登录。仅向可信 WiFi 开放开发后端，管理员登录也应关闭。

二维码输出到 `artifacts/wechat-phone-preview.png`，CLI 信息输出到 `artifacts/wechat-phone-preview-info.json`，均不提交 Git。命令需要已安装后端依赖的 Windows 虚拟环境 `backend/.venv/Scripts/python.exe`：微信 CLI 的图片可能实际为 JPEG，脚本通过既有 Pillow 解码校验并转换为真正的 PNG，随后删除中间图片。命令先删除旧结果，只有本次产生有效的新 PNG 才报告成功；微信 CLI 报错后即使退出码为 0，也不会将旧二维码判为成功。被强制中断后若留下 `artifacts/wechat-phone-preview.lock`，先确认旧进程已停止，再删除锁文件后重试。

后续继续检查私人/共同记录、照片上传与展示、双账号绑定与隔离，以及境外原生地图。本次登录进入地图的验证不覆盖这些场景。正式体验版继续使用 HTTPS 公网域名、服务器域名白名单及原有发布校验。
