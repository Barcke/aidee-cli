# Tasks

## Plan

- [x] Review the current repository structure, entrypoints, and command registrations
- [x] Verify the real authentication model from code and confirm `token` / `api key` behavior
- [x] Rewrite the root `README.md` with more formal public-facing wording
- [x] Replace outdated install/run instructions with command information that matches the source tree
- [x] Validate the final README against code and record the verification result

## Review

- 根据用户纠正，重新收缩 README 为面向客户的中文基础使用文档，不再使用英文主说明。
- 已核对源码确认 `redemption` 仅包含 `code-detail` 和 `records`，不存在“兑换码创建”命令，相关错误描述已移除。
- 已删除不适合客户文档的深度内容，例如完整能力盘点、底层实现、测试说明和高权限命令导向。
- 已保留基础配置、认证方式和常见场景案例，包括账号查询、录音查询、摘要查询、兑换码详情与兑换记录。
- 已再次使用帮助命令校对案例对应的命令面：
  - `python3 -m cli_anything.aidee.aidee_cli user --help`
  - `python3 -m cli_anything.aidee.aidee_cli recording --help`
  - `python3 -m cli_anything.aidee.aidee_cli summary --help`
