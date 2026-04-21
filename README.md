# AIDEE CLI

AIDEE CLI 是一个面向 AIDEE 服务的命令行工具，适合客户或运维同学通过终端快速完成基础查询与常用操作，例如查看账号信息、查询录音、查看摘要、兑换权益等。

本文档以日常使用为主，只保留基础说明和基础案例。

更多中文说明可参考 [README.zh-CN.md](/Users/jeyyu/pyProject/aidee-cli/README.zh-CN.md)。

## 适用场景

- 查看当前账号信息
- 查询录音列表与录音详情
- 查看摘要结果
- 使用兑换码查询权益信息
- 查看自己的兑换记录

## 认证方式

支持以下两种认证方式，二选一即可：

- `Token`：通过 `IM-TOKEN` 认证
- `API Key`：通过 `X-Api-Key` 认证

可使用以下任一方式配置：

- `AIDEE_TOKEN`
- `AIDEE_API_KEY`

一般情况下，只需要提供其中一个，不需要同时配置。

## 基础配置

默认服务地址：

```text
https://api.aidee.me/aidee-server
```

首次使用前，建议先设置服务地址和认证信息。

使用 Token：

```bash
cli-anything-aidee config set-base-url https://api.aidee.me/aidee-server
cli-anything-aidee config set-token YOUR_IM_TOKEN
```

使用 API Key：

```bash
cli-anything-aidee config set-base-url https://api.aidee.me/aidee-server
cli-anything-aidee config set-api-key YOUR_API_KEY
```

查看当前配置：

```bash
cli-anything-aidee config show
cli-anything-aidee session status
```

## 基础使用案例

### 1. 查看账号信息

```bash
cli-anything-aidee user info
```

### 2. 查看录音列表

```bash
cli-anything-aidee recording list
```

如果希望控制分页：

```bash
cli-anything-aidee recording list --page 1 --size 20
```

### 3. 查看某条录音详情

```bash
cli-anything-aidee recording get RECORDING_CODE
```

### 4. 创建一条录音记录

```bash
cli-anything-aidee recording create --title "客户沟通纪要"
```

### 5. 查看某条录音的摘要列表

```bash
cli-anything-aidee summary list RECORDING_CODE
```

### 6. 查看某条摘要详情

```bash
cli-anything-aidee summary get SUMMARY_ID
```

### 7. 查询兑换码可兑换内容

```bash
cli-anything-aidee redemption code-detail CODE_STRING
```

说明：这里是查询兑换码详情，不是创建兑换码。

### 8. 查看当前账号的兑换记录

```bash
cli-anything-aidee redemption records
```

如果需要按来源筛选：

```bash
cli-anything-aidee redemption records --redeem-source aideeApp
```

## 常用命令

```bash
cli-anything-aidee --help
cli-anything-aidee --version
cli-anything-aidee config show
cli-anything-aidee user info
cli-anything-aidee recording list
cli-anything-aidee summary list RECORDING_CODE
cli-anything-aidee redemption code-detail CODE_STRING
```

## 交互模式

可以直接进入交互模式：

```bash
cli-anything-aidee
```

或者：

```bash
cli-anything-aidee repl
```

如果参数中包含空格，请使用引号：

```bash
recording create --title "一对一客户回访"
```

## 环境变量方式

如果不想把认证信息写入本地配置，也可以直接使用环境变量：

使用 Token：

```bash
export AIDEE_BASE_URL="https://api.aidee.me/aidee-server"
export AIDEE_TOKEN="YOUR_IM_TOKEN"
cli-anything-aidee user info
```

使用 API Key：

```bash
export AIDEE_BASE_URL="https://api.aidee.me/aidee-server"
export AIDEE_API_KEY="YOUR_API_KEY"
cli-anything-aidee recording list
```

## 说明

- 文档中的命令名为 `cli-anything-aidee`
- 本工具支持 `Token` 和 `API Key` 两种认证方式，任选其一即可
- 当前客户文档仅展示基础能力和常用案例
- 如需查看全部命令，请执行 `cli-anything-aidee --help`
