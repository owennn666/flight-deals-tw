"""設定：預設用純 Python dict（零依賴即可跑），可選擇性讀 YAML 覆蓋。"""
from __future__ import annotations

import os
from typing import Optional

# 台灣出發的示範航線（可自行增減）
DEFAULT_ROUTES = [
    ("TPE", "NRT"), ("TPE", "KIX"), ("TPE", "ICN"),
    ("TPE", "BKK"), ("TPE", "DAD"), ("TPE", "CDG"), ("TPE", "LHR"),
]

DEFAULT_CONFIG: dict = {
    "routes": DEFAULT_ROUTES,
    "window_days": 90,
    # 資料源：預設 mock（離線）。上線改成 travelpayouts（見 config.example.yaml）
    "sources": [{"name": "mock", "params": {}}],
    # DB 路徑可用環境變數 FLIGHTDEALS_DB 覆蓋（雲端部署時指向持久化 volume，如 /data/flightdeals.db）
    "store": {"name": "sqlite", "params": {"path": os.getenv("FLIGHTDEALS_DB", "flightdeals.db")}},
    "detectors": [
        {"name": "cheap", "params": {"threshold": 0.25, "strong": 0.40}},
        {"name": "error_fare", "params": {"threshold": 0.70}},
    ],
    "notifiers": [{"name": "console", "params": {}}],
}


def load_config(path: Optional[str] = None) -> dict:
    """讀設定。未指定或未安裝 pyyaml 時，回傳預設設定。"""
    cfg = {k: v for k, v in DEFAULT_CONFIG.items()}
    if not path:
        return cfg
    try:
        import yaml  # 選用依賴
        with open(path, "r", encoding="utf-8") as f:
            user = yaml.safe_load(f) or {}
        cfg.update(user)
    except ImportError:
        print("[warn] 未安裝 pyyaml，改用預設設定（pip install pyyaml 可讀 config.yaml）")
    except FileNotFoundError:
        print(f"[warn] 找不到設定檔 {path}，改用預設設定")
    return cfg


def load_dotenv(path: str = ".env") -> None:
    """極簡 .env 載入（零依賴）：把 KEY=VALUE 讀進 os.environ（不覆蓋既有值）。"""
    import os
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
