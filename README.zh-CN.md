# Aidee 用户 CLI

查询本人的录音、原文和总结，以及有权访问的团队空间；为本人兑换权益、查看会员套餐和生成付款入口。

需要 Python 3.10+ 和 uv。正式签名发行完成前，可从当前源码安装：

```bash
uv tool install .
aidee --version
aidee auth login                 # 隐藏输入本人已有 API Key
# 或
aidee auth login --browser       # 原网页登录并确认权限
aidee auth login --browser --scope write  # 兑换/下单所需read+write，在网页明确确认
aidee auth status --verify
```

浏览器授权需要配套 Aidee Web/服务端版本。Key 不写入聊天、URL或使用说明。配置优先使用系统钥匙串；无可用钥匙串时使用本机受限权限文件。无浏览器环境可用 `AIDEE_API_KEY`，或 `aidee auth login --key-stdin`。

```bash
aidee recording list --period last_week --limit 20
aidee recording list --week 2026-W01 --timezone Asia/Shanghai
aidee recording get <录音code>
aidee recording transcript <录音code> --all
aidee summary list <录音code>
aidee folder tree

aidee team list
aidee team use <团队ID>
aidee space list
aidee space recording list --space <空间ID> --all
aidee space recording transcript <录音code> --space <空间ID> --all

aidee membership current
aidee membership quota
aidee membership plans
aidee membership checkout --plan <packageVersionId>
aidee order get <订单号>
aidee order wait <订单号>
aidee order recover <原requestId>

aidee redemption preview
aidee redemption redeem
aidee redemption records
```

下单和兑换先展示真实内容，再确认。付款由用户在收银台完成；二维码内容 `codeUrl` 不是通用网页链接。付款后查单，支付成功与权益到账分别展示。请求超时使用已保存的 requestId 恢复原订单，不能盲目重复下单。非交互写操作需要取得用户授权后显式使用 `--yes`；`--dry-run` 不联网、不创建订单、不消费兑换码。

默认 JSON；`--output table` / `--output markdown` 适合终端阅读；`--jq` 使用本机 jq。进度和提醒写入 stderr，HTTP 200 中的业务失败仍会非零退出。分页 `--all` 最多100页、5000条、120秒，截断会返回续页信息。若 `meta.next` 含 `query` 与 `offset`，保留相同筛选/limit，按 query 的页码或游标续查并增加 `--offset <offset>`；offset 只跳过续读首页已收到的条目。团队按真实分享权限读取，列表可见不等于原文可见；合并总结只读当前版本、无原文。

```bash
aidee recording export <录音code> --format md
aidee recording export <录音code> --output-file notes.md
# 已存在文件需要明确 --overwrite
aidee --profile test config set api_base https://test-api.ideamake.cn/aidee-server
aidee --profile test config set team_base https://test-api.ideamake.cn/team-aidee-server
aidee profile use test
aidee schema
aidee schema membership.checkout
aidee skills list
aidee skills sync --dry-run
```

本版保留 `cli-anything-aidee` 核心查询入口和 `user info`、`group list`、`template redeem` 等个人命令别名；新增确认和失败退出码可能影响旧脚本。编辑、删除、设备操作、触发AI任务不属于本版。没有生成兑换码、代兑、调整会员、团队成员管理或任意HTTP接口命令。旧工具不会被自动卸载。

正式发行安装由签名清单验证后交给 uv tool；已有 pipx 安装继续用原管理器。源码或直接 pip 安装不会被自动覆盖。签名与安装来源尚未配置时，升级会明确失败并给出原管理器指引。

```bash
aidee update --check
aidee update
aidee update --sync-skills   # 明确选择同步本CLI的Agent指南
# 现有uv/pipx工具缺回执，且当前版本存在可信签名发行时：
aidee update --register-manager pipx
aidee config set update.auto true
```

默认只检查并提示。自动安装需明确开启、TTY且非CI、非 `--json`、非dry-run；升级调用不发业务请求，下一次命令使用新版。升级保留授权和profile，失败尝试原管理器恢复原固定版本。默认不修改Agent的Skills目录，会单独报告 `skillsSync.status=not_requested`；可手动运行 `aidee skills sync`，或安装/升级时显式选择 `--sync-skills`。每次覆盖本地修改前保留可恢复副本；Skills失败独立提示，已完成的安装/升级状态仍单独展示。

工程构建、发布与验证见 [维护说明](docs/maintainer.md)。
