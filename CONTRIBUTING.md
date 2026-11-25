# 贡献指南 / Contributing

感谢关注 VCardForge！欢迎通过 Issue 报告问题、通过 Pull Request 提交改进。

## 开发环境

只需 Python 3.8+，**无需安装任何依赖**：

```bash
git clone https://github.com/gitstq/VCardForge.git
cd VCardForge
python3 -m unittest discover -s tests -v
```

## 贡献原则

1. **零依赖红线**：`vcardforge/` 包内只允许使用 Python 标准库。
2. **离线红线**：不得引入任何网络请求（号段查询、在线去重服务等一律不要）。
3. **测试覆盖**：新功能必须附带单元测试（`tests/`），修复 Bug 需先写复现用例。
4. **往返无损**：解析 -> 输出的 round-trip 不允许静默丢弃用户数据。
5. **文档同步**：影响行为/接口的改动需同步更新三语 README 中对应小节。

## 提交规范（Angular 风格）

```
feat(parser): 支持 vCard 2.1 裸 TYPE 参数
fix(merge): 修复并查集合并顺序导致的误合并
docs(readme): 补充 birthdays 子命令示例
refactor(writer): 抽取行折叠逻辑为独立函数
test(export): 补充 CSV BOM 用例
```

类型限定：`feat` / `fix` / `docs` / `refactor` / `test` / `chore`。

## 流程

1. Fork -> 新建分支 `feat/xxx` 或 `fix/xxx`
2. 提交改动，确保 `python3 -m unittest discover -s tests` 全绿
3. 发起 Pull Request，描述改动动机与自测方式
