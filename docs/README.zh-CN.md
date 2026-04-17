# AIDEE CLI

AIDEE CLI 是一个面向 AIDEE 后端服务的 Python 命令行工具。它把 AIDEE 的 REST API 封装成可直接调用的终端命令，适合开发联调、测试验证、自动化脚本以及 Agent 场景使用。

English version: [README.md](/Users/jeyyu/pyProject/aidee-cli/README.md)

## 项目简介

这个项目的定位不是“本地做转写和摘要”的离线工具，而是一个对接 AIDEE 服务端能力的轻量 CLI。它的核心价值在于：

- 提供清晰的命令树，直接操作 AIDEE 后端资源
- 支持 `--json` 输出，方便脚本、CI 和 Agent 调用
- 支持本地持久化会话配置，不必每次都传基础地址和 Token
- 支持环境变量配置，适合无交互运行
- 支持 REPL 交互模式，便于联调和手工探索接口
- 以很薄的一层 Python 代码映射后端 API，扩展成本低

## 当前覆盖的能力

从代码来看，这个仓库已经覆盖了 AIDEE 中比较完整的一组业务能力：

- `config`：设置和查看基础地址、Token、本地会话
- `session`：查看当前会话状态
- `recording`：录音创建、查询、更新、删除、分页列表、按文件名查询、批量删除、使用统计、说话人相关能力等
- `summary`：摘要列表、详情、更新、停止、删除
- `template`：摘要模板管理、兑换、额度查询
- `redemption`：兑换码创建、详情查询、兑换记录
- `user`：用户信息、会员信息、资料更新、行业职位设置、删除用户
- `device`：设备绑定、解绑、主设备查询与设置、设备统计
- `group`：录音分组的增删改查与排序
- `template-category`：模板分类查询
- `membership`：会员等级、订单、订单状态、升级价格
- `industry` / `position`：基础元数据查询
- `word-library`：个人词库、热词管理
- `feedback`：反馈记录查询
- `websocket`：WebSocket 管理端相关接口
- `thirdparty`：摘要转第三方文档
- `firmware`：固件升级信息

这意味着它已经不是一个 Demo，而是一个面向真实后端资源的运维/联调型 CLI 雏形。

## 项目设计思路

这个项目的设计很直接，主要分成三层：

### 1. CLI 层

[aidee_cli.py](/Users/jeyyu/pyProject/aidee-cli/aidee_cli.py) 负责：

- 定义 `click` 命令组和子命令
- 处理 `--json`、`--base-url`、`--token`
- 在没有传入子命令时进入 REPL 模式
- 把参数解析后的工作委托给 `core/` 中的 API 包装函数

### 2. 资源接口层

[core](/Users/jeyyu/pyProject/aidee-cli/core) 目录下按资源拆分模块，例如：

- [core/recording.py](/Users/jeyyu/pyProject/aidee-cli/core/recording.py)
- [core/summary.py](/Users/jeyyu/pyProject/aidee-cli/core/summary.py)
- [core/template.py](/Users/jeyyu/pyProject/aidee-cli/core/template.py)
- [core/redemption.py](/Users/jeyyu/pyProject/aidee-cli/core/redemption.py)

每个模块都很薄，基本就是把 Python 函数映射到具体 REST 接口。这个结构的优点是：

- 好维护
- 好扩展
- 好测试
- 与后端接口文档的对应关系清晰

### 3. 基础设施层

[utils/aidee_backend.py](/Users/jeyyu/pyProject/aidee-cli/utils/aidee_backend.py) 统一负责：

- HTTP 请求发送
- `IM-TOKEN` 请求头注入
- 超时控制
- JSON 解析
- 连接错误、超时错误、HTTP 错误转换

[core/session.py](/Users/jeyyu/pyProject/aidee-cli/core/session.py) 负责本地会话持久化，把 `base_url` 和 `token` 保存到本地 JSON 文件。

## 认证与配置方式

这个项目有一个非常关键的点：后端认证不是 `Authorization: Bearer`，而是使用 `IM-TOKEN` 请求头。

配置来源支持三类：

- 命令行参数
  - `--base-url`
  - `--token`
- 环境变量
  - `AIDEE_BASE_URL`
  - `AIDEE_TOKEN`
  - `AIDEE_REQUEST_TIMEOUT`
  - `AIDEE_SESSION_DIR`
- 本地 session 文件

session 文件路径规则：

- 如果设置了 `AIDEE_SESSION_DIR`，则使用 `$AIDEE_SESSION_DIR/session.json`
- 否则默认使用 `~/.cli_anything_aidee/session.json`

## 使用方式示例

### 配置服务地址和 Token

```bash
cli-anything-aidee config set-base-url http://localhost:8945/aidee-server
cli-anything-aidee config set-token YOUR_IM_TOKEN
cli-anything-aidee config show
```

### 查询用户和录音

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

### 机器可读输出

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

REPL 内部使用 `shlex.split` 解析命令，所以支持带空格参数：

```bash
recording create --title "Quarterly Business Review"
```

## 仓库结构说明

```text
.
├── aidee_cli.py          # CLI 主入口，注册所有命令
├── __main__.py           # python -m 入口
├── core/                 # 按资源拆分的 REST API 包装层
├── utils/
│   ├── aidee_backend.py  # HTTP 请求和错误处理
│   ├── output.py         # 输出格式化
│   └── repl_skin.py      # REPL 展示与交互外观
├── tests/
│   ├── test_core.py      # 单元测试
│   ├── test_full_e2e.py  # 子进程与可选真服务 E2E
│   └── TEST.md           # 测试计划
└── skills/SKILL.md       # Agent 使用说明
```

## 适合公开发布时怎么介绍这个项目

如果这是准备公开发布到 Git 的 `aidee-cli` 工具，我建议把它定义为：

> A backend-oriented Python CLI for interacting with the AIDEE platform, covering recordings, summaries, templates, memberships, redemption workflows, and operational endpoints through a scriptable command-line interface.

换成中文，就是：

> 一个面向 AIDEE 平台后端能力的 Python 命令行工具，通过可脚本化的命令接口，统一访问录音、摘要、模板、会员、兑换码以及部分运维类接口。

这个定义比较准确，因为它既表达了业务价值，也没有夸大为“完整 SDK”或“独立 AI 产品”。

## 当前仓库的真实状态

从代码实际情况看，这个仓库已经具备公开介绍项目能力的基础，但还有几个事实需要在文档里说清楚：

### 1. 这是源码仓库，不是完整打包产物

当前代码的 import 路径使用的是 `cli_anything.aidee` 命名空间，但仓库里还没有看到独立发布常见的：

- `pyproject.toml`
- `setup.py`
- console script entry point
- 明确的依赖声明

所以它现在更像“可嵌入现有工程的 CLI 源码”，而不是已经可以直接 `pip install` 的独立发行版。

### 2. 文档需要避免写死错误的安装方式

现有旧 README 中有一些历史路径，例如 `cd agent-harness`。这类内容如果继续保留，会让公开仓库的使用者困惑。

### 3. 测试文件存在，但当前环境未完成执行

仓库里有：

- [tests/test_core.py](/Users/jeyyu/pyProject/aidee-cli/tests/test_core.py)
- [tests/test_full_e2e.py](/Users/jeyyu/pyProject/aidee-cli/tests/test_full_e2e.py)

但本地当前 Python 环境缺少 `pytest`，因此这次只能做代码级一致性检查，不能在当前环境里完整跑通测试。

## 后续适合补齐的公开发布项

如果你下一步是把它真正做成公开可安装的工具，建议优先补这些内容：

1. 增加 `pyproject.toml`
2. 声明依赖，例如 `click`、`requests`
3. 配置 `cli-anything-aidee` 的 entry point
4. 增加 LICENSE
5. 增加 CONTRIBUTING 或开发说明
6. 清理 `.DS_Store`、`__pycache__` 等不应提交的内容
7. 评估是否公开 `websocket` 这类偏管理端能力

## 这个项目适合谁

适合：

- AIDEE 后端接口联调人员
- QA 和测试工程师
- 自动化脚本作者
- 需要 JSON 输出的 Agent / workflow 集成场景
- 想基于现有后端快速做 CLI 封装的开发者

不适合：

- 期待本地离线转写/摘要能力的人
- 期待桌面客户端的人
- 期待已经完整打包并可直接发布到 PyPI 的用户

## 总结

这个仓库的优点是结构直接、职责清晰、扩展成本低，已经有一个不错的 API CLI 雏形。对于公开发布来说，最重要的不是再堆新功能，而是把项目定位、运行前提、支持范围和当前发布状态写清楚。

本中文文档与英文 README 一起，目标就是把这件事说明白。
