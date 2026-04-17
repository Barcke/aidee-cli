# AIDEE CLI

AIDEE CLI 是一个面向 AIDEE 后端服务的 Python 命令行工具。它将 AIDEE 的 REST API 封装为结构化终端命令，用于录音、AI 摘要、模板、用户、设备、会员、兑换码及相关运营能力的统一访问。

English version: [README.md](/Users/jeyyu/pyProject/aidee-cli/README.md)

## 项目概述

AIDEE CLI 面向开发者、测试人员、自动化流程以及需要直接接入 AIDEE 服务的集成场景。它以清晰的命令树提供稳定的后端访问方式，适合联调、验证、脚本化调用与批处理操作。

项目提供：

- 基于 `click` 的命令组与子命令体系
- 面向脚本和 Agent 的 `--json` 输出模式
- 本地会话持久化，保存 API 基础地址与 Token
- 基于环境变量的无交互配置方式
- 用于交互探索的 REPL 模式
- 与后端接口高度对应的资源级 API 包装层
- 覆盖核心流程的单元测试与端到端测试文件

## 功能范围

当前代码已覆盖以下命令域与接口能力：

- `config`：本地配置基础地址与 Token
- `session`：查看当前会话状态
- `recording`：录音创建、查询、更新、删除、分页列表、说话人查询、使用统计、批量删除、按文件名查询等
- `summary`：摘要列表、详情、更新、停止、删除
- `template`：摘要模板管理、兑换、额度查询
- `redemption`：兑换码创建、详情查询、兑换记录
- `user`：用户信息、会员信息、资料更新、行业职位设置、删除用户
- `device`：设备列表、主设备查询、绑定、解绑、主设备设置、设备状态查询
- `group`：录音分组创建与管理
- `template-category`：模板分类查询
- `membership`：会员等级、订单、订单状态、升级价格
- `industry` 与 `position`：基础元数据查询
- `word-library`：个人词库与热词管理
- `feedback`：反馈记录查询
- `websocket`：WebSocket 管理能力与消息发送
- `thirdparty`：摘要转第三方文档
- `firmware`：固件升级信息

## 架构说明

项目的大部分业务逻辑位于 AIDEE 后端，CLI 主要承担四类职责：

1. 接收命令行参数并校验输入结构。
2. 从命令参数、环境变量和本地会话中解析运行配置。
3. 以约定的方法、路径、请求头和负载调用后端接口。
4. 输出适合终端阅读或机器消费的结果。

这一结构使项目具备良好的可扩展性。新增接口通常只需要：

1. 在 `core/<resource>.py` 中补充包装函数
2. 在 [aidee_cli.py](/Users/jeyyu/pyProject/aidee-cli/aidee_cli.py) 中注册对应命令
3. 为参数与请求形态补充测试
4. 同步更新文档

## 认证与配置

后端使用 `IM-TOKEN` 请求头，而不是 `Authorization: Bearer`。

配置来源包括：

- 命令行参数：`--base-url`、`--token`
- 环境变量：
  - `AIDEE_BASE_URL`
  - `AIDEE_TOKEN`
  - `AIDEE_REQUEST_TIMEOUT`
  - `AIDEE_SESSION_DIR`
- 本地持久化 session 文件

session 文件位置：

- 如果设置了 `AIDEE_SESSION_DIR`，则使用 `$AIDEE_SESSION_DIR/session.json`
- 否则默认使用 `~/.cli_anything_aidee/session.json`

## 使用示例

### 配置

```bash
cli-anything-aidee config set-base-url http://localhost:8945/aidee-server
cli-anything-aidee config set-token YOUR_IM_TOKEN
cli-anything-aidee config show
```

### 查询用户与录音

```bash
cli-anything-aidee user info
cli-anything-aidee recording list
cli-anything-aidee recording get RECORDING_CODE
```

### 操作摘要

```bash
cli-anything-aidee summary list RECORDING_CODE
cli-anything-aidee summary get 123
cli-anything-aidee summary update 123 --content "Updated summary content"
```

### 输出 JSON

```bash
cli-anything-aidee --json recording list
cli-anything-aidee --json redemption records
```

### 进入交互模式

```bash
cli-anything-aidee
# 或
cli-anything-aidee repl
```

REPL 使用 `shlex.split` 解析输入，因此支持包含空格的参数：

```bash
recording create --title "Quarterly Business Review"
```

## 仓库结构

```text
.
├── aidee_cli.py          # CLI 主入口与命令注册
├── __main__.py           # python -m 入口
├── core/                 # 按资源拆分的 REST API 包装层
├── utils/
│   ├── aidee_backend.py  # HTTP 客户端与错误处理
│   ├── output.py         # 输出格式化
│   └── repl_skin.py      # REPL 展示层
├── tests/
│   ├── test_core.py      # 基于 mock 的单元测试
│   ├── test_full_e2e.py  # 子进程与可选真服务端到端测试
│   └── TEST.md           # 测试计划说明
└── skills/SKILL.md       # Agent 使用说明
```

## 实现说明

### CLI 层

[aidee_cli.py](/Users/jeyyu/pyProject/aidee-cli/aidee_cli.py) 包含顶层 `click` 命令组和全部命令注册，同时负责：

- 暴露 `--json`
- 解析上下文中的 `base_url` 与 `token`
- 在未提供子命令时回退到 REPL 模式
- 将具体 HTTP 调用委托给 `core/`

### 核心 API 层

[core](/Users/jeyyu/pyProject/aidee-cli/core) 目录下的每个模块都对应一类后端资源，函数设计尽量与 REST 接口保持直接映射。

示例：

- [core/recording.py](/Users/jeyyu/pyProject/aidee-cli/core/recording.py)
- [core/summary.py](/Users/jeyyu/pyProject/aidee-cli/core/summary.py)
- [core/redemption.py](/Users/jeyyu/pyProject/aidee-cli/core/redemption.py)

### HTTP 基础层

[utils/aidee_backend.py](/Users/jeyyu/pyProject/aidee-cli/utils/aidee_backend.py) 统一处理：

- 超时控制
- `IM-TOKEN` 请求头注入
- JSON 解码
- 连接错误、超时错误与 HTTP 错误转换

这样命令处理层和资源层可以更专注于接口行为本身。

## 测试

仓库包含：

- [tests/test_core.py](/Users/jeyyu/pyProject/aidee-cli/tests/test_core.py)：session/config 与请求形态相关的单元测试
- [tests/test_full_e2e.py](/Users/jeyyu/pyProject/aidee-cli/tests/test_full_e2e.py)：子进程测试与可选真实服务 E2E

典型执行方式：

```bash
pytest tests/ -v
```

真实服务 E2E 可通过以下条件开启：

- `AIDEE_E2E=1`
- 可访问的 AIDEE 服务
- 有效的 `AIDEE_TOKEN`
