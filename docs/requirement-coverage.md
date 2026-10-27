# 用户 CLI 能力与验证边界

本仓库提供面向本人和已授权团队的用户CLI。下面列出实现位置、兼容范围与需要独立环境验收的边界。

| 能力 | 实现位置 | 覆盖与边界 |
| --- | --- | --- |
| Python3.10+／Click／原core复用／namespace／两个入口 | `pyproject.toml`、`setup.py`、`src/cli_anything/aidee/core` | 标准wheel；原核心本人查询及本人兑换兼容别名，明确拒绝已移除命令；不迁Go、不做独立二进制 |
| 现有Key／显式token／PKCE／profile／本机退出 | `auth.py`、`settings.py`、`aidee_cli.py` | 校验真实本人后保存；read默认、write显式且网页确认；唯一权威store/generation、origin绑定、logout tombstone；不新签导入Key、不自动撤销旧Key |
| 状态和诊断 | `aidee_cli.py` 的auth/status/whoami/doctor | 安全身份与实际权限、配置/网络/权限失败明码及提示；doctor兼容显式token，不回显凭据 |
| 个人录音列表／详情／目录／已有原文和总结 | `aidee_cli.py`、`core/recording.py`、`core/summary.py` | 真正服务字段/分页；周期与明确时区；补指定ISO周 `--week YYYY-Www`，互斥period/from/to，跨年W01/W53按ISO年校验；用户zone转apiTimezone，游标不换算 |
| 团队发现／选择／TEAM空间／录音／总结 | `aidee_cli.py` 的team/space | team list无需选择；空间带X-Team-Id；详情真实`/spaces/{id}`白名单；仅TEAM和所选团队；team:总结ID编码；合并总结只读当前版本，原文不适用 |
| 本人会员／套餐／兑换预览和执行／记录 | `core/membership.py`、`core/redemption.py`、`aidee_cli.py` | 复用原已发布套餐及本人接口；写权限自省与confirm/yes；无管理、生成码、代兑或团队管理 |
| checkout／查单／原requestId恢复／等待权益 | `aidee_cli.py` 的membership/order | 先保存意图、真实金额确认、POST一次；丢响应UNKNOWN+原requestId恢复；READY原付款参数；checkoutUrl原账号登录；支付与权益分开；PAID+FAILED/FAILURE立即结束且不重下单，PENDING继续等，UNKNOWN不冒充成功 |
| 输出／错误／大ID／jq | `output.py`、`errors.py`、`client.py` | JSON信封及约定退出码；HTTP200错误非零；1005/明确风控→4，429及4290/4291/4292/4293/4299→6；只读有限重试且不提前违反Retry-After；table/markdown仅显示层转义控制字符，JSON/原文保持值；真实入口UTF8 stdout/stderr |
| 有界分页与可实际续读 | `client.py`、`list_options` | 默认20／最多100页5000项120秒；截断next与原因；补`--offset`只跳续读首页，和相同limit/page或cursor使用；中途失败非零并带partial |
| 已有原文／总结txt/md/json导出 | `export.py`、recording/space export | 不新增音频或AI任务；默认stdout；显式文件与overwrite；完整后同目录原子写入、UTF8/LF、无损内容；权限由原服务约束 |
| schema／Agent Skills | `metadata.py`、`skills.py`、命令schema | 注册元数据自动含真实选项；Skills只管理自身指南，逐次本地编辑先备份原始字节，备份不冲掉旧版；UTF8源/文件/重定向 |
| 正式安装／已有uv或pipx来源 | `scripts/install.py/.sh/.ps1`、`updates.py` | 现成管理器与Ed25519库；验签和wheel校验后安装，记录receipt；未知/源码环境不自动覆盖；显式`update --register-manager uv\|pipx`仅在当前签名wheel逐文件相同、元数据/解释器/管理器目录可证时登记 |
| 升级／自动检查与明确opt-in | `updates.py`、`aidee_cli.py` | 24h缓存，显式check/update；自动安装仅已开启+TTY+无JSON/CI/dry-run；当次不发业务；同管理器旧固定wheel恢复并版本/原生加密依赖健康检查，恢复未证实不宣称成功 |
| 安装升级联动Skills | installer/update `--sync-skills` | 默认独立报告not_requested及手动命令，不触碰目录；显式选择才同步；Skills失败独立warning，已安装/已升级结果单独保留 |
| 自动构建／签名／公开存储／稳定通道保护 | `.github/workflows/cli.yml`、`scripts/release.py/promote.py` | 固定manifest原始bytes签名，单wheel、不可变版本目录、旧tag不得回退通道；preview安装器独立；原pair及3个bootstrap保存，任一上传/回读失败尝试恢复并公众回读；多OSS对象不承诺绝对原子，恢复不能确认明确报错 |
| 五目标架构与锁依赖 | CI、`uv.lock`、`scripts/verify-wheel.py` | 官方runner配置见维护说明；真正无全局site-packages的wheel安装；标准tzdata依赖支持无系统IANA数据库的环境；配置与实际平台结果分别核验 |

## 验证与环境验收

`uv sync --extra test --locked`、构建wheel后运行完整测试。测试只使用虚构Key、临时配置与本地HTTP服务；签名测试使用临时测试密钥，不读取真实钥匙串。安装、升级与故障演练命令见[维护说明](maintainer.md)。

CI配置五架构与Python3.10/3.12；云作业和目标平台实际管理器结果应单独核验。生产发行需要受保护的签名配置、正确的公开OSS路径和真实回读。业务能力依赖配套Aidee/team/Web版本、网关主体与空间分享权限、实际商户NATIVE/H5和支付权益链路。

Go、设备/编辑删除/新AI任务和管理员能力不属于本版。Api-Version仍需跨服务正式协调，CLI不会自行分配。
