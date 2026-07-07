# 上線部署指南 — Supabase + GitHub Actions + Vercel（$0 架構）

沒有常駐伺服器,關掉筆電也能隨時查。

```
GitHub repo
  ├─ Python 偵測引擎  → GitHub Actions 每 15 分跑一次 → 寫入 Supabase
  └─ apps/mobile（Expo Web）→ Vercel → 前端直接讀 Supabase
        Supabase = Postgres 資料庫 + 自動 API（取代常駐後端）
```

## 費用
| 項目 | 費用 |
|---|---|
| Supabase | 免費方案（500MB DB，綽綽有餘） |
| Vercel | 免費 |
| GitHub Actions | **公開 repo 無限免費**；私有 repo 免費 2000 分/月（每 15 分會超，見最後一節） |

> 把 repo 設 **Public** → 整套可做到 **$0/月**。

## 事前準備
- 註冊(免費):**GitHub**、**Supabase**、**Vercel**。
- 你的 **Travelpayouts token**(抓票用)。

---

## Step 1 — 建 Supabase 專案 + 建表
1. supabase.com → **New Project**(記住你設的 **DB 密碼**)。
2. 專案 → **SQL Editor** → 貼上 `supabase_schema.sql` 全部 → **Run**(建好 5 張表 + RLS)。
3. 到 **Project Settings** 拿三樣東西:
   - **Project URL**(API → Project URL,例 `https://xxxx.supabase.co`)
   - **anon public key**(API → Project API keys → `anon` `public`)
   - **DATABASE_URL**(Database → Connection string → **URI**;把 `[YOUR-PASSWORD]` 換成你的 DB 密碼。用 "Session pooler" 那條即可)

---

## Step 2 — 推 GitHub + 設定抓票排程
1. 推專案上 GitHub:
   ```bash
   cd ~/Desktop/抓票平台
   git init && git add . && git commit -m "init"
   git remote add origin https://github.com/你的帳號/piao.git
   git branch -M main && git push -u origin main
   ```
   `.env` 已 gitignore,不會外洩。**建議設 Public**(Actions 無限免費);要 Private 也行,但注意分鐘數(見最後)。
2. repo → **Settings → Secrets and variables → Actions → New repository secret**,加:
   - `DATABASE_URL` = 你的 Supabase 連線字串
   - `TRAVELPAYOUTS_TOKEN` = 你的 token
   - (選)`TRAVELPAYOUTS_MARKER` = 聯盟 marker
3. repo → **Actions** 分頁 → 若提示啟用就啟用 → 選「**抓票（每 15 分）**」→ 按 **Run workflow** 先手動跑一次。
4. 看 log:應出現 `[run] 本輪偵測到 N 筆好康`。**手動再跑一次**(第一次是建基準線,第二次才會判好康)。
5. 到 Supabase → **Table Editor → deals**,確認有資料列進來。

---

## Step 3 — Vercel 部署網頁
1. vercel.com → **Add New → Project** → Import 你的 repo。
2. **Root Directory 設 `apps/mobile`**(重要)。
3. 環境變數:
   - `EXPO_PUBLIC_SUPABASE_URL` = 你的 Project URL
   - `EXPO_PUBLIC_SUPABASE_ANON_KEY` = anon public key
4. **Deploy** → 得到 `https://yyy.vercel.app` → 開它就是你的 App,直接讀 Supabase、手機也能開、隨時查。

---

## 完成 & 維護
- 資料**每 15 分自動更新**(GitHub Actions)。
- 改航線/門檻:改 `config.prod.yaml` → `git push` → 下次抓票生效。
- 換 token:改 GitHub Secret 即可。
- 看抓票紀錄:repo → Actions → 點進某次執行看 log。

---

## 注意事項
1. **GitHub 排程免費分鐘**:公開 repo 無限;私有 repo 每月 2000 分,每 15 分跑約 3000 分/月會超。要私有又免費 → 把 `.github/workflows/fetch.yml` 的 cron 改成 `*/30 * * * *`(每 30 分,約 1500 分/月)。
2. **排程延遲**:GitHub 排程尖峰時可能晚幾分鐘,屬正常。
3. **60 天沒 commit** 會自動停用排程,去 Actions 點一下即可恢復。
4. **首次要跑兩次**才會有好康(第一次建基準線)。之後每輪都會判。
5. **安全**:anon key 放前端是 Supabase 正常設計;RLS 已限制匿名只能讀 deals、寫 devices/subscriptions,碰不到 prices。

## 本機開發(選)
- App 連 Supabase:在 `apps/mobile/` 建 `.env`:
  ```
  EXPO_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
  EXPO_PUBLIC_SUPABASE_ANON_KEY=你的anonkey
  ```
  然後 `npx expo start`。
- 手動抓一次:`DATABASE_URL=... TRAVELPAYOUTS_TOKEN=... python main.py run -c config.prod.yaml`(需先 `pip install 'psycopg[binary]'`)。

> 註:`Procfile`、`nixpacks.toml`、`runtime.txt`、`DEPLOY.md` 是「另一條 Railway 路線」的檔案,這條 Supabase 路線用不到,留著不影響。
