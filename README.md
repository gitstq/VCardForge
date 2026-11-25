<div align="center">

# 🎴 VCardForge

**零依赖 · 离线优先的 vCard (.vcf) 通讯录工具箱**

*Zero-dependency · Offline-first vCard toolkit — Python 标准库实现，库 + CLI 双形态*

[简体中文](README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md)

`Python 3.8+` · `0 依赖` · `0 网络请求` · `MIT`

</div>

---

## 🎉 介绍

**VCardForge** 把散落在手机、微信、Outlook 导出文件里的 `.vcf` 通讯录变成可编程、可清洗、可审计的数据。它用纯 Python 标准库自研实现了 vCard 2.1 / 3.0 / 4.0 的完整解析与生成，专为「数据不出本机」的场景设计。

与其他方案不同：

- ✅ **零第三方依赖** —— 只用标准库，`pip install` 秒装，也能直接复制源码使用
- ✅ **完全离线** —— 规范化、去重、校验全部本地完成，通讯录数据永不出机
- ✅ **兼容脏数据** —— vCard 2.1 的 QUOTED-PRINTABLE、Outlook 的 `item1.` 分组、iOS 的多 TYPE 参数、行折叠等历史包袱全都能啃下
- ✅ **往返无损** —— 解析 → 输出保留所有原始属性，不丢字段

## ✨ 特性

| 模块 | 能力 |
|------|------|
| 🔍 **解析** | vCard 2.1 / 3.0 / 4.0；行折叠还原；QUOTED-PRINTABLE / BASE64 解码；`item1.` 分组剥离；损坏文件局部容错 |
| ☎️ **号码规范化** | E.164 风格统一；中国手机号 / 座机识别；全角数字纠偏；跨格式（`+86 138...` vs `138-0013-8000`）归一 |
| 🧬 **智能去重** | 手机号 0.60 + 邮箱 0.30 + 姓名 0.10 加权评分；并查集传递合并；组内保留信息最完整的一条 |
| 📦 **多文件合并** | 任意多个 .vcf 一次合并去重，输出 vCard 3.0 / 4.0 |
| 📊 **导出** | JSON（含规范化号码）/ CSV（UTF-8 BOM，Excel 直接打开不乱码） |
| 🛡️ **校验** | 10 条规则（R01–R10）：缺 FN/N、非法 VERSION、坏日期、重复号码、坏邮箱……可作 CI 门禁（错误时退出码 2） |
| 🎂 **生日提醒** | 未来 N 天生日列表，闰年 2/29 自动回退到 2/28 |
| 🔄 **版本转换** | 2.1 / 3.0 → 3.0 / 4.0，自动补 UID / FN / N |

## 🚀 快速开始

**方式一：pip 安装**

```bash
pip install .
```

**方式二：单文件运行（零安装）**

```bash
# 下载 Release 中的 vcardforge-*.pyz 后：
python3 vcardforge-1.0.0.pyz --help
```

**方式三：库方式集成**

```python
from vcardforge import parse_file, dedup_contacts, write_file

contacts = parse_file("通讯录.vcf")
clean, report = dedup_contacts(contacts)
print(f"输入 {len(contacts)} -> 去重后 {len(clean)}")
write_file(clean, "干净.vcf", version="4.0")
```

## 📖 使用指南

### CLI 六大子命令

```bash
vcardforge info      通讯录.vcf                # 📊 概览：人数 / 版本分布 / 字段统计
vcardforge validate  通讯录.vcf --detail       # 🛡️ 10 条规则校验，错误退出码 2
vcardforge merge a.vcf b.vcf -o merged.vcf -v # 🧬 合并 + 智能去重
vcardforge export    通讯录.vcf -o out.csv     # 📦 导出 CSV / JSON
vcardforge birthdays 通讯录.vcf --days 30      # 🎂 未来 30 天生日
vcardforge convert   旧.vcf -o new.vcf --version 4.0  # 🔄 版本转换
```

### 典型工作流：手机导出 → 清洗 → 回导

```bash
# 1. 先体检
vcardforge validate 全部联系人.vcf --detail

# 2. 合并多个来源并去重（微信导出 + 手机导出 + 备份）
vcardforge merge weixin.vcf phone.vcf backup.vcf -o clean.vcf -v

# 3. 给 Excel 的人看
vcardforge export clean.vcf -o contacts.csv

# 4. 转 vCard 4.0 回导手机
vcardforge convert clean.vcf -o clean4.vcf --version 4.0
```

### Python API 速查

```python
from vcardforge import (
    parse_text, parse_file,      # 解析
    write_text, write_file,      # 生成（3.0 / 4.0）
    normalize_phone,             # 号码规范化 -> E.164 风格
    dedup_contacts, merge_contacts,  # 去重 / 多源合并
    to_json, to_csv,             # 导出
    validate_contacts,           # 校验报告
)

c = parse_file("x.vcf")[0]
c.display_name        # 最佳显示名（FN > N > 昵称 > ORG）
c.phones[0].raw       # 原始号码
normalize_phone("13800138000")   # -> '+8613800138000'
```

### 校验规则速览

| 规则 | 内容 | 级别 |
|------|------|------|
| R01/R02 | 缺 FN / 缺 N | warning |
| R03 | FN 与 N 均缺失（导入会被拒） | **error** |
| R04/R05 | 缺 VERSION / 值非法 | warning / error |
| R06 | 生日无法解析 | warning |
| R07 | 电话无有效数字 | **error** |
| R08/R09 | 联系人内部 / 跨联系人号码重复 | warning |
| R10 | EMAIL 缺 @ | warning |

## 💡 设计迭代

- **v1.0.0**：解析（2.1/3.0/4.0）· 号码规范化 · 加权去重 · JSON/CSV 导出 · 10 规则校验 · 生日提醒 · 版本转换 · zipapp 单文件打包
- **路线图**：ADR 属性精细建模 · 农历生日支持 · 照片（PHOTO）尺寸统计 · fuzzy 姓名拼音匹配

## 📦 打包部署

```bash
# 一键打包：单文件 CLI (.pyz) + 源码包 + SHA256 校验和
python3 scripts/build.py

# 产物在 dist/：
#   vcardforge-1.0.0.pyz        任何平台直接 python3 运行
#   vcardforge-1.0.0-src.zip    完整源码
#   SHA256SUMS.txt              校验和
```

单元测试：

```bash
python3 -m unittest discover -s tests -v
```

## 🤝 贡献

欢迎 Issue 与 PR！提交遵循 Angular 规范（`feat` / `fix` / `docs` / `refactor` / `test` / `chore`），详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

两条红线：**只用标准库**、**绝不联网**。

## 📄 协议

[MIT](LICENSE) © VCardForge Contributors
