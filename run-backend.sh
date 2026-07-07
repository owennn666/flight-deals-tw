#!/usr/bin/env bash
# 一鍵啟動後端（用 uv 管理獨立 Python，避開壞掉的 Homebrew Python）
# 用法：bash run-backend.sh   （需先： brew install uv）
set -e
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "需要 uv。請先執行：  brew install uv   然後再跑一次  bash run-backend.sh"
  exit 1
fi

# 只用 uv 自己下載的獨立 Python（不碰系統/Homebrew 那個壞掉的）
export UV_PYTHON_PREFERENCE=only-managed
VENV="$HOME/.flightdeals-venv"
PORT=8010   # 8000 被別的程式佔用，改用 8010（App 也已指向 8010）

echo "==> [1/3] 準備獨立 Python 3.12 + 安裝套件（第一次比較久）"
uv python install 3.12
rm -rf "$VENV"
uv venv --python 3.12 "$VENV"
uv pip install --python "$VENV/bin/python" -r requirements.txt

PY="$VENV/bin/python"
echo "==> [2/3] 寫入示範好康資料（離線、免 token）"
"$PY" main.py demo-data
echo "    （要抓真實票價：.env 放好 TRAVELPAYOUTS_TOKEN 後，跑  $PY main.py run -c config.yaml）"

echo "==> [3/3] 啟動 API → http://localhost:$PORT     （API 文件：http://localhost:$PORT/docs）"
echo "    按 Ctrl+C 可停止。"
"$PY" main.py serve --port "$PORT"
