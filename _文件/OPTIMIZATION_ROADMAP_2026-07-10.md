# 便宜機票平台 優化路線圖（六路審查合併版）

產出日期：2026-07-10
來源：六個角度的獨立審查（引擎正確性、資料品質、前端 UX、資安、營運可靠性、產品轉化），P0/P1 皆經對抗驗證。標記規則：verdict=REFUTED 的發現不採用（列於第 5 節帶過）；CONFIRMED 採用；UNVERIFIED 保留但明確標註。跨路重複的發現已合併為單條並註明「多路同報」。

---

## 1. 總覽（專案健康度三句話）

1. 程式碼本體是健康的（可插拔架構清楚、SQL 全參數化、無金鑰外洩、測試 25 passed），但「產品對使用者的承諾」與「實際管線」之間有三處結構性斷裂：推播訂閱全鏈路斷開（存了永遠不會推）、Web 版訂閱存了就丟（裝置 id 不持久化）、偵測基準線把不同出發月份與不同 OTA 混在同一池比較（核心判斷「這比平常便宜」不可信）。
2. 商業與產品主打點目前掛零：全站外導點擊零分潤（Trip.com 連結程式層級沒有聯盟參數、TRAVELPAYOUTS_MARKER 未設）、BUG 票分頁上線以來零筆資料。
3. 營運面是「無人看守的 $0 架構」：抓票失敗無任何告警管道、prices 表只增不減，在數月尺度內會自然走向靜默停擺——必須在那之前補上告警、保活與資料清理。

---

## 2. 立刻做（P0 與已確認的高影響低工作量）

| # | 事項 | severity/effort | 落點 | 修法 |
|---|------|----------------|------|------|
| 2.1 | 移除推播假承諾文案、隱藏無效推播開關（P0 斷鏈的立即止血） | P0 止血 / S | apps/mobile/src/screens/SubscriptionsScreen.tsx:49、SettingsScreen.tsx:5 | 「之後符合條件的好康會推播給你」改成「功能籌備中」；設定頁純裝飾的推播 Switch 先隱藏（開關無效這條為 UNVERIFIED，但隱藏是零風險動作）。根治見 4.2。多路同報：前端 + 產品（皆 CONFIRMED P0） |
| 2.2 | Web 裝置 id 持久化 | P0 / S | apps/mobile/src/notifications/push.ts:17-24 | 產生 UUID 存 localStorage（封裝跨平台），裝置識別與 push token 脫鉤；token 註冊失敗不影響識別。現況：Web 每次重新整理拿新隨機 id，訂閱「存了就丟」。CONFIRMED P0 |
| 2.3 | 基準線可信度止血 | P0 根因的低成本止血 / S | flightdeals/models.py:58-61 | is_reliable 除 sample_size>=20 外，加「observed_at 至少橫跨 7 個不同曆日」；並考慮把門檻拉高到 50-100（順帶修 stats.py:30 在 n=20 時 p05 幾乎等於最小觀測值的不穩定問題）。根治見 4.1。CONFIRMED P0（data 路） |
| 2.4 | prices 表加 retention | P1 / S | flightdeals/storage/postgres_store.py:31-42、supabase_schema.sql:5-17 | Supabase pg_cron 排程 `delete from prices where observed_at < now() - interval '95 days'`；可加去重 unique index + ON CONFLICT DO NOTHING 減緩成長。現況：純 INSERT 無清除，估數月內逼近免費 500MB 上限。多路同報：資料 + 營運（皆 CONFIRMED，對抗驗證後定 P1） |
| 2.5 | 抓票失敗告警 + 60 天保活 | P1 / S | .github/workflows/fetch.yml:3 | 加 `if: failure()` 步驟 curl 打 webhook（Discord/ntfy.sh）；讓 workflow 定期產生真 commit 避開 GitHub「60 天無 commit 停排程」（連鎖到 Supabase 7 天低活動暫停）。CONFIRMED（對抗驗證後 P1：GitHub 預設會 email 排程失敗，且前端讀取也算 Supabase 活動） |
| 2.6 | dedupe_key 補齊維度 | P1 / S | flightdeals/models.py:82-86 | key 併入 gate（或 flight_number）與 return_date；價格改粗桶如 round(price, -2)。現況：不同 gate/班機同價會被 DB unique 靜默吃掉且永久壓制（seen_deal 無時間窗，比原描述更糟）。改完跑 tests/test_pipeline.py。CONFIRMED P1 |
| 2.7 | SQLiteStore.baseline 補 p10/p05 | P1 / S | flightdeals/storage/sqlite_store.py:66-76 | 仿 memory.py:38-39 / postgres_store.py:60-61 補 percentile 計算。現況：預設 store（config.py:19）下 p10=p05=0.0，cheap 偵測器被靜默永久關閉，本機驗證必踩坑。CONFIRMED P1 |
| 2.8 | 卡片與詳情頁顯示資料新鮮度 | P1 / S | apps/mobile/src/components/DealCard.tsx、screens/DealDetailScreen.tsx | created_at 已隨 select=* 回到前端（types.ts:7）但零使用；加「X 分鐘前發現」相對時間，純前端。對時效性產品是信任缺口，也是唯一能肉眼確認排程活著的訊號。多路同報：前端 + 產品（皆 CONFIRMED P1） |

---

## 3. 短期（一週內值得做）

| # | 事項 | severity/effort | 落點 | 修法 |
|---|------|----------------|------|------|
| 3.1 | RLS 止血：拿掉全表匿名讀取 | P1 / S | supabase_schema.sql:85-90 | 先移除 `anon read subs`（現況任何人可 SELECT 全部訂閱，native 版洩出的 device 值就是可直接發推播的 Expo token）；subscriptions.device 改存與 push token 脫鉤的隨機 id。根治（Anonymous Auth + ownership policy）見 4.6。CONFIRMED（對抗驗證後 P1：資料低敏感、web 版拿不到真 token） |
| 3.2 | anon 寫入加硬上限 | P1 / S | supabase_schema.sql:55-66 | devices.token 加 char_length CHECK、subscriptions.routes 加 octet_length CHECK，降低灌爆免費額度的破壞力。CONFIRMED P1 |
| 3.3 | DealDetailScreen 補齊資訊 + tier 中文化 | P1+P2 / S | apps/mobile/src/screens/DealDetailScreen.tsx:17-21 | 把 DealCard 的 dateLine/flightInfoLine 抽成共用 util，詳情頁補 return_date/航班/gate（卡片改版時漏同步，git log 佐證）；第 18-20 行別直接印英文 tier 原值，比照 DealCard 只在 strong 顯示「難得低價」。CONFIRMED P1 |
| 3.4 | BUG 票分頁空狀態改設計 | P1 / S | apps/mobile/src/screens/DealsScreen.tsx:194 | 不調低 threshold=0.70（刻意的信任權衡），改成誠實留人的空狀態：顯示最近一筆歷史 error_fare（標「已失效，僅供參考」）或併回主列表加徽章。實測 prod 全史 0 筆 error_fare。CONFIRMED P1 |
| 3.5 | gate 過濾下推 + 分頁 | P1（UNVERIFIED，未經對抗驗證）/ M | apps/mobile/src/api/client.ts:83、screens/DealsScreen.tsx:76-77 | `&gate=not.is.null` 下推到 PostgREST，避免前端二次過濾吃掉 limit=50 名額；加 onEndReached 分頁；空清單區分「沒資料」與「篩選太窄」 |
| 3.6 | pipeline 逐航線容錯 | P2 / S | flightdeals/pipeline.py:35、main.py:74-79 | route 迴圈本體包 try/except（比照 26-30 行對 source 的作法），單航線失敗只記警告不中斷；cmd_run 包 try/finally 保證 pipe.close()。多路同報：引擎 + 營運（ops 路對抗驗證後降 P2：例外會讓 Actions 變紅、非完全靜默） |
| 3.7 | window_days 死參數接線 | P2 / S | flightdeals/pipeline.py:35、config.py:15 | config 的 window_days 一路傳進 store.baseline()，或從 config 移除避免誤導。多路同報：引擎 + 資料 |
| 3.8 | 修既有 tsc 兩錯 | P2 / S | apps/mobile/App.tsx:40、src/notifications/push.ts:48 | createNavigationContainerRef 補泛型參數去掉 as never；projectId 改用型別斷言收斂成 string \| undefined（審查已附具體修法） |
| 3.9 | 價格輸入防呆 | P2 / S | apps/mobile/src/screens/DealsScreen.tsx:55-58 | onChangeText 加 debounce（每個按鍵現在都打一次 API）；驗證改 Number.isFinite（現在擋不住 Infinity，會回 400 且錯誤訊息文不對題）；選做 AbortController 防競態 |
| 3.10 | aviasales 連結 authority injection 防護 | P2 / S | flightdeals/ingest/travelpayouts.py:163-172 | 第三方回傳的 link path 強制以單一 `/` 開頭（或 urlsplit 取 .path，不合法就走自組路徑），阻斷 `@evil.com` 導去偽冒網域 |
| 3.11 | CI 安裝瘦身 | P2 / S | .github/workflows/fetch.yml:17-21 | setup-python 加 `cache: pip`；拆 requirements-fetch.txt（只留 pyyaml + psycopg）。CONFIRMED（對抗驗證後降 P2：實測安裝僅 6 秒、public repo 免費，屬可靠性加固） |

---

## 4. 中期（規劃性 / 大工程）

| # | 事項 | severity/effort | 落點 | 說明 |
|---|------|----------------|------|------|
| 4.1 | 基準線正確化（P0 根治） | P0 / L | flightdeals/storage/postgres_store.py:44-62、supabase_schema.sql:5-17、ingest/travelpayouts.py:84-85 | prices 表補 gate 欄位（現在 FarePrice.gate 存庫時被丟棄，gate 混雜是結構性的）、baseline 依 gate 與「距出發天數」分桶計算，處理不同出發月份季節性混池；並一併吸收被推翻那條 engine 發現殘留的合理部分（sorting=price 截斷樣本造成的靜態校準偏差與折扣百分比失真）。這是「這比平常便宜」這個核心承諾可不可信的根本。CONFIRMED P0（data 路） |
| 4.2 | 推播管線接通（P0 根治） | P0 / M | flightdeals/subscribers.py、notify/expo_push.py:60,64、config.prod.yaml:28-29 | 新寫 PostgresSubscriberRepo（讀 DATABASE_URL，對應 Supabase devices/subscriptions 表——目前後端沒有任何程式碼路徑讀得到前端寫進去的訂閱），config.prod.yaml notifiers 加 expo_push 並注入。多路同報：前端 + 產品（皆 CONFIRMED P0）。做完才把 2.1 的文案改回承諾 |
| 4.3 | 聯盟分潤接上 | P1 / M | flightdeals/ingest/travelpayouts.py:147-161,182-184 | 申請 Trip.com 聯盟（Allianceid/SID）補進 _trip_link()（docstring 自認待辦）；設定 TRAVELPAYOUTS_MARKER secret（實測 gh secret list 不存在）。程式改動小，卡點在聯盟帳號前置作業。CONFIRMED P1 |
| 4.4 | 降價舊卡下架 + 復現解噤聲 | P1 / M | flightdeals/storage/postgres_store.py:73-121、models.py:82 | 存新 deal 時把同 (type, route, depart_date) 較貴的舊 deal 標 superseded 或刪除；deals_seen 用既有 ts 欄位加 30-60 天時間窗，讓復現的 bug 票能重新觸發。CONFIRMED P1 |
| 4.5 | 深連結 + 分享 + OG metadata | P2 / M | apps/mobile/App.tsx:62、src/api/client.ts:94-98、app.json | NavigationContainer 加 linking 對應 /deal/:id（用閒置的 api.deal(id) 還原畫面，順帶修 Web 重新整理掉回首頁）；加分享按鈕（Share API）；補 og:title/description/image、lang=zh-Hant、PWA manifest。多路同報：前端 + 產品——自然增長管道兩端目前都缺 |
| 4.6 | RLS ownership 根治 | P1 / M | supabase_schema.sql:80-90、前端 auth | 改用 Supabase Anonymous Auth，policy 全部改成 device = auth.uid()::text 只准操作自己那列（審查附完整 SQL）；同時解決 3.1/3.2 的止血遺留 |
| 4.7 | 無障礙屬性補齊 | P2 / M | apps/mobile/src/screens/DealsScreen.tsx 等 | 全 src 零筆 accessibilityRole/Label；至少補訂票 CTA、篩選 chip、清除鈕、面板展開鈕 |
| 4.8 | errorfare 高艙等死碼處置 | P2 / S-M | flightdeals/detectors/errorfare.py:35、ingest/travelpayouts.py:121 | cabin 被寫死 ECONOMY，高艙等規則永遠不可達；確認 API 是否帶艙等欄位，沒有就移除規則並在 docstring 註明，有就補解析。多路同報：引擎 + 資料（也是 3.4 BUG 票零筆的備用觸發路徑失效原因） |

---

## 5. 已知但暫緩

- 【被推翻】「cheap 基準線建立在已篩最低價樣本上，自我循環、偵測力隨時間衰退」（engine P0）：對抗驗證 REFUTED——基準線是 90 天滾動窗對全部報價取分位數，門檻不會單調下壓、觸發率不會逐漸稀疏；殘留的截斷偏誤與季節混池屬靜態校準精度問題，已併入 4.1 一起處理。
- datetime.utcnow() 棄用與 naive/aware 混用（P3/S，models.py:37 等 5 檔）：現在能跑靠 Supabase session timezone 剛好是 UTC；改 datetime.now(timezone.utc) 即可，隨手修。
- InMemoryStore 忽略 window_days（P3/S，storage/memory.py:28）：僅測試/demo 用，docstring 註明即可。
- GitHub Actions 釘 commit SHA + requirements lock 檔（P3/S，fetch.yml:16-17）：防禦縱深加固，非急迫。
- concurrency queue 疊跑行為（P3，fetch.yml:11）：審查者自承未查證到官方文件，最壞只是多打幾次 API，先觀察。
- 抓票頻率 15 分 vs API 48 小時快取（P2 取捨，fetch.yml:5）：拉長到 30-60 分可緩解 DB 膨脹，但 2.4 retention 上線後壓力大減，屆時再評估。
- 兩條 UNVERIFIED（無分頁 3.5、設定開關 2.1 附帶）：超出該輪對抗驗證額度，採用前建議先花十分鐘實測復現。

---

## 6. 各角度檢查覆蓋清單（透明化：誰查了什麼）

**引擎正確性**：pipeline.run_once 全流程、models 資料結構與 dedupe_key、stats 邊界（空序列/mad=0/n=20 插值）、三個 detector 判定邏輯、travelpayouts API 參數與深連結組法、三個 store 對 base.py 介面契約的一致性（p10/p05、window_days）、serializers 與 schema 對齊、registry/config 接線、main.py 各子命令、既有測試覆蓋缺口（SQLiteStore.baseline 以腳本實測復現）、datetime.utcnow 全 repo 盤點。

**資料品質**：baseline SQL 篩選條件、prices 表 schema/index/unique、add_prices 去重、gate 欄位存庫追蹤、sample_size 門檻達成速度推演、percentile n=20 邊界、prices 成長速率估算對照 Supabase 500MB、store 寫入例外處理、dedupe_key 與 deals_seen TTL、window_days 消費追蹤、errorfare 高艙等可達性、確認無對真 Supabase 的測試。

**前端 UX**：apps/mobile/src 全檔精讀、實跑 tsc 重現兩錯並定位根因、grep 佐證（created_at/無障礙/持久化儲存/linking/api.deal 皆零使用）、PostgREST 組字串注入面排除、devices/subscriptions CRUD 與 RLS 核對、推播管線斷鏈追蹤（含讀 expo-notifications 原始碼證實 Web 必 throw）、DealCard 與 DealDetail 欄位差異比對、loading/error/empty 與篩選交互、Linking.openURL 錯誤處理。

**資安**：五張表 RLS 逐條、前端 query 注入面（皆 encodeURIComponent/Number 轉換）、ownership 檢查串接到 push token 實際內容、deep_link 產生與使用鏈（發現 aviasales 分支缺路徑前綴檢查）、workflow secret 用法與 action 釘選、.gitignore、git 全歷史掃密（JWT/連線字串/金鑰 pattern，皆無命中）、.env.example、requirements 釘選、postgres_store SQL 參數化、notify 模組外呼、外鍵/RPC 繞 RLS 攻擊面（無）。

**營運可靠性**：fetch.yml 全檔（trigger/timeout/concurrency/安裝/env）、main.py 例外路徑、config.prod.yaml 參數、pipeline 容錯逐行、postgres_store 連線模式、notify/repository 落地、travelpayouts 逾時與快取敘述、detector guard、全專案 grep 清除邏輯（零筆）、requirements 逐項比對 run 路徑 import、SUPABASE_DEPLOY.md、前端輪詢檢查（無）、外部查證三項官方文件（Travelpayouts 速率限制、GitHub 60 天停排程、Supabase 免費方案暫停與額度）。

**產品轉化**：detector 門檻邏輯、正式環境 notifier/detector/source 實際啟用值、推播「命中到送出」全路徑、前端裝置註冊與訂閱寫入去向、schema 前後端資料流比對、兩條外導連結聯盟參數檢查、實際開啟 prod 網站（好康密度/BUG 票分頁/篩選面板）、network 面板核對 REST 端點、curl 首頁原始碼與 manifest/robots（OG/meta/lang/PWA 皆缺）、卡片與詳情渲染欄位、created_at 型別使用追蹤、全 repo 分享機制 grep（零筆）、app.json web 設定。
