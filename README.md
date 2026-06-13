# 🔍 Lite Image Search

輕量級本機圖片搜尋工具，使用 Google Gemini Embedding API 實現以圖找圖、以文找圖的語意搜尋。

## ✨ 功能特色

- **語意搜尋** — 輸入文字描述即可搜尋相關圖片（基於 Gemini Embedding + 餘弦相似度）
- **以圖找圖** — 上傳圖片自動建立 embedding，支援相似圖片比對
- **多格式支援** — JPG/PNG/GIF/WebP/BMP/TIFF/SVG/AI/EPS/PSD/PDF/HEIC/HEIF
- **自動轉檔** — AI/EPS/PDF（PyMuPDF）、PSD（psd-tools）、SVG（CairoSVG）、HEIC（pillow-heif）自動轉為 PNG 預覽
- **網頁介面** — 单頁式 UI，亮色/暗色主題、拖曳上傳、拖曳選取、收藏功能
- **輕量無依賴** — 純 Python + SQLite，不需要 GPU 或 PyTorch
- **跨平台** — Windows / Linux / macOS

## 📸 截圖

<!-- 可在此加入截圖 -->
<!-- ![Lite Image Search 截圖](screenshots/demo.png) -->

## 🚀 快速開始

### Windows

1. 確認已安裝 [Python 3.10+](https://www.python.org/downloads/)
2. 雙擊 `start.bat`（首次會自動安裝套件）
3. 瀏覽器自動開啟 `http://localhost:6626`

或使用指令：

```batch
start.bat
start.bat 8080
```

### Linux / macOS

```bash
# 賦予執行權限（首次）
chmod +x start.sh

# 啟動（首次會自動建立 venv 並安裝套件）
./start.sh

# 指定通訊埠
./start.sh 8080
```

### 手動啟動

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows
pip install -r requirements.txt
python start.py
```

### 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `LIS_PORT` | 伺服器通訊埠 | `6626` |
| `GEMINI_API_KEY` | Gemini API 金鑰（也可在網頁介面設定） | — |

## 🔑 Gemini API 金鑰

本工具需要 Google Gemini API 金鑰才能使用語意搜尋功能。

1. 前往 [Google AI Studio](https://aistudio.google.com/apikey) 取得免費 API 金鑰
2. 在網頁介面的設定欄位輸入金鑰，或設定環境變數 `GEMINI_API_KEY`

> 免費方案有用量限制，請參考 [Gemini API 定價](https://ai.google.dev/pricing)

## 📡 CLI 使用 / API 端點

詳細 API 文件請參考 [API.md](API.md)。以下為常用 curl 範例：

### 上傳圖片

```bash
curl -X POST http://localhost:6626/api/upload \
  -F "files=@photo.jpg" \
  -F "files=@design.ai"
```

### 文字搜尋

```bash
curl -X POST http://localhost:6626/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "夕陽海灘", "top_k": 10}'
```

### 列出所有圖片

```bash
curl http://localhost:6626/api/images?sort=newest
```

### 下載圖片

```bash
curl -O -J http://localhost:6626/api/download/1
```

### 匯出 / 匯入

```bash
# 匯出
curl -o backup.zip http://localhost:6626/api/export

# 匯入
curl -X POST http://localhost:6626/api/import \
  -F "file=@backup.zip"
```

## ⚙️ 設定

所有設定集中在 `config.py`：

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `HOST` | 綁定位址 | `0.0.0.0` |
| `PORT` | 通訊埠 | `6626` |
| `GEMINI_MODEL` | Embedding 模型 | `gemini-embedding-2` |
| `EMBEDDING_DIMENSION` | Embedding 維度（Matryoshka 截斷） | `768` |
| `THUMBNAIL_MAX_SIZE` | 縮圖最大尺寸（像素） | `800` |

## 🖼️ 支援的圖片格式

| 格式 | 副檔名 | 說明 |
|------|--------|------|
| 點陣圖 | `.jpg` `.jpeg` `.png` `.gif` `.bmp` `.webp` `.tiff` `.tif` | Pillow 直接開啟 |
| Adobe Illustrator | `.ai` | PyMuPDF 轉檔（AI 為 PDF 格式） |
| Photoshop | `.psd` | psd-tools 轉檔 |
| PDF | `.pdf` | PyMuPDF 轉檔 |
| SVG | `.svg` | CairoSVG 轉檔 |
| HEIC/HEIF | `.heic` `.heif` | pillow-heif 轉檔 |
| EPS | `.eps` | PyMuPDF / Ghostscript 轉檔 |

> 原始檔案**一律保留**，轉檔僅用於預覽與 embedding 生成。

## 🏗️ 專案架構

```
lite_image_search/
├── main.py              # FastAPI 後端（API 端點）
├── config.py            # 設定（通訊埠、路徑、API 金鑰）
├── database.py          # SQLite 資料庫（metadata + embedding 向量）
├── gemini_client.py     # Gemini Embedding API 客戶端
├── converter.py         # 圖片格式轉換
├── search.py            # 餘弦相似度搜尋（純 Python）
├── start.py             # 跨平台啟動器（argparse）
├── start.sh             # Linux / macOS 啟動腳本
├── start.bat            # Windows 啟動腳本（含便攜 Python 自動安裝）
├── install.bat          # Windows 套件重裝工具
├── requirements.txt     # Python 套件依賴
├── static/
│   └── index.html       # 單頁式網頁 UI
├── data/                # 執行時資料（自動建立）
│   ├── lite_image_search.db
│   ├── original/        # 原始上傳檔案
│   ├── converted/       # 轉檔後 PNG
│   ├── thumbnails/      # 縮圖
│   └── api_key.txt      # API 金鑰
└── runtime/             # Windows 便攜 Python（自動建立）
```

## 📦 依賴套件

- **FastAPI** + **Uvicorn** — Web 伺服器
- **Pillow** — 圖片處理
- **PyMuPDF** — AI/EPS/PDF 轉檔
- **psd-tools** — PSD 轉檔
- **CairoSVG** — SVG 轉檔
- **pillow-heif** — HEIC/HEIF 轉檔
- **pdf2image** — PDF 備用轉檔（需 poppler）
- **requests** — API 呼叫

## 📄 授權

本專案採用 [MIT License](https://opensource.org/licenses/MIT) 授權。
