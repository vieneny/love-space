# 共赴山海手记 · Love Space

两个人共同旅行、共同生活的地图与时间线。Python 后端、Web 管理后台、微信小程序在同一个 Git 仓库维护。

## 工程

- `backend/`：FastAPI、SQLAlchemy、数据库迁移、私有照片、权限与接口测试。
- `apps/miniapp/`：uni-app / Vue 3 / TypeScript，微信端及 H5 本地预览。
- `apps/admin/`：Vue 3 / TypeScript 管理后台。
- `packages/`：接口类型和通用逻辑。
- `docs/API_CONTRACT.md`：开发接口契约。

## 本地开发

先按 backend/README.md 安装和启动 API，再在仓库根目录运行：

```powershell
pnpm install
pnpm dev:admin
pnpm dev:miniapp
```

两个终端分别运行前端。API 默认 `http://127.0.0.1:18100`，后台 `http://127.0.0.1:15173`，小程序 H5 预览 `http://127.0.0.1:15174`。这组端口避开当前电脑已有项目。开发身份登录仅供本地调试；正式微信登录必须配置自己的 AppID、AppSecret。

## 构建与验证

```powershell
pnpm build:admin
pnpm build:h5
pnpm build:miniapp:preview
pnpm build:miniapp
pnpm types:api
pnpm check:release
```

正式上传前填写小程序 `.env.production.local` 的 `VITE_WX_APPID` 与 `VITE_API_BASE_URL`。`check:release` 会阻止空 AppID、旧测试号、HTTP/局域网地址与开发身份登录。产物通过开发者工具导入；预览、上传和设为体验版是不同步骤，应分别核验。

已完成手机同 Wi-Fi 开发预览，用户确认微信登录后进入地图。以下使用示例私网地址 `192.168.1.100`，请替换为你自己的电脑地址，并保持手机同网、后端运行：

```powershell
pnpm preview:wechat --api-base-url http://192.168.1.100:18101
```

后端启动、IP 变更及同 Wi-Fi 操作见 [手机预览说明](docs/PHONE_PREVIEW.md)。使用移动网络或异地手机开发预览，见 [0 元外网预览](docs/PUBLIC_PREVIEW.md)：本机后端 → 受限网关 → 免费临时 HTTPS 隧道，电脑和进程需要持续运行，朋友需按微信规则获得项目开发权限。当前没有上传平台体验版或公开发布，未开通云托管。

## 开源与协作

原创业务代码采用 [MIT 许可证](LICENSE)，第三方依赖和品牌素材的权利边界见 [商用与许可证](docs/COMMERCIAL_AND_LICENSES.md)。开源代码不包括微信、地图等在线服务的商业授权。

所有新提交使用中文主题，例如 `feat: 新增旅行回忆筛选`。克隆后运行 `pnpm setup:hooks` 安装本仓库的提交检查；规范见 [贡献说明](CONTRIBUTING.md)。环境文件、真实凭据、数据库、用户照片和二维码不进入 Git。问题反馈可使用 GitHub Issues；安全问题按 [安全说明](SECURITY.md) 处理，勿公开秘密信息。

## 数据边界

个人私密记录归作者；共享内容仅当前空间成员可见。解绑关闭原空间，个人保留自己发布的内容。照片访问也校验身份和空间，不能放到公共静态目录。地图和时间线展示同一条回忆；虚线表示地点顺序，不是 GPS 轨迹。

请勿提交密钥、用户照片、数据库、编译产物或微信私有配置。第三方开源许可证与地图服务授权分别管理。

开发与交付情况见 [交付记录](docs/DELIVERY.md)，技术和功能见 [架构说明](docs/ARCHITECTURE.md)，注册与资源预算见 [最低成本方案](docs/LOW_COST_DEPLOYMENT.md)，依赖分发见 [商用与许可证](docs/COMMERCIAL_AND_LICENSES.md)。用户已提交个人主体注册，工程内品牌已统一为“共赴山海手记”。
