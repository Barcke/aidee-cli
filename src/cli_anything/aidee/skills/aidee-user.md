---
name: aidee-user
description: Use Aidee personal and authorized team recordings, self membership checkout and redemption.
---

# Aidee 用户 CLI

先运行 `aidee schema` 查看本次安装版本的命令。`aidee auth login` 隐藏输入本人已有 Key，或 `aidee auth login --browser` 经原网页登录授权。不要把 Key 写入聊天、命令参数、Skill 或 URL。

结果默认 JSON，进度走 stderr。`--jq` 使用系统 jq。HTTP 200 中业务失败也会非零退出。个人列表 `recording list --all --max-pages 10` 有界读取；原文与总结单独查询。

团队先 `team list`，再 `team use <id>`、`space list`、`space recording list --space <id>`；不自动选第一团队。只能读服务端授予的内容，列表可见不代表原文可读，不尝试其他入口绕过拒绝。合并总结只读当前版本，原文不适用。

`redemption preview` 在线预览，`redemption redeem` 预览并经用户确认。`membership plans` 后用 `membership checkout --plan <packageVersionId>` 展示真实价格，经用户确认才创建本人订单；输出支付入口，用户自行付款。非交互需要明确授权再使用 `--yes`。响应超时使用已保存 requestId 执行 `order recover`，不要换 requestId 重复下单。付款和权益到账分别判断。

`--dry-run` 不联网，不兑换、不创建订单。`recording export` 仅导出已有授权内容，`--output-file` 显式落盘，覆盖需要 `--overwrite`。没有生成兑换码、代兑、调整会员、团队成员管理、广播或任意 HTTP path 命令。

退出码：0成功，2参数/jq，3鉴权，4权限，5业务，6网络/限流，7本地安装/升级，130取消。升级用 `update --check` 或 `update`，沿用原uv/pipx安装管理器。Skills同步只管理 aidee-user，保留备份，不覆盖其他技能。
