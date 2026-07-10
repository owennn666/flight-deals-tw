# CLAUDE.md — 便宜機票平台（給 Claude Code 的專案脈絡）

## 這是什麼
台灣出發的**便宜票 / BUG 票（標錯價）/ 四腳票**偵測平台。核心是「自動偵測 + 展示/推播」，**不賣票**，訂票導向 OTA（聯盟連結）。定位為資訊分享以降低法律風險。

## 架構（已選定 Path A：Supabase + GitHub Actions + Vercel，目標 $0）
- **偵測引擎**：Python（`flightdeals/`），可插拔四層 `ingest → storage → detectors → notify`，靠 `registry.py` 以名稱選用。
- **抓票排程**：GitHub Actions 每 15 分跑 `python main.py run -c config.prod.yaml`，寫進 Supabase。
- **資料庫 + API**：Supabase（Postgres + PostgREST 自動 API，取代常駐後端）。
- **前端**：`apps/mobile/`（Expo / React Native，一套碼 iOS/Android/**Web**），**直接讀 Supabase**。網頁部署 Vercel。
- 另有一條備援路線（Railway 常駐後端）：`DEPLOY.md` + `Procfile`/`nixpacks.toml`，Path A 用不到。

## 關鍵檔案
- `flightdeals/` — 引擎：`ingest/`（mock/travelpayouts）、`detectors/`（cheap/errorfare/nested）、`storage/`（memory/sqlite/**postgres**）、`notify/`、`pipeline.py`、`registry.py`
- `flightdeals/storage/postgres_store.py` — 寫 Supabase（讀 `DATABASE_URL`，psycopg 延遲載入）
- `config.prod.yaml` — 正式抓票設定（travelpayouts 來源 + postgres 儲存）
- `supabase_schema.sql` — Supabase 建表 + RLS（貼進 SQL Editor 跑一次）
- `.github/workflows/fetch.yml` — 每 15 分抓票（cron `*/15 * * * *`）
- `apps/mobile/src/api/client.ts` — 前端讀 Supabase（PostgREST）
- `apps/mobile/src/config.ts` — 讀 `EXPO_PUBLIC_SUPABASE_URL` / `EXPO_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_DEPLOY.md` — **部署步驟（照這個做）**
- `main.py` — CLI：`demo` / `seed` / `run` / `serve` / `demo-data`

## 現況：已上線（2026-07-10）
- **live 站** https://flight-deals-tw.vercel.app ；repo github.com/owennn666/flight-deals-tw（public）；Supabase 專案「Piao」（ref `kmvyjcmxstghppwqxsbg`）。
- **抓票排程**：GitHub Actions 每 15 分自動跑（cron），寫進 Supabase `deals`。手動觸發：`gh workflow run fetch.yml --repo owennn666/flight-deals-tw`。
- **部署**：前端**非** git 自動部署，需手動 `cd apps/mobile && vercel deploy --prod`；後端隨排程自動生效。
- **七日暖機語意**：基準線可信門檻 = 樣本 ≥50 且橫跨 ≥7 曆日。新部署後每輪印 `本輪偵測到 0 筆好康` 是**預期行為**（暖機中），非壞掉；累積滿 7 天才恢復產出新好康。
- 首次建置細節見 `SUPABASE_DEPLOY.md`。

## 祕密 / 環境變數（絕不 hardcode、不 commit；`.env` 已 gitignore）
- `TRAVELPAYOUTS_TOKEN`（抓票）、`DATABASE_URL`（Supabase 連線字串，含 DB 密碼）→ GitHub Secrets。
- `EXPO_PUBLIC_SUPABASE_URL` / `EXPO_PUBLIC_SUPABASE_ANON_KEY` → Vercel env（前端）。
- 全部由使用者提供，放進各平台的 secret store。**請勿把值寫進檔案或印出來。**

## 環境地雷（本機已踩過，重要）
- **Homebrew Python 壞掉**（pyexpat / libexpat symbol 不合，3.12 與 3.14 都掛）→ 一律用 **uv**：`uv venv --python 3.12` + `uv pip install`。本機既有 venv 在 `~/.flightdeals-venv`。
- 中文資料夾名曾讓 `python -m venv` 出錯 → 用 uv 或 ASCII 路徑。
- 本機 8000 埠被別的程式佔用 → 本機 `serve` 用 8010（Path A 部署不需要 serve）。
- 跑 Expo 需要 **watchman**（否則 EMFILE）：`brew install watchman`。Node 目前 v25（很新），遇怪事可用 nvm 切 20。

## live 資料庫操作邊界（實測規則，務必遵守）
- **讀取**（read-only query）：隨時可做，走 Supabase Management API `POST /v1/projects/{ref}/database/query`（token 在 `.env` 的 `SUPABASE_ACCESS_TOKEN`；HTTP 需帶 `User-Agent: curl/8.7.1`，否則被 Cloudflare 1010 擋）。
- **DDL**（加欄/索引/constraint）：先把確切 SQL 列給使用者、拿到明確同意，再由 agent 執行。
- **改/刪資料列**：自動安全機制會擋、且視重試為繞過——**不要嘗試**，一律請使用者自己貼 Supabase SQL Editor 跑。
- `postgres_store.py` 與前端 `client.ts` 已對真 Supabase 驗證過（不再是「只用假連線測過」）。

## 本機跑 / 測
- 測試：`~/.flightdeals-venv/bin/python -m pytest -q`（目前 54 passed）
- 離線 demo：`python main.py demo`
- 抓真票（需 `DATABASE_URL` + `TRAVELPAYOUTS_TOKEN` 環境變數 + `pip install 'psycopg[binary]'`）：`python main.py run -c config.prod.yaml`

## 慣例
- 儲存 / 資料源 / 偵測器 / 通知皆可插拔（`registry.py` 註冊名字）；新增模組 = 實作介面 + 註冊 + config 啟用。
- 不代訂票；BUG 票 UI 需有風險免責（已內建）。
- 費用目標 $0：Supabase free + GitHub Actions（public repo 免費）+ Vercel free（非商業）。營利後網頁可改 Cloudflare Pages。
