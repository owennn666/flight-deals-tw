# 便宜機票 App（React Native + Expo）

台灣出發便宜票 / BUG 票 / 四腳票平台的**手機客戶端**。薄客戶端：只負責看好康、管訂閱、收推播；偵測都在 Python 後端跑。

## 需求
- Node.js 18+
- 手機裝 **Expo Go**（開發預覽用），或用 iOS/Android 模擬器
- 後端已啟動（見專案根目錄 `../../README.md` 的 `python main.py serve`）

## 安裝與啟動
```bash
cd apps/mobile
npm install
npx expo install        # 對齊 Expo SDK 相依版本（建議跑一次）
npx expo start          # 掃 QR code 用 Expo Go 開，或按 i / a 開模擬器
```

## 連到後端 API（重要）
App 要打到你的 FastAPI 後端。改 `app.json` 的 `expo.extra.apiBaseUrl`：
- iOS 模擬器：`http://localhost:8000`
- Android 模擬器：`http://10.0.2.2:8000`
- **實體手機**：跟電腦同一個 Wi-Fi，設成電腦區網 IP，例：`http://192.168.0.10:8000`

## 專案結構
```
apps/mobile/
  App.tsx                     # 進入點 + 導覽（底部 Tab + Deals Stack）
  app.json                    # Expo 設定（含 apiBaseUrl）
  src/
    config.ts                 # 讀 API base URL
    api/
      types.ts                # 與後端對齊的型別
      client.ts               # typed fetch 封裝（呼叫 /api/*）
    components/
      DealCard.tsx            # 好康卡片
    screens/
      DealsScreen.tsx         # 好康列表（篩選 + 下拉刷新）
      DealDetailScreen.tsx    # 詳情 + BUG 票免責 + 訂票（聯盟）按鈕
      SubscriptionsScreen.tsx # 訂閱航線/預算
      SettingsScreen.tsx      # 推播開關 + 風險說明
    notifications/
      push.ts                 # Expo push 註冊 → 打 /api/devices
```

## 推播說明
- **Expo Go** 可看 UI，但要拿真正的 push token、收原生通知，建議用 **development build**（`npx expo run:ios` / `run:android`）或實體裝置。
- 目前 `push.ts` 的裝置 id 存在記憶體，重開會變；正式版請用 `expo-secure-store` 持久化。

## 注意
- 這是 **scaffold**：畫面、狀態管理、錯誤處理都可再擴充（可加 React Query、深色模式、i18n）。
- App 不代訂機票，訂票一律開外部連結（聯盟）。BUG 票、四腳票的風險免責已內建於畫面。
