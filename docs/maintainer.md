# CLI 维护与验证

唯一用户发行源是本仓库，namespace `cli_anything.aidee`，distribution `cli-anything-aidee`；入口 `aidee` 和兼容入口 `cli-anything-aidee`。不要与后端 agent-harness 安装到同一环境。

```bash
uv sync --extra test --locked
uv run pytest -q
uv build --wheel
uv run python scripts/verify-wheel.py
```

测试只使用临时配置、虚构Key与127.0.0.1 mock；不读取真实session/keyring。CI配置macOS/Linux/Windows五架构、Python3.10/3.12；实际云端执行结果仍以CI为准，不把配置当成通过。测试包含原core只读契约、HTTP200业务失败、origin绑定/唯一凭据、cursor大ID、确认/dry-run、原订单恢复、PKCE状态、签名、管理器故障恢复以及本次wheel隔离安装。管理器单元故障注入不能冒充所有平台实际恢复证明。

## 认证与API

默认Key通过 `X-Api-Key`；token只在显式模式使用，不混发。Web地址可用 `web_base` 配置；个人和团队地址在同一profile但凭据绑定两者。新增接口是配套后端契约，不表示线上已部署。`schema` 列出本次版本注册的用户命令，不提供raw任意path。

本版不分配 Api-Version：跨服务协议号未冻结；不借 X-App-Version 伪装契约版本。所有雪花ID、游标ID和分金额经JSON输出转十进制字符串。

## 发布

GitHub Actions：main/PR校验，tag `vX.Y.Z` 稳定通道，`vX.Y.Z-rc.N` preview。需要受保护的 `cli-release` environment、`AIDEE_RELEASE_SIGNING_KEY_PEM`、`AIDEE_RELEASE_PUBLIC_KEY_PEM`、OSS凭据/bucket。公钥与私钥必须匹配才允许构建，私钥不写盘或打包。维护者须将公钥配置为可信根；本地源码未伪造生产公钥。

`scripts/release.py` 使用现成cryptography Ed25519生成manifest原始UTF-8字节签名，发行包内注入可信公钥和build commit。产物为一份通用wheel，不伪称五个平台二进制。manifest字段固定：schemaVersion/version/channel/commit/pythonRequires/publishedAt/releaseNotesUrl/artifacts[{filename,url,sha256,size}]。

版本产物先上传不可变目录，`promote.py`回读实际wheel校验，最后晋级稳定或preview清单。客户端未通过签名、版本、平台、大小和哈希校验不会安装；两个清单文件晋级过程的临时不一致会验签失败，不执行包。正式tag前应完成对应环境的必要验收，并核对受保护环境的发布配置。

默认发行base：`https://ai-agent.ideamake.cn/aidee-cli`。安装脚本执行已嵌公钥的install.py；`AIDEE_RELEASE_BASE`可指定测试源，显式 `--public-key-file`仅用于自行确认的可信测试公钥。

安装器记录环境、manager、distribution、版本、commit、原wheel和通道。更新器交叉检查包元数据/解释器/管理器目录；未知来源仅提供指引。更新前校验并缓存新旧固定wheel，管理器升级失败后尝试装回旧包并验证版本；恢复失败返回rolledBack=false，不能说原子回滚已完成。凭据/profile在工具环境外，不随工具升级删除。

版本检查24小时缓存，仅TTY人工调用可提示；明确opt-in才会在业务请求前发起独立升级并退出。非TTY、CI、显式JSON、dry-run或 `AIDEE_NO_UPDATE=1` 不自动安装。无可用签名源不阻断正常查询。

## 环境验收

环境验收覆盖：目标Aidee/team/Web部署、网关Key入口、实际空间角色/shareScopes裁剪、测试商户NATIVE/H5、生产可信公钥与OSS权限、三平台uv/pipx真实安装/恢复。测试mock和本地wheel通过不能证明上述外部环境已完成。

时间筛选：`--timezone`表示用户输入/周期的IANA时区；无offset输入按该zone解释，有offset输入按其真实时刻解释。再转为服务`apiTimezone`（默认Asia/Shanghai）后才去offset，对齐原LocalDateTime查询契约；可通过config set apiTimezone配置确认后的服务语义。团队cursorSortTime保持原服务值，不参与此转换。

## 安装与兼容验证

能力与边界见[能力说明](requirement-coverage.md)。wheel验收使用无全局site-packages的干净venv并正常安装依赖；POSIX用标准symlink方式兼容独立Python，Windows保留标准redirector。独立子进程强制禁用系统TZ路径验证tzdata，强制cp1252输出设置验证产品真实入口UTF8。

CI的五个官方runner为 `ubuntu-24.04` x64、`ubuntu-24.04-arm` arm64、`macos-15-intel` x64、`macos-15` arm64、`windows-2022` x64，分别跑Python3.10/3.12并断言实际架构。标签依据[GitHub官方runner表](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)和[setup-python](https://github.com/actions/setup-python)；发布结果以作业实际状态为准。OSSutil 2.3.0的固定下载地址、SHA256和解压路径保存在工作流中。

```bash
# 完全临时的签名发行／真实管理器故障演练
uv run python scripts/rehearse-install.py --manager uv
uv run python scripts/rehearse-install.py --manager pipx
```

已有无回执的工具仅在用户明确执行 `aidee update --register-manager uv` 或 `pipx` 时尝试登记：同一实际管理器、发行包/解释器目录与版本一致，当前版本不可变签名manifest有效，当前包每个wheel文件字节相同。不存在签名旧发行、源码editable、未知环境或不一致时拒绝，不猜来源。

安装/升级默认Skills结果为not_requested，不写Agent目录；只有明确`--sync-skills`才同步，失败独立warning。每次覆盖用户编辑保留原始字节备份，包含重复编辑和已有备份冲突。发布失败恢复包含manifest/signature和三个可变bootstrap；所有旧字节/缺失状态回读确认才报告恢复。进程强杀或恢复失败仍需人工检查，不宣称OSS事务原子性。preview仅改自己的bootstrap。

发行地址与存储必须配套：公开base为`https://ai-agent.ideamake.cn/aidee-cli`，OSS前缀为`aidee-cli`，版本对象在`aidee-cli/versions/<version>/`，通道在`aidee-cli/stable/`或`aidee-cli/preview/`。`OSS_BUCKET`、访问凭据和深圳region由受保护CI环境注入，须对应该CDN实际源站及已验证权限；不沿用其他插件目录的写权限假设。工作流显式传同一`AIDEE_RELEASE_BASE`和`OSS_RELEASE_PREFIX`，安装器和客户端默认值与之相同。个人/团队API地址独立于发行地址。
