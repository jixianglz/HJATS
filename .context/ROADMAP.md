# HJATS 路线图

> 最后更新: 2026-06-27

## 短期目标（1-2周）

### 高优先级

- [x] Git 初始化 + 首次提交
  - 初始化 Git 仓库
  - 清理敏感文件（检查 .env 是否被跟踪）✅ 安全
  - 添加 .context/ 到仓库
- [x] 清理技术债务
  - 更新 Inittxt.txt → 已填充导航内容
  - .gitignore 覆盖敏感文件 ✅ 已确认
- [x] 单元测试框架搭建（pytest, 16 tests, 4个测试文件）
  - 引入 pytest
  - 为核心模块写测试

### 中优先级

- [ ] 实盘模式验证
  - 测试 BinanceBroker
  - 完善 LiveEngine 风控
- [ ] 配置外部化
  - 策略参数从 config.ini 读取
  - MongoDB 密码移到 .env
