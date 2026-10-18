# 0 元临时外网开发预览

使用自己的电脑运行后端，经本机受限网关和 Cloudflare Quick Tunnel 提供临时 HTTPS 地址。无需购买服务器或域名；不创建云托管环境。这条路径用于小范围开发调试，不是微信正式体验版或对公众稳定运营的部署。电脑、网络和三个服务必须持续运行。

## 前提

先准备已能真实微信登录的隔离手机预览后端，关闭开发身份登录与管理员登录；不要复用旧项目数据库。现有后端监听哪个私网地址，就把该地址显式传给启动脚本；绑定 WLAN 地址的服务不能假定可通过 127.0.0.1 访问。

启动脚本不读取或显示 AppSecret、JWT、管理员密码等配置，也不通过有副作用的登录探针验证开关；源后端配置由维护者启动时核对。受限网关另外强制屏蔽开发登录、后台和文档路由。不要直接将源后端端口挂到公网。

需要 backend/.venv/Scripts/python.exe、已安装的后端依赖，以及从 [Cloudflare 官方发布页](https://github.com/cloudflare/cloudflared/releases) 下载并校验的 cloudflared.exe。默认工具位置为 artifacts/tools/cloudflared.exe，也可通过参数指定其他已校验路径。脚本只检查文件存在，不代替官方摘要或来源校验。

## 启动临时入口

在仓库根打开 PowerShell，地址中的 `192.168.1.100` 只是示例，替换为本机后端实际监听的私网地址：

```powershell
# 只检查地址格式和本地可执行文件，不启动任何进程。
.\scripts\start-public-preview.ps1 -BackendOrigin 'http://192.168.1.100:18101' -CheckOnly

# 实际启动；可加 -CloudflaredPath 'C:\工具目录\cloudflared.exe'。
.\scripts\start-public-preview.ps1 -BackendOrigin 'http://192.168.1.100:18101'
```

脚本先以隐藏窗口启动 `127.0.0.1:18102` 的受限网关，通过进程归属与 `/health` 检查后才启动隧道。隧道固定使用本机已验证可连通的 HTTP/2，并只连接该网关；源后端地址通过 PREVIEW_API_UPSTREAM 传给网关，临时设置会在启动后恢复。可执行文件、工作目录和日志路径分别传给 Start-Process，不经 cmd.exe 拼接；命令参数本身不包含文件路径。

网关仅允许 `/health` 与正常 `/api/v1/app/*`，屏蔽开发登录、管理 API、Swagger/OpenAPI 与其他路径；上传大小也受限制。Windows 虚拟环境的 python.exe 可能另启真正监听端口的 Python 子进程；脚本只沿本次启动器的父子关系跟踪指定网关模块，并核对创建时间和实际路径，以真正监听进程判定就绪。进程路径暂时为空时使用同 PID 和创建时间匹配的 CIM 信息辅证，无法核对则停止操作。启动等待默认 45 秒，最多可设为 50 秒；失败清理前再次核对身份，先子进程再启动器，不停止源后端、旧预览或其他项目。已有网关监听、仍存活的上次预览或另一个启动流程会被拒绝，避免意外接管进程。

只有临时 HTTPS `/health` 已通过检查，脚本才输出 Gateway PID、Tunnel PID 和随机 Public URL。日志及进程定位保存在被 Git 忽略的 artifacts/public-preview/，最新定位为 artifacts/public-preview-state.json。不要把这些日志、二维码、真实私网地址或临时 URL 提交到仓库。

## 重新生成微信二维码

用本次脚本输出的随机地址替换下面示例：

```powershell
pnpm preview:wechat --api-base-url 'https://your-tunnel.trycloudflare.com' --check
pnpm preview:wechat --api-base-url 'https://your-tunnel.trycloudflare.com'
```

预览构建强制关闭开发身份登录，生成二维码后从微信扫码。手机如提示域名不合法，按该版本微信的菜单进入开发调试，开启调试后重新进入。测试手机关闭 Wi-Fi、使用移动网络，再核验真实微信登录、地图、照片上传和展示，以及两账号的私密/共同空间隔离；二维码生成和电脑能访问 `/health` 都不能代替手机验证。

朋友使用当前开发预览码，需要先具有这个小程序的开发权限。维护者在微信小程序后台“用户身份 → 成员管理 → 添加成员”，按后台实际角色给指定朋友开发权限，朋友接受绑定后扫码。个人主体官方上限为15个项目成员、15个体验成员；项目开发权限不应向无关人员开放。体验成员对应平台体验版，不能保证只添加体验成员就能使用开发预览码。目前没有核实到普通朋友免项目权限的“好友调试”路径，因此不要承诺二维码发给任意人即可使用。成员规则见[微信官方开发前准备](https://developers.weixin.qq.com/miniprogram/introduction/#开发前准备)。

临时域名并不代表已满足微信正式服务器域名、备案或版本发布要求。不要将本流程描述为已上传平台体验版。隧道域名变化后，旧小程序包仍指向旧地址，需要重新构建并扫码。

## 停止与重启

先读取 artifacts/public-preview-state.json，核对记录的 PID、startTimeUtc 和 executablePath 与当前进程一致，再只停止本次 cloudflared、网关服务进程及其启动器。formatVersion=2 的记录区分 gateway、gatewayLauncher 和 gatewayChildren；相同 PID 只处理一次。PID 可能被系统复用，不能只复制旧 PID 直接结束进程；不要结束源后端或其他项目服务。

停止 cloudflared 后，临时 URL 随即失效。停止本次网关后可重新运行启动脚本；每次新建 Quick Tunnel 都会得到新域名。若脚本在关闭 PowerShell、断电或强制中断时未完成清理，先按状态文件确认遗留进程再处理，不能通过批量结束 python/cloudflared 或扫描其他项目解决。

## 已知限制

[Cloudflare Quick Tunnels 官方文档](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)于 2026-10-18 核实：无需 Cloudflare 账号或自有域名；仅供测试开发，无可用性保证；最多 200 个同时在途请求，超出返回 429；不支持 SSE；停止进程即失效，重建时域名变化。

任何拿到临时地址的人都可以访问入口，正常业务仍依赖服务端微信登录与权限隔离。不要公开分享真实情侣记录、定位或照片。官方新增 `--allowed-mail` 需要交互浏览器验证，不支持非交互客户端，因此本小程序 API 隧道不使用该选项。国内移动网络对临时域名的可达性、速度与微信行为必须实测，不能保证稳定。

生产部署及一致备份工具保留在 deploy/，供未来需要长期运营时另行评估；本次临时预览不购买或开通这些资源。
