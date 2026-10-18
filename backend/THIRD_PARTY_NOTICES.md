# Python 后端第三方许可说明

本项目原创业务代码采用根目录 LICENSE 中的 MIT 许可证。第三方依赖保留各自版权与许可证，不因被本项目调用而改为 MIT。

以下版本与许可于 2026-10-18 通过本地已安装包的 `*.dist-info/METADATA`、许可证文件及 backend/uv.lock 核对；未为核对额外安装包或查询外部服务。表格覆盖直接运行时依赖及显式安装的 psycopg-binary，不代表传递依赖、平台特定 wheel 或系统组件的完整清单。升级后需重新核对锁定版本与实际交付包。

| 组件 | 核对版本 | 本地元数据中的许可 |
| --- | --- | --- |
| FastAPI | 0.143.3 | MIT |
| Uvicorn | 0.54.0 | BSD-3-Clause |
| SQLAlchemy | 2.1.5 | MIT |
| Alembic | 1.20.0 | MIT |
| psycopg | 3.3.6 | LGPL-3.0-only |
| psycopg-binary | 3.3.6 | LGPL-3.0-only |
| pydantic-settings | 2.16.0 | MIT |
| PyJWT | 2.15.1 | MIT |
| pwdlib | 0.3.1 | MIT |
| python-multipart | 0.0.32 | Apache-2.0 |
| Pillow | 12.3.0 | MIT-CMU |
| HTTPX | 0.28.1 | BSD-3-Clause |
| tzdata | 2026.5 | Apache-2.0（包内时区数据另有来源说明） |

## psycopg 与二进制分发

上游项目为 [psycopg](https://github.com/psycopg/psycopg)。本地两个包的 `METADATA` 均明确声明 `License-Expression: LGPL-3.0-only`，随包许可位于：

```text
psycopg-3.3.6.dist-info/licenses/LICENSE.txt
psycopg_binary-3.3.6.dist-info/licenses/LICENSE.txt
```

这些文件包含 LGPL 第 3 版文本，并说明其纳入 GPL 第 3 版的相关条款。复制或再分发 wheel、预装环境或容器镜像时，不要删除上游许可证、版权与包内第三方声明；应随实际交付物保留完整适用文本，并核对 LGPL 关于对应源码、修改库源码、库替换或重新链接以及必要告知等适用义务。不能把本说明替代为完整许可证，也不能笼统声称所有后端依赖均为 MIT。

调用 LGPL 库和修改该库本身是不同的情况；应按实际链接、修改与分发方式评估义务，不能直接推断所有原创业务代码必须改用 LGPL。本仓库没有在源码树中复制上述 wheel；安装命令和锁文件不等于已完成后续二进制交付的许可审查。

## 其他交付内容

`psycopg-binary` 的实际平台构建及其链接或捆绑的 libpq、加密库等组件，PostgreSQL 镜像、Python、uv 与基础镜像中的系统组件，都可能带有额外许可和声明。分发容器或离线安装包时，应根据最终镜像和平台逐项保留上游文件，不能只核对这里的 Python 包表格。开发/测试依赖（例如 pytest）与其他传递依赖也需按实际交付范围核对。

前端声明继续保留在 docs/THIRD_PARTY_NOTICES.txt 和小程序静态声明中；地图、微信平台及 AI 品牌素材的在线服务条款见 docs/COMMERCIAL_AND_LICENSES.md。本文件是来源与义务提示，不是完整法律意见或商业使用保证。
