# HEXO Editor Desktop

專為部落客打造的跨平台 HEXO 文章編輯器，提供完整的文章管理、編輯預覽、分類標籤管理等功能。

A cross-platform desktop editor for HEXO blog, featuring article management, live preview, categories/tags management and more.

## ✨ 特色功能

- 📝 **Markdown 編輯器**
  - 即時預覽功能
  - 支援標準 Markdown 語法
  - 快速鍵支援 (Ctrl+S 儲存)

- 🗂 **文章管理**
  - YAML Front Matter 編輯器
  - 階層式分類管理
  - 標籤管理系統
  - 文章搜尋與篩選

- 🎨 **使用者介面**
  - 直覺的操作介面
  - 跨平台支援 (Windows/MacOS/Linux)
  - 分割視窗即時預覽

- 💾 **資料安全**
  - 文章備份與匯出
  - ZIP 格式打包

## 🚀 安裝說明

### 系統需求
- Python 3.8 或以上版本
- PySide6
- Git (選用)

### 安裝步驟

1. 複製專案到本機：
```bash
git clone https://github.com/yourusername/hexo-editor-desktop.git
cd hexo-editor-desktop
```

2. 安裝相依套件：
```bash
pip install -r requirements.txt
```

3. 執行程式：
```bash
python main.py
```

## 📖 使用教學

### 基本操作流程

1. 選擇 HEXO 部落格目錄
2. 瀏覽或搜尋已有文章
3. 編輯文章內容與設定
4. 儲存並預覽結果

### 文章編輯

- 支援標準 Markdown 語法
- 可即時預覽渲染結果
- 一鍵編輯 Front Matter
- YAML 格式自動整理

### 分類標籤管理

- 階層式分類管理
- 標籤使用統計
- 批量修改功能
- 重複項目檢查

## 🔧 開發文件

### 專案結構
```
hexo-editor-desktop/
├── main.py      # 主程式
└── requirements.txt   # 相依套件
```

### 主要類別說明

- `HexoEditor`: 主視窗類別
- `MarkdownEditor`: Markdown 編輯器元件
- `FileLoader`: 檔案載入器
- `StyleManager`: 樣式管理器
- `CategoryManager`: 分類管理
- `TagManager`: 標籤管理

## 🤝 參與貢獻

我們歡迎任何形式的貢獻，包括但不限於：

- 回報問題
- 功能建議
- 程式碼提交
- 文件翻譯

### 貢獻步驟

1. Fork 此專案
2. 建立您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的修改 (`git commit -m '新增一個好用的功能'`)
4. 推送到您的分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 📝 授權條款

此專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案

## 🌟 鳴謝

感謝以下開源專案：

- [PySide6](https://doc.qt.io/qtforpython/index.html)
- [markdown2](https://github.com/trentm/python-markdown2)
- [PyYAML](https://pyyaml.org/)

## 📞 聯絡資訊

如有任何問題或建議，歡迎透過以下方式聯繫：

- 在 GitHub 上[開啟 Issue](https://github.com/kyosora/hexo-editor-desktop/issues)
- 寄信到 [coasta98381@gmail.com](mailto:coasta98381@gmail.com)

## ⚠️ 免責聲明

本專案為開源軟體，依據 MIT 授權條款提供。作者及貢獻者不對任何使用本軟體造成的損失負責。使用前請詳閱授權條款。
