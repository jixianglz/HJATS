# HJATS .context 目录

> 本目录用于维护项目上下文信息，帮助 AI 工具（Cline、Cursor 等）快速理解项目全貌。

## 文件导航

| 文件 | 说明 | 维护频率 |
|------|------|---------|
| [`PROJECT_SUMMARY.md`](./PROJECT_SUMMARY.md) | 项目一句话定位、版本、目录结构 | 低 |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | 三线程管道架构详解 + 数据流 | 中（架构变更时） |
| [`CURRENT_STATUS.md`](./CURRENT_STATUS.md) | 各模块开发状态、已知问题 | **高（每次变更更新）** |
| [`CHANGELOG.md`](./CHANGELOG.md) | 版本历史更新记录 | **高（每次变更更新）** |
| [`ROADMAP.md`](./ROADMAP.md) | 未来计划、待办事项、需求池 | 中 |
| [`STRATEGIES.md`](./STRATEGIES.md) | 当前交易策略说明 + 开发指南 | 中（策略变更时） |
| [`API_REFERENCE.md`](./API_REFERENCE.md) | 核心类/方法速查 | 中 |
| [`TESTING.md`](./TESTING.md) | 测试指南（16 test, 4 files） | 中 |
| [`COMMANDS.md`](./COMMANDS.md) | 常用命令速查 | 低 |
| [`CONTEXT_CURSOR.md`](./CONTEXT_CURSOR.md) | **AI 入口文件** — AI 接管时首先读取 | **高** |

## 使用规范

1. **每次功能变更后** → 更新 `CURRENT_STATUS.md` + `CHANGELOG.md`
2. **AI 启动时** → 先读 `CONTEXT_CURSOR.md`（快捷摘要），再按需深入
3. **策略修改** → 更新 `STRATEGIES.md`
4. **架构调整** → 更新 `ARCHITECTURE.md`
5. **新增需求** → 更新 `ROADMAP.md`
