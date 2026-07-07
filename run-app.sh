#!/usr/bin/env bash
# 一鍵啟動 App（iOS / Android / Web，同一套 React Native 碼）
# 用法：另開一個終端機，執行  bash run-app.sh
# 前提：先啟動後端（bash run-backend.sh）
set -e
cd "$(dirname "$0")/apps/mobile"

echo "==> 安裝 App 套件（第一次比較久）"
npm install

echo "==> 啟動 Expo"
echo "    · 按 w 開網頁版"
echo "    · 按 i 開 iOS 模擬器（需 Xcode）"
echo "    · 手機裝 Expo Go App 掃 QR code"
echo "    注意：實體手機請把 apps/mobile/app.json 的 apiBaseUrl 改成你電腦的區網 IP"
npx expo start
