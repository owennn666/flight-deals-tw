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

## 現在要做：部署（照 SUPABASE_DEPLOY.md）
1. Supabase 專案 + 跑 `supabase_schema.sql`（使用者建帳號/專案）。
2. 推 GitHub（建議 **public**，讓 Actions 無限免費）。
3. 設 GitHub Secrets：`DATABASE_URL`、`TRAVELPAYOUTS_TOKEN`、（選）`TRAVELPAYOUTS_MARKER`。可用 `gh secret set`。
4. Actions 手動觸發抓票 **兩次**（第一次建基準線），確認 Supabase `deals` 表有資料。
5. Vercel 部署 `apps/mobile`（Root Directory = `apps/mobile`），env：`EXPO_PUBLIC_SUPABASE_URL` / `EXPO_PUBLIC_SUPABASE_ANON_KEY`。

## 祕密 / 環境變數（絕不 hardcode、不 commit；`.env` 已 gitignore）
- `TRAVELPAYOUTS_TOKEN`（抓票）、`DATABASE_URL`（Supabase 連線字串，含 DB 密碼）→ GitHub Secrets。
- `EXPO_PUBLIC_SUPABASE_URL` / `EXPO_PUBLIC_SUPABASE_ANON_KEY` → Vercel env（前端）。
- 全部由使用者提供，放進各平台的 secret store。**請勿把值寫進檔案或印出來。**

## 環境地雷（本機已踩過，重要）
- **Homebrew Python 壞掉**（pyexpat / libexpat symbol 不合，3.12 與 3.14 都掛）→ 一律用 **uv**：`uv venv --python 3.12` + `uv pip install`。本機既有 venv 在 `~/.flightdeals-venv`。
- 中文資料夾名曾讓 `python -m venv` 出錯 → 用 uv 或 ASCII 路徑。
- 本機 8000 埠被別的程式佔用 → 本機 `serve` 用 8010（Path A 部署不需要 serve）。
- 跑 Expo 需要 **watchman**（否則 EMFILE）：`brew install watchman`。Node 目前 v25（很新），遇怪事可用 nvm 切 20。

## 尚未對真環境驗證（部署時要盯）
- `postgres_store.py` 的 SQL **只用假連線測過 Python 邏輯，沒對真 Supabase 跑過** → 第一次抓票盯 Actions log，可能要修小地方（欄位名/型別/`::date`/`::jsonb` cast）。
- 前端 `client.ts`（Supabase PostgREST）也沒對真 Supabase 測過。
- 首次抓票要跑 **兩輪** 才會有 deals（第一輪只建基準線）。

## 本機跑 / 測
- 測試：`~/.flightdeals-venv/bin/python -m pytest -q`（目前 25 passed）
- 離線 demo：`python main.py demo`
- 抓真票（需 `DATABASE_URL` + `TRAVELPAYOUTS_TOKEN` 環境變數 + `pip install 'psycopg[binary]'`）：`python main.py run -c config.prod.yaml`

## 慣例
- 儲存 / 資料源 / 偵測器 / 通知皆可插拔（`registry.py` 註冊名字）；新增模組 = 實作介面 + 註冊 + config 啟用。
- 不代訂票；BUG 票 UI 需有風險免責（已內建）。
- 費用目標 $0：Supabase free + GitHub Actions（public repo 免費）+ Vercel free（非商業）。營利後網頁可改 Cloudflare Pages。
