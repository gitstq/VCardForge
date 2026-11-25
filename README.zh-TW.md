<div align="center">

# 🎴 VCardForge

**零依賴 · 離線優先的 vCard (.vcf) 通訊錄工具箱**

*以純 Python 標準庫自研實現 vCard 解析與生成，提供「函式庫 + 命令列」雙重形態*

[简体中文](README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md)

`Python 3.8+` · `0 依賴` · `0 網路請求` · `MIT`

</div>

---

## 🎉 介紹

**VCardForge** 把散落在手機、通訊軟體、Outlook 匯出檔案裡的 `.vcf` 通訊錄變成可程式化、可清洗、可稽核的資料。它以純 Python 標準庫自研實現 vCard 2.1 / 3.0 / 4.0 的完整解析與生成，專為「資料不出本機」的場景設計。

與其他方案不同：

- ✅ **零第三方依賴** —— 只用標準庫，安裝秒完成，也能直接複製原始碼使用
- ✅ **完全離線** —— 正規化、去重、校驗全部在本機完成，通訊錄資料永不上傳
- ✅ **相容髒資料** —— vCard 2.1 的 QUOTED-PRINTABLE、Outlook 的 `item1.` 分組、iOS 的多 TYPE 參數、行折疊等歷史包袱全都能處理
- ✅ **往返無損** —— 解析 → 輸出保留所有原始屬性，不丟欄位

## ✨ 特性

| 模組 | 能力 |
|------|------|
| 🔍 **解析** | vCard 2.1 / 3.0 / 4.0；行折疊還原；QUOTED-PRINTABLE / BASE64 解碼；`item1.` 分組剝離；受損檔案局部容錯 |
| ☎️ **號碼正規化** | E.164 風格統一；中國手機號 / 市話識別；全形數字糾偏；跨格式（`+86 138...` 與 `138-0013-8000`）歸一 |
| 🧬 **智慧去重** | 手機號 0.60 + 電子郵件 0.30 + 姓名 0.10 加權評分；並查集傳遞合併；組內保留資訊最完整的一筆 |
| 📦 **多檔案合併** | 任意多個 .vcf 一次合併去重，輸出 vCard 3.0 / 4.0 |
| 📊 **匯出** | JSON（含正規化號碼）/ CSV（UTF-8 BOM，Excel 直接開啟不亂碼） |
| 🛡️ **校驗** | 10 條規則（R01–R10）：缺 FN/N、非法 VERSION、壞日期、重複號碼、壞信箱……可作 CI 門檻（錯誤時結束代碼 2） |
| 🎂 **生日提醒** | 未來 N 天生日清單，閏年 2/29 自動回退到 2/28 |
| 🔄 **版本轉換** | 2.1 / 3.0 → 3.0 / 4.0，自動補 UID / FN / N |

## 🚀 快速開始

**方式一：pip 安裝**

```bash
pip install .
```

**方式二：單檔案執行（零安裝）**

```bash
# 下載 Release 中的 vcardforge-*.pyz 後：
python3 vcardforge-1.0.0.pyz --help
```

**方式三：以函式庫整合**

```python
from vcardforge import parse_file, dedup_contacts, write_file

contacts = parse_file("通訊錄.vcf")
clean, report = dedup_contacts(contacts)
print(f"輸入 {len(contacts)} -> 去重後 {len(clean)}")
write_file(clean, "乾淨.vcf", version="4.0")
```

## 📖 使用指南

### CLI 六大子命令

```bash
vcardforge info      通訊錄.vcf                # 📊 概覽：人數 / 版本分布 / 欄位統計
vcardforge validate  通訊錄.vcf --detail       # 🛡️ 10 條規則校驗，錯誤時結束代碼 2
vcardforge merge a.vcf b.vcf -o merged.vcf -v # 🧬 合併 + 智慧去重
vcardforge export    通訊錄.vcf -o out.csv     # 📦 匯出 CSV / JSON
vcardforge birthdays 通訊錄.vcf --days 30      # 🎂 未來 30 天生日
vcardforge convert   舊.vcf -o new.vcf --version 4.0  # 🔄 版本轉換
```

### 典型工作流：手機匯出 → 清洗 → 回匯

```bash
vcardforge validate 全部聯絡人.vcf --detail
vcardforge merge weixin.vcf phone.vcf backup.vcf -o clean.vcf -v
vcardforge export clean.vcf -o contacts.csv
vcardforge convert clean.vcf -o clean4.vcf --version 4.0
```

### Python API 速查

```python
from vcardforge import (
    parse_text, parse_file,      # 解析
    write_text, write_file,      # 生成（3.0 / 4.0）
    normalize_phone,             # 號碼正規化 -> E.164 風格
    dedup_contacts, merge_contacts,  # 去重 / 多源合併
    to_json, to_csv,             # 匯出
    validate_contacts,           # 校驗報告
)

c = parse_file("x.vcf")[0]
c.display_name        # 最佳顯示名（FN > N > 暱稱 > ORG）
normalize_phone("13800138000")   # -> '+8613800138000'
```

### 校驗規則速覽

| 規則 | 內容 | 級別 |
|------|------|------|
| R01/R02 | 缺 FN / 缺 N | warning |
| R03 | FN 與 N 均缺失（匯入會被拒） | **error** |
| R04/R05 | 缺 VERSION / 值非法 | warning / error |
| R06 | 生日無法解析 | warning |
| R07 | 電話無有效數字 | **error** |
| R08/R09 | 聯絡人內部 / 跨聯絡人號碼重複 | warning |
| R10 | EMAIL 缺 @ | warning |

## 💡 設計迭代

- **v1.0.0**：解析（2.1/3.0/4.0）· 號碼正規化 · 加權去重 · JSON/CSV 匯出 · 10 規則校驗 · 生日提醒 · 版本轉換 · zipapp 單檔案打包
- **路線圖**：ADR 屬性精細建模 · 農曆生日支援 · 照片（PHOTO）尺寸統計 · 姓名拼音模糊比對

## 📦 打包部署

```bash
# 一鍵打包：單檔案 CLI (.pyz) + 原始碼包 + SHA256 校驗和
python3 scripts/build.py
```

單元測試：

```bash
python3 -m unittest discover -s tests -v
```

## 🤝 貢獻

歡迎 Issue 與 PR！提交遵循 Angular 規範（`feat` / `fix` / `docs` / `refactor` / `test` / `chore`），詳見 [CONTRIBUTING.md](CONTRIBUTING.md)。

兩條紅線：**只用標準庫**、**絕不連網**。

## 📄 授權條款

[MIT](LICENSE) © VCardForge Contributors
