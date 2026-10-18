# 共赴山海手记 · 微信小程序

Vue 3 / TypeScript / uni-app。五个入口：地图、时光、旅行、一起、我们；所有用户数据通过 Python API 保存，无预置用户、照片或旅行统计。

在仓库根安装工作区依赖后，在本目录运行：

```powershell
pnpm dev:h5
pnpm dev:mp-weixin
pnpm typecheck
pnpm build:h5
pnpm build:mp-weixin:preview
```

H5 本地入口为 `http://127.0.0.1:15174`，默认 API `http://127.0.0.1:18100`。API 需要允许该开发来源跨域；真机访问时应把 API 改为真机可访问的局域网地址或 HTTPS 服务。`.env.example` 说明配置；不要提交本地环境文件。

`dev:h5` / `dev:mp-weixin` 才显示本地调试登录，生产编译完全移除该入口。开发模式未显式禁用时允许体验者输入自己的固定标识；服务端也必须开启其开发登录。生产 H5 未配置 API 时明确显示未配置，不会连接其他项目。

`build:mp-weixin:preview` 只验证本地小程序编译，可以无 AppID，不能据此上传发布。正式运行 `pnpm build:mp-weixin` 前必须设置 `VITE_WX_APPID`、HTTPS `VITE_API_BASE_URL`，并将 `VITE_ENABLE_DEV_LOGIN=false`；命令调用仓库统一发布预检，拒绝缺失配置、旧测试号、本机地址等。正式 AppID 只写入生成的 `project.config.json`；源文件保留空占位，不复用旧测试号。生成目录为 `dist/build/mp-weixin`。本地预览包同样没有生产调试登录入口；使用本地调试登录请运行开发服务。

微信端使用原生腾讯地图。H5 无地图服务密钥时显示明确标注的经纬度分布网格，支持手动标点，不冒充导航底图。国内 WGS84 原始点不盲目偏移，待坐标校验；海外原生底图、点位对齐和地点服务仍需正式 AppID/授权后真机核验。虚线仅为按日期排列的「地点顺序」，不是 GPS 轨迹。

上传图片使用后端返回的受保护 URL；客户端不把 Bearer token 附加到图片 URL。地图与时间线使用同一批回忆。进入各页重新请求授权范围内的数据，解绑后不复用对方内容。共享范围由服务端检查，前端按钮不作为权限保障。

## 免费外网预览与正式体验版

临时0元外网调试可使用[免费外网预览说明](../../docs/PUBLIC_PREVIEW.md)，在隔离后端前运行受限网关与 Cloudflare Quick Tunnel，然后执行 `pnpm preview:wechat --api-base-url https://实际随机子域.trycloudflare.com`。预览命令仅接受该服务的单层 HTTPS 子域，保持 development 构建、开发登录关闭，并仅在生成配置关闭域名校验。电脑、后端、网关和隧道必须持续运行；地址变化需重新编译。该路径仍是开发预览，扫码者需在小程序后台获得[开发者权限](https://developers.weixin.qq.com/miniprogram/dev/framework/quickstart/release.html#小程序成员管理)，并在手机中[开启调试模式](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html#跳过域名校验)；体验成员权限适用于体验版。该命令不会生成平台正式体验版，也不保证任意微信用户可访问。

分享给异地体验者需要持续可访问的公网 HTTPS Python 后端、持久数据库和私有图片存储。局域网地址和关闭域名校验的开发预览不能替代该部署。本仓库命令不会开通云资源、购买服务或修改后端配置。

上传前完成：

1. 将正式 `VITE_WX_APPID` 保存在被忽略的 `.env.production.local`；AppSecret、数据库密码等只放服务端，任何 `VITE_*` 都可能编译到客户端，不能放密钥。
2. 部署与该 AppID 匹配的后端，关闭开发登录；配置真实 HTTPS 域名、持久数据库、私有媒体、备份及隐私指引。确认微信后台接受并配置该 API 对应的 request、uploadFile、downloadFile 合法域名。
3. 登录官方微信开发者工具，开启安全设置中的服务端口，并确保登录账号具有该小程序的开发／上传权限。Windows 默认工具路径为 `C:\Program Files (x86)\Tencent\微信web开发者工具\cli.bat`。CLI 令牌如有配置，使用官方环境变量 `WECHAT_DEVTOOLS_CLI_TOKEN`，不要放入命令参数或仓库。

在仓库根目录运行，将示例替换为实际已部署的域名及本次版本说明：

```powershell
# 离线校验：不联网、不构建、不上传
pnpm prepare:wechat --api-base-url https://api.your-domain.tld --version 0.1.0 --desc "首版旅行体验" --check

# 验证公网连通性并准备 production 产物，不上传
pnpm prepare:wechat --api-base-url https://api.your-domain.tld --version 0.1.0 --desc "首版旅行体验"

# 重新验证和构建后，通过官方 CLI 上传代码
pnpm upload:wechat --api-base-url https://api.your-domain.tld --version 0.1.0 --desc "首版旅行体验"
```

正式流程拒绝 HTTP、IP、本机／局域网／示例域名和 URL 规范化绕过，并强制 `VITE_ENABLE_DEV_LOGIN=false`。实际构建前检查域名解析为公网地址、HTTPS `GET /health` 返回正常及未登录 `GET /api/v1/app/me` 返回401；这些检查只证明指定接口的连通性和认证响应，不能证明真实登录、持久化、图片、配对权限或海外地图已就绪。

生产产物写入被忽略的 `artifacts/wechat-release/mp-weixin`，保留 `urlCheck=true`，不覆盖当前同 WiFi 预览的 `dist/build/mp-weixin` 或二维码。`build-manifest.json` 保存版本、API源、AppID与构建哈希。上传必须同时取得官方 CLI 明确成功标记和本次生成的有效 `upload-info.json`，才生成 `upload-receipt.json`；退出码0本身不作为上传成功证据。被强制中断留下锁时，先确认旧进程停止，再删除 `artifacts/wechat-release/release.lock`。

代码上传后，在微信后台「管理 → 版本管理」核对开发版本，设为体验版，再按后台实际规则添加体验成员并分享体验版二维码。CLI `upload` 不会自动完成这些操作；体验版不保证任意微信用户都能访问。类目、备案、隐私指引及审核条件按该账号当前后台提示确认，不因构建成功自动满足。

至少使用两个获授权的微信账号，在手机切换为移动网络后验证登录、私人／共享记录、照片、绑定／解绑和旧图片访问撤销；国内外原生地图另做坐标与底图验收。当前同 WiFi 预览及已验证范围不能直接扩展为上述公网体验结果。
