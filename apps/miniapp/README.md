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
