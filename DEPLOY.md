# 上線部署指南（網頁版 + 後端 24hr，每 15 分自動更新）

把平台放上雲端,關掉筆電也能隨時查。架構:

```
你的 GitHub repo
   ├─ 後端（FastAPI + 每15分自動抓票 + SQLite on volume） → Railway
   └─ apps/mobile（Expo Web 靜態網頁）                     → Vercel
App/網頁 → 打 Railway 後端網址
```

---

## 費用（2026 現況，老實說）

| 項目 | 費用 |
|---|---|
| Vercel（網頁） | **免費** |
| Railway（後端） | 新帳號有 **$5 試用額度**（免費起步）；之後約 **$5/月**（Hobby，用量小） |

> **為什麼不用「完全免費」的 Render free？** 它沒流量時會休眠(scale to zero),一休眠就**停止抓票** → 不符合「24hr 每 15 分更新」。想完全 $0 有進階做法(見附錄),但較繁瑣,建議先用 Railway。

---

## 事前準備
- 註冊(都免費):**GitHub**、**Railway**、**Vercel** 帳號。
- 你的 Travelpayouts token(已在本機 `.env`;雲端會**另外設環境變數**,`.env` 不會上傳)。

---

## Step 0 — 把專案推上 GitHub

```bash
cd ~/Desktop/抓票平台
git init
git add .
git commit -m "init"
```
先確認 `.env` 沒被加進去(已列入 `.gitignore`):執行 `git status`,**不該**看到 `.env`。

在 GitHub 建一個 **Private** repo,照它顯示的指令 push:
```bash
git remote add origin https://github.com/你的帳號/piao.git
git branch -M main
git push -u origin main
```

---

## Step 1 — Railway 部署後端

1. 到 railway.app → **New Project** → **Deploy from GitHub repo** → 選你的 repo。
   （會用 `nixpacks.toml` 認出 Python、照 `Procfile` 啟動,埠自動帶入 `$PORT`。）
2. **加持久化磁碟**(存 DB,重部署不會丟資料):service → **Settings → Volumes → New Volume**,Mount path 填 **`/data`**。
3. **設環境變數**(service → **Variables**):
   - `TRAVELPAYOUTS_TOKEN` = 你的 token
   - `FLIGHTDEALS_DB` = `/data/flightdeals.db`
   - （選）`TRAVELPAYOUTS_MARKER` = 你的聯盟 marker（變現用）
   - `PORT` 不用設,Railway 自動提供。
4. **產生公開網址**:Settings → **Networking → Generate Domain** → 得到 `https://xxx.up.railway.app`。
5. **驗證**:開 `https://xxx.up.railway.app/api/health` → 看到 `{"status":"ok"}` 就成功。
   - 剛部署時 `/api/deals` 可能是空的。排程每 15 分抓一次,**約 15–30 分後**開始有真票(前一輪先建基準線,下一輪才判好康)。

---

## Step 2 — Vercel 部署網頁

1. 到 vercel.com → **Add New → Project** → **Import** 你的 GitHub repo。
2. **Root Directory 設成 `apps/mobile`**（重要）。Vercel 會讀 `apps/mobile/vercel.json`,用 `expo export` 建置成靜態網頁。
3. **設環境變數**:`EXPO_PUBLIC_API_BASE_URL` = 你 Railway 的網址（`https://xxx.up.railway.app`,**結尾不要斜線**）。
4. **Deploy** → 得到 `https://yyy.vercel.app`。
5. 開它 → 就是你的 App 網頁版,連到雲端後端。**手機瀏覽器**也能開、隨時查、可加到主畫面。

---

## Step 3 — 完成 & 日常維護

- **資料每 15 分自動更新**(Railway 背景排程,`--poll 900`)。
- **改航線 / 門檻**:編輯 `config.prod.yaml` → `git push` → Railway 自動重新部署。
- **換 token**:改 Railway 的環境變數即可(別寫進程式碼)。
- **看後端日誌**:Railway service → Deployments/Logs,可看到 `[poll] 更新完成，本輪 N 筆新好康`。

---

## 安全
- `.env` 永不上傳(已 gitignore);token 只放在 Railway 環境變數。
- GitHub repo 建議設 **Private**。
- (進階)上線穩定後,可把後端 CORS 從 `*` 收緊成只允許你的 Vercel 網域(在 `flightdeals/api/app.py` 的 `allow_origins` 改成 `["https://yyy.vercel.app"]`)。

---

## 附錄 — 想完全 $0 的進階做法
後端仍需一個持久化的地方。可用 **Render free**(會休眠)放 API + DB,另用 **GitHub Actions 排程**(免費額度 2000 分/月)每 15 分觸發抓票(呼叫後端或直接跑 `run`)。設定較繁瑣;要走這條再跟我說,我幫你寫 GitHub Actions workflow。

---

## 之後要做手機 App 上架?
網頁版之外,同一套碼可用 **Expo EAS** 打包上 iOS / Android(需 Apple $99/年、Google $25 開發者帳號 + 商店審核)。要做時再找我,我給你 EAS 設定與步驟。
