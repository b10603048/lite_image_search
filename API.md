# Lite Image Search — REST API 文件

> 供 AI 代理人（Agent）透過 curl / REST API 操作圖片庫的完整參考文件。

---

## 基本資訊

| 項目 | 說明 |
|---|---|
| **通訊協定** | HTTP（本機） |
| **預設位址** | `http://localhost:6626` |
| **API 前綴** | 所有端點皆在 `/api/` 之下 |
| **自訂埠號** | 啟動時加 `--port` 參數，或設定環境變數 `LIS_PORT` |
| **資料格式** | JSON（上傳 / 匯入為 multipart form） |
| **字元編碼** | UTF-8 |

### 快速測試連線

```bash
curl -s http://localhost:6626/api/stats
```

---

## 錯誤處理

所有端點在失敗時回傳 JSON，包含 `detail` 欄位描述錯誤原因。
Gemini API 相關錯誤的中文訊息如下：

| HTTP 狀態碼 | 錯誤訊息 |
|---|---|
| **429** | `Gemini API 用量已達上限 (429 Rate Limit)，請稍後再試或等待隔天重置` |
| **403** | `Gemini API Key 無效或已停用 (403 Forbidden)` |
| **400** | 顯示 API 回傳的詳細錯誤資訊 |

一般錯誤回應範例：

```json
{"detail": "找不到此圖片"}
```

---

## 端點總覽

| 方法 | 路徑 | 用途 |
|---|---|---|
| POST | `/api/key` | 設定 Gemini API Key |
| GET | `/api/key` | 查詢 API Key 是否已設定 |
| POST | `/api/upload` | 上傳圖片 |
| POST | `/api/search` | 以文字搜尋圖片 |
| GET | `/api/images` | 列出所有圖片 |
| GET | `/api/images/{id}` | 取得單張圖片資訊 |
| DELETE | `/api/images/{id}` | 刪除單張圖片 |
| POST | `/api/favorite/{id}` | 切換收藏狀態 |
| GET | `/api/download/{id}` | 下載原始圖片 |
| GET | `/api/thumb/{id}` | 取得縮圖 |
| POST | `/api/download-batch` | 批次下載（ZIP） |
| POST | `/api/delete-batch` | 批次刪除 |
| GET | `/api/stats` | 取得統計資料 |
| GET | `/api/export` | 匯出整個圖片庫（ZIP） |
| POST | `/api/import` | 匯入圖片庫（ZIP） |

---

## 端點詳細說明

---

### 1. POST `/api/key` — 設定 Gemini API Key

設定用於圖片描述與搜尋的 Gemini API 金鑰。

**請求**

- Content-Type: `application/json`

```json
{
  "api_key": "AIzaSy..."
}
```

**回應**

```json
{
  "ok": true
}
```

**curl 範例**

```bash
curl -X POST http://localhost:6626/api/key \
  -H "Content-Type: application/json" \
  -d '{"api_key": "AIzaSyD...your_key_here..."}'
```

---

### 2. GET `/api/key` — 查詢 API Key 是否已設定

檢查是否已設定 Gemini API Key，回傳遮蔽後的金鑰。

**回應**

```json
{
  "configured": true,
  "masked": "AIzaSy...****"
}
```

- `configured`：`true` 表示已設定，`false` 表示尚未設定
- `masked`：遮蔽後的金鑰字串（未設定時可能為空）

**curl 範例**

```bash
curl -s http://localhost:6626/api/key
```

---

### 3. POST `/api/upload` — 上傳圖片

上傳一或多張圖片，系統會自動產生縮圖並以 Gemini 生成描述（若 API Key 已設定）。

**請求**

- Content-Type: `multipart/form-data`
- 欄位名稱：`files`（可多選）

**回應**

```json
{
  "uploaded": [
    {
      "id": 1,
      "filename": "photo.jpg",
      "file_ext": ".jpg",
      "original_path": "/path/to/photo.jpg",
      "converted_path": "/path/to/photo.webp",
      "thumbnail_path": "/path/to/photo_thumb.png",
      "favorite": false,
      "download_count": 0,
      "created_at": "2026-06-13T12:00:00"
    }
  ],
  "errors": [
    {
      "filename": "bad.txt",
      "error": "不支援的檔案類型"
    }
  ]
}
```

- `uploaded`：成功上傳的圖片清單
- `errors`：上傳失敗的檔案及錯誤原因

**curl 範例**

上傳單張圖片：

```bash
curl -X POST http://localhost:6626/api/upload \
  -F "files=@/path/to/photo.jpg"
```

上傳多張圖片：

```bash
curl -X POST http://localhost:6626/api/upload \
  -F "files=@/path/to/photo1.jpg" \
  -F "files=@/path/to/photo2.png"
```

---

### 4. POST `/api/search` — 以文字搜尋圖片

使用自然語言查詢，透過 Gemini 語意嵌入搜尋最相關的圖片。

**請求**

- Content-Type: `application/json`

```json
{
  "query": "夕陽下的海灘",
  "top_k": 10
}
```

- `query`（必填）：搜尋文字
- `top_k`（選填，預設 10）：回傳的最大結果數量

**回應**

```json
{
  "results": [
    {
      "id": 5,
      "filename": "sunset_beach.jpg",
      "similarity": 0.92,
      "file_ext": ".jpg",
      "original_path": "/path/to/sunset_beach.jpg",
      "converted_path": "/path/to/sunset_beach.webp",
      "thumbnail_path": "/path/to/sunset_beach_thumb.png",
      "favorite": true,
      "download_count": 3,
      "created_at": "2026-06-12T18:30:00"
    }
  ]
}
```

- `similarity`：相似度分數（越高越相近）

**curl 範例**

```bash
curl -X POST http://localhost:6626/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "夕陽下的海灘", "top_k": 5}'
```

---

### 5. GET `/api/images` — 列出所有圖片

取得圖片庫中的所有圖片，支援排序與收藏篩選。

**查詢參數**

| 參數 | 類型 | 預設值 | 說明 |
|---|---|---|---|
| `sort` | string | `newest` | 排序方式：`newest`（最新）、`oldest`（最舊）、`downloads`（下載數） |
| `fav` | string | — | 篩選收藏：`true` 僅顯示收藏、`false` 僅顯示未收藏。不傳則顯示全部 |

**回應**

```json
{
  "images": [
    {
      "id": 1,
      "filename": "photo.jpg",
      "file_ext": ".jpg",
      "original_path": "/path/to/photo.jpg",
      "converted_path": "/path/to/photo.webp",
      "thumbnail_path": "/path/to/photo_thumb.png",
      "favorite": false,
      "download_count": 0,
      "created_at": "2026-06-13T12:00:00"
    }
  ],
  "total": 42
}
```

**curl 範例**

列出所有圖片（最新優先）：

```bash
curl -s http://localhost:6626/api/images
```

依下載數排序：

```bash
curl -s "http://localhost:6626/api/images?sort=downloads"
```

僅顯示收藏圖片：

```bash
curl -s "http://localhost:6626/api/images?fav=true"
```

組合使用：

```bash
curl -s "http://localhost:6626/api/images?sort=oldest&fav=true"
```

---

### 6. GET `/api/images/{id}` — 取得單張圖片資訊

依 ID 取得特定圖片的詳細資訊。

**路徑參數**

| 參數 | 類型 | 說明 |
|---|---|---|
| `id` | integer | 圖片 ID |

**回應**

```json
{
  "id": 1,
  "filename": "photo.jpg",
  "file_ext": ".jpg",
  "original_path": "/path/to/photo.jpg",
  "converted_path": "/path/to/photo.webp",
  "thumbnail_path": "/path/to/photo_thumb.png",
  "favorite": false,
  "download_count": 0,
  "created_at": "2026-06-13T12:00:00"
}
```

**curl 範例**

```bash
curl -s http://localhost:6626/api/images/1
```

---

### 7. DELETE `/api/images/{id}` — 刪除單張圖片

依 ID 刪除一張圖片及其相關檔案（原始檔、轉檔、縮圖）。

**路徑參數**

| 參數 | 類型 | 說明 |
|---|---|---|
| `id` | integer | 圖片 ID |

**回應**

```json
{
  "ok": true
}
```

**curl 範例**

```bash
curl -X DELETE http://localhost:6626/api/images/1
```

---

### 8. POST `/api/favorite/{id}` — 切換收藏狀態

將指定圖片切換為收藏 / 取消收藏。

**路徑參數**

| 參數 | 類型 | 說明 |
|---|---|---|
| `id` | integer | 圖片 ID |

**回應**

```json
{
  "ok": true,
  "favorite": true
}
```

- `favorite`：切換後的狀態（`true` = 已收藏，`false` = 未收藏）

**curl 範例**

```bash
curl -X POST http://localhost:6626/api/favorite/1
```

---

### 9. GET `/api/download/{id}` — 下載原始圖片

下載指定圖片的原始檔案，每次下載會將 `download_count` 加 1。

**路徑參數**

| 參數 | 類型 | 說明 |
|---|---|---|
| `id` | integer | 圖片 ID |

**回應**

- 回傳二進位檔案，含 `Content-Disposition: attachment; filename="..."` 標頭
- Content-Type 依原始檔案類型而定

**curl 範例**

下載並存檔：

```bash
curl -OJ http://localhost:6626/api/download/1
```

下載至指定路徑：

```bash
curl -o ./my_photo.jpg http://localhost:6626/api/download/1
```

---

### 10. GET `/api/thumb/{id}` — 取得縮圖

取得指定圖片的 PNG 縮圖。若無縮圖可用，回傳佔位圖（placeholder）。

**路徑參數**

| 參數 | 類型 | 說明 |
|---|---|---|
| `id` | integer | 圖片 ID |

**回應**

- Content-Type: `image/png`
- 若無縮圖則回傳佔位圖片

**curl 範例**

```bash
curl -o thumb.png http://localhost:6626/api/thumb/1
```

---

### 11. POST `/api/download-batch` — 批次下載（ZIP）

將多張圖片打包為 ZIP 檔案下載。

**請求**

- Content-Type: `application/json`

```json
{
  "ids": [1, 2, 3]
}
```

- `ids`（必填）：要下載的圖片 ID 陣列

**回應**

- 回傳 ZIP 檔案，含 `Content-Disposition: attachment; filename="..."` 標頭
- Content-Type: `application/zip`

**curl 範例**

```bash
curl -X POST http://localhost:6626/api/download-batch \
  -H "Content-Type: application/json" \
  -d '{"ids": [1, 2, 3]}' \
  -o batch_download.zip
```

---

### 12. POST `/api/delete-batch` — 批次刪除

一次刪除多張圖片。

**請求**

- Content-Type: `application/json`

```json
{
  "ids": [1, 2, 3]
}
```

- `ids`（必填）：要刪除的圖片 ID 陣列

**回應**

```json
{
  "ok": true,
  "deleted": 3
}
```

- `deleted`：實際刪除的數量

**curl 範例**

```bash
curl -X POST http://localhost:6626/api/delete-batch \
  -H "Content-Type: application/json" \
  -d '{"ids": [1, 2, 3]}'
```

---

### 13. GET `/api/stats` — 取得統計資料

取得圖片庫的統計摘要。

**回應**

```json
{
  "total_images": 42
}
```

**curl 範例**

```bash
curl -s http://localhost:6626/api/stats
```

---

### 14. GET `/api/export` — 匯出圖片庫

將整個圖片庫匯出為 ZIP 檔案，包含資料庫、原始圖片、縮圖及轉檔。

**回應**

- 回傳 ZIP 檔案
- ZIP 內容包含：資料庫檔案（DB）、原始圖片、縮圖（thumbnails）、轉檔（converted）
- Content-Type: `application/zip`

**curl 範例**

```bash
curl -o gallery_export.zip http://localhost:6626/api/export
```

---

### 15. POST `/api/import` — 匯入圖片庫

從先前匯出的 ZIP 檔案還原圖片庫。

**請求**

- Content-Type: `multipart/form-data`
- 欄位名稱：`file`

**回應**

```json
{
  "ok": true,
  "imported": 38,
  "skipped": 4
}
```

- `imported`：成功匯入的數量
- `skipped`：因重複等原因跳過的數量

**curl 範例**

```bash
curl -X POST http://localhost:6626/api/import \
  -F "file=@gallery_export.zip"
```

---

## 常見工作流程

### 初次設定並上傳搜尋

```bash
# 1. 設定 API Key
curl -X POST http://localhost:6626/api/key \
  -H "Content-Type: application/json" \
  -d '{"api_key": "AIzaSy...your_key"}'

# 2. 上傳圖片
curl -X POST http://localhost:6626/api/upload \
  -F "files=@photo1.jpg" \
  -F "files=@photo2.png"

# 3. 搜尋圖片
curl -X POST http://localhost:6626/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "藍天白雲", "top_k": 5}'

# 4. 下載搜尋結果
curl -OJ http://localhost:6626/api/download/3
```

### 備份與還原

```bash
# 匯出備份
curl -o backup.zip http://localhost:6626/api/export

# 還原備份
curl -X POST http://localhost:6626/api/import \
  -F "file=@backup.zip"
```

### 批次管理

```bash
# 批次下載
curl -X POST http://localhost:6626/api/download-batch \
  -H "Content-Type: application/json" \
  -d '{"ids": [1,2,3,4,5]}' \
  -o batch.zip

# 批次刪除
curl -X POST http://localhost:6626/api/delete-batch \
  -H "Content-Type: application/json" \
  -d '{"ids": [6,7,8]}'
```

---

## 備註

- 所有需要 JSON 請求體的端點皆須加上 `Content-Type: application/json` 標頭
- 上傳與匯入端點使用 `multipart/form-data`，無須手動設定 Content-Type（curl 會自動處理）
- 圖片 ID 為整數，在 URL 路徑中直接傳遞（如 `/api/images/42`）
- 下載端點會自動遞增下載計數器
- 收藏切換為 toggle 機制：呼叫同一端點即可在收藏/取消收藏之間切換
