# 便宜機票偵測平台 — 全端骨架

台灣出發、整合「異常便宜票 / BUG 票 / 四腳票」三種票源的自動化偵測平台。
**Python 偵測引擎 + FastAPI（後端）＋ React Native / Expo（App 客戶端）**，模組化、可跑、可逐步擴充。

> 搭配文件：`../機票平台_產品與技術架構.md`（完整產品、市場、法律、路線圖分析，含 RN 版架構）

---

## 專案結構（monorepo）

```
flight-deals-mvp/
  flightdeals/          # ★ Python 後端：偵測引擎 + FastAPI
    ingest/             #   資料源（mock / travelpayouts / amadeus）
    storage/            #   儲存 + 基準線 + deals 持久化（memory / sqlite）
    detectors/          #   三種票偵測（cheap / errorfare / nested）
    notify/             #   通知（console / line / repository）
    api/                #   FastAPI：/deals /routes /subscriptions /devices
    pipeline.py         #   編排引擎（串起四層）
  tests/                #   19 個測試（核心 + API）
  main.py               #   CLI：demo / seed / run / serve
  apps/mobile/          # ★ React Native (Expo) App 客戶端
```

四層可插拔：`ingest → storage → detectors → notify`，各層有 `base.py` 介面，靠 `registry.py` 用名稱抽換。`pipeline.py` 是唯一管流程的地方，模組間互不相依。

---

## 快速開始

### A. 離線 demo（30 秒、零依賴、免 API key）
```bash
python3 main.py demo
```
對 7 條台灣出發航線注入合成歷史 → 偵測 → 印出 💰 便宜票 與 🐞 BUG 票。

### B. 全端跑起來（後端 API + App）
```bash
# 1) 後端
pip install -r requirements.txt          # 或：pip install fastapi "uvicorn[standard]" httpx
python3 main.py seed                      # 注入歷史讓基準線可用（寫入 flightdeals.db）
python3 main.py run                       # 跑一輪偵測，好康存進 DB
python3 main.py serve                     # 啟動 API：http://127.0.0.1:8000 （/docs 有互動文件）

# 2) App / Web（另開一個終端；同一套 RN 碼）
cd apps/mobile
npm install
npx expo start            # 手機 App（Expo Go / 模擬器）
npx expo start --web      # ★ 同一套碼直接跑成網頁（react-native-web）
# 記得把 app.json 的 expo.extra.apiBaseUrl 指到後端
```

> **RN = App + Web**：同一份 `App.tsx` 與畫面，`--web` 就編譯成網頁，不用另寫一份前端。

### C. 跑測試
```bash
pip install pytest fastapi httpx
python3 -m pytest -q                       # 19 passed
```

---

## API 端點（FastAPI）

| 方法 | 路徑 | 用途 |
|---|---|---|
| `GET` | `/api/health` | 健康檢查 |
| `GET` | `/api/routes` | 可追蹤航線清單 |
| `GET` | `/api/deals?limit=&type=` | 近期好康（可依 `cheap`/`error_fare`/`nested` 篩選）|
| `GET` | `/api/deals/{id}` | 單筆好康詳情 |
| `POST` | `/api/devices` | 註冊 Expo push token |
| `GET`/`POST` | `/api/subscriptions` | 查詢/設定訂閱條件 |

---

## 三種票怎麼偵測

| 票種 | 模組 | 邏輯 | 誤報控制 |
|---|---|---|---|
| 異常便宜票 | `detectors/cheap.py` | 低於基準線 `threshold`（預設 25%）| 基準線需 ≥8 樣本才判 |
| BUG 票 | `detectors/errorfare.py` | 極端低價（預設 70%）或高艙等低價 | **一律標記需人工複核** |
| 四腳票/隱藏城市 | `detectors/nested.py` | 比較「構票總價 vs 直購價」 | 骨架，Phase 3 接 multi-city |

---

## 如何擴充（模組化重點）

新增一個資料源，三步：
1. `flightdeals/ingest/myapi.py` 實作 `DataSource.search()` 回傳 `list[FarePrice]`。
2. `registry.py` 的 `SOURCES` 加 `"myapi": MyApiSource`。
3. `config.yaml` 的 `sources` 啟用 `- name: myapi`。

偵測器 / 通知 / 儲存後端同理（各自 `base.py` + registry + config）。每個模組都能交給 AI 獨立生成與測試。

---

## 上線設定（接真實服務）
1. `.env`（複製 `.env.example`）：`TRAVELPAYOUTS_TOKEN`、`LINE_CHANNEL_ACCESS_TOKEN`。
2. `config.yaml`（複製 `config.example.yaml`）：`sources` 改 `travelpayouts`、`notifiers` 加 `line` 與 `expo_push`（App 原生推播，會讀同一個 DB 的訂閱決定推給誰）。
3. `pip install pyyaml && python3 main.py seed -c config.yaml && python3 main.py run -c config.yaml`
4. 用 cron 定時跑 `run`；`serve` 常駐提供 API；App 用 Expo EAS 打包上架。

---

## 重要提醒
- **這是骨架**：偵測門檻、季節性調整、反爬蟲、推播過濾等仍需依真實資料調校。
- **SQLite 提示**：`flightdeals.db` 需放在一般本機資料夾（雲端同步/網路掛載資料夾可能不支援檔案鎖）。
- **法律**：平台定位為「資訊分享/比價」，訂票導向 OTA/航司（聯盟連結），自己不開票；BUG 票務必附風險免責（程式已內建），四腳票/隱藏城市屬「違約但不違法」灰色地帶，上線前請諮詢台灣執業律師。詳見架構文件第 8、11 章。
