# 新聞什麼 (NewsWhat Taiwan)

這是一個使用 Flask 和 AI 技術構建的應用程式，用於爬取 Yahoo 新聞台灣版的內容，並使用 AI 生成幽默的新聞摘要、分析和幽默翻譯。目的是縮短新聞閱讀時間，並為閱讀新聞添增樂趣。英文(CNN)版本：[NewsWhat](https://github.com/hazeishere/News-What)

## 功能特點

- **自動爬取新聞**：從 Yahoo 新聞台灣版抓取最新頭條新聞
- **AI 新聞分析**：使用 AI 模型分析新聞內容，提取以下信息：
  - 幽默翻譯版本
  - 簡潔摘要
  - 主題分類
  - 情感分析 (正面/負面/中性)
  - 主要關鍵字提取 (人物、組織、地點)
  - 核心要點 (以 Markdown 格式呈現)
- **美觀的用戶界面**：使用 Bootstrap 構建的現代化網頁界面
- **完全中文支持**：使用繁體中文呈現全部界面和內容

## 技術堆棧

- **後端**: Python + Flask
- **網頁爬蟲**: BeautifulSoup + Requests
- **AI 分析**: AI大模型 [使用 g4f](https://github.com/xtekky/gpt4free)
- **前端**: HTML, CSS, Bootstrap 5, JavaScript

## 安裝指南

### 環境需求
- Python 3.8 或更高版本

### 步驟

1. clone此存儲庫：
   ```
   git clone https://github.com/hazeishere/News-What-Taiwan
   cd news-what-Taiwan
   ```

2. 創建並啟用虛擬環境 (推薦使用)：
   ```
   python -m venv venv

   # Windows系統：
   venv\Scripts\activate

   # macOS/Linux系統:
   source venv/bin/activate
   ```

3. 安裝 dependencies：
   ```
   pip install -r requirements.txt
   ```

4. 執行程式：
   ```
   python app.py
   ```

5. 在瀏覽器中訪問應用程式：
   ```
   http://127.0.0.1:5000
   ```

## 使用說明

1. **爬取新聞**: 
   - 點擊 "爬取最新新聞" 按鈕從 Yahoo 新聞獲取最新的台灣新聞頭條
   - 系統會隨機選擇多篇文章，避免重複爬取

2. **瀏覽新聞列表**:
   - 查看所有已爬取的新聞，包括標題、來源和基本信息
   - 已分析的文章會顯示情感和主題標籤

3. **查看文章分析**:
   - 點擊任一文章查看詳細內容
   - 首次點擊時，系統會使用 AI 生成分析和幽默翻譯
   - 分析完成後，您可以看到幽默翻譯、摘要、核心要點和主要關鍵字

## 文件結構

```
news-what-Taiwan/
├── app.py                # 主程式
├── articles.json         # 存儲爬取的文章
├── requirements.txt      # dependencies列表
├── templates/            # HTML 模板
│   ├── index.html        # 文章列表頁面
│   ├── article.html      # 文章詳細頁面
│   ├── crawling.html     # 爬取頁面
│   ├── debug.html        # debug頁面
│   └── introduction.html # 首頁/介紹頁面
└── README.md             # 本文檔
```

## 問題排解

如果您在使用 AI 分析時遇到問題，可能是因為：

1. **網絡連接問題**：確保您的網路可以連接到 AI 服務
2. **API 限制**：某些 AI 模型可能有使用限制
3. **文章格式**：某些新聞文章可能無法正確提取

請查看除錯頁面 (/debug) 了解系統狀態和可用的 AI 模型。

## 隱私和免責聲明

此程式僅用於教育和娛樂目的。它不存儲個人數據，但它會爬取和處理來自公開可用的新聞來源的內容。生成的內容僅代表 AI 的輸出，不應被視為事實或專業意見。

---

© 2025 新聞什麼 