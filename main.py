#!/usr/bin/env python3
"""CLI 入口。

用法：
    python main.py demo                 # 離線示範，不需 API key，印出好康
    python main.py seed                 # 為 SQLite 注入合成歷史，讓基準線可用
    python main.py run                  # 跑一輪偵測（會把好康存進 DB 供 API 讀）
    python main.py run -c config.yaml   # 用自訂設定
    python main.py serve                # 啟動 FastAPI（給 RN App 打的 API）
"""
from __future__ import annotations

import argparse
import os

from flightdeals.config import load_config, load_dotenv
from flightdeals.detectors.cheap import CheapFareDetector
from flightdeals.detectors.errorfare import ErrorFareDetector
from flightdeals.ingest.mock import MockDataSource
from flightdeals.models import Route
from flightdeals.notify.console import ConsoleNotifier
from flightdeals.notify.repository import RepositoryNotifier
from flightdeals.pipeline import Pipeline
from flightdeals.registry import DETECTORS, NOTIFIERS, SOURCES, STORES
from flightdeals.seed import seed_history
from flightdeals.storage.memory import InMemoryStore


def _routes(cfg) -> list[Route]:
    return [Route(o, d) for o, d in cfg["routes"]]


def build_pipeline(cfg) -> Pipeline:
    """依設定 + registry 組出 pipeline（可插拔的核心）。

    另外自動掛上 RepositoryNotifier，把每筆好康存進 store 供 API 查詢。
    """
    sources = [SOURCES[s["name"]](**s.get("params", {})) for s in cfg["sources"]]
    store = STORES[cfg["store"]["name"]](**cfg["store"].get("params", {}))
    detectors = [DETECTORS[d["name"]](**d.get("params", {})) for d in cfg["detectors"]]
    notifiers = [NOTIFIERS[n["name"]](**n.get("params", {})) for n in cfg["notifiers"]]
    notifiers.append(RepositoryNotifier(store))  # 好康持久化，供 FastAPI /deals 讀取
    window_days = cfg.get("window_days", 90)
    return Pipeline(sources, store, detectors, notifiers, window_days=window_days)


def cmd_demo(_args) -> None:
    """離線示範：記憶體儲存 + 注入歷史 + 強制注入兩類異常，保證看得到輸出。"""
    cfg = load_config()
    routes = _routes(cfg)
    store = InMemoryStore()
    seeded = seed_history(store, routes)
    print(f"[demo] 已注入 {seeded} 筆合成歷史，開始偵測…\n")

    for force in ("cheap", "error"):
        pipe = Pipeline(
            sources=[MockDataSource(seed=1, force=force)],
            store=store,
            detectors=[CheapFareDetector(), ErrorFareDetector()],
            notifiers=[ConsoleNotifier(), RepositoryNotifier(store)],
        )
        deals = pipe.run_once(routes)
        print(f"\n[demo] force={force} → 觸發 {len(deals)} 筆好康\n")
    print(f"[demo] 目前已持久化好康：{len(store.recent_deals(limit=999))} 筆（API /deals 可讀）")


def cmd_seed(args) -> None:
    cfg = load_config(args.config)
    pipe = build_pipeline(cfg)
    n = seed_history(pipe.store, _routes(cfg))
    pipe.close()
    print(f"[seed] 已為 {len(cfg['routes'])} 條航線注入共 {n} 筆合成歷史。")


def cmd_run(args) -> None:
    cfg = load_config(args.config)
    pipe = build_pipeline(cfg)
    try:
        deals = pipe.run_once(_routes(cfg))
        pruned = pipe.store.prune()
        print(f"[run] 清理 {pruned} 筆 95 天前舊價")
    finally:
        pipe.close()
    print(f"\n[run] 本輪偵測到 {len(deals)} 筆好康（已存入 DB，API /deals 可讀）。")


def cmd_demo_data(args) -> None:
    """把示範好康寫進『設定的 store』（預設 SQLite），讓 serve 後 App 立刻有東西看（離線、免 token）。"""
    cfg = load_config(args.config)
    store = STORES[cfg["store"]["name"]](**cfg["store"].get("params", {}))
    routes = _routes(cfg)
    seed_history(store, routes)
    for force in ("cheap", "error"):
        Pipeline(
            sources=[MockDataSource(seed=1, force=force)],
            store=store,
            detectors=[CheapFareDetector(), ErrorFareDetector()],
            notifiers=[RepositoryNotifier(store)],
        ).run_once(routes)
    n = len(store.recent_deals(limit=999))
    store.close()
    print(f"[demo-data] 已寫入示範好康 {n} 筆到 DB（serve 後 App 就看得到）。")


def _start_poller(config_path, interval: int) -> None:
    """背景執行緒：每 interval 秒抓一次票（雲端 24hr 自動更新用）。"""
    import threading
    import time

    def loop():
        while True:
            try:
                cfg = load_config(config_path)
                pipe = build_pipeline(cfg)
                deals = pipe.run_once(_routes(cfg))
                pipe.close()
                print(f"[poll] 更新完成，本輪 {len(deals)} 筆新好康")
            except Exception as e:  # 抓票失敗不該讓服務掛掉
                print(f"[poll] 抓取失敗：{e}")
            time.sleep(interval)

    threading.Thread(target=loop, daemon=True).start()
    print(f"[poll] 已啟動背景排程：每 {interval} 秒（{interval // 60} 分）抓一次票")


def cmd_serve(args) -> None:
    try:
        import uvicorn
    except ImportError:
        print("需要 fastapi + uvicorn：pip install fastapi 'uvicorn[standard]'")
        return
    from flightdeals.api.app import create_app

    if args.poll > 0:
        _start_poller(args.config, args.poll)

    app = create_app()
    print(f"[serve] FastAPI 啟動於 http://{args.host}:{args.port}　（/docs 可看 API 文件）")
    uvicorn.run(app, host=args.host, port=args.port)


def main() -> None:
    parser = argparse.ArgumentParser(description="便宜機票偵測平台 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("demo", help="離線示範（不需 API key）").set_defaults(func=cmd_demo)

    p_seed = sub.add_parser("seed", help="注入合成歷史讓基準線可用")
    p_seed.add_argument("-c", "--config", default=None)
    p_seed.set_defaults(func=cmd_seed)

    p_run = sub.add_parser("run", help="跑一輪偵測（好康存入 DB）")
    p_run.add_argument("-c", "--config", default=None)
    p_run.set_defaults(func=cmd_run)

    p_demo_data = sub.add_parser("demo-data", help="寫入示範好康到 DB（離線，給 App 看）")
    p_demo_data.add_argument("-c", "--config", default=None)
    p_demo_data.set_defaults(func=cmd_demo_data)

    p_serve = sub.add_parser("serve", help="啟動 FastAPI（給 App / 網頁）")
    p_serve.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    p_serve.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    p_serve.add_argument("--poll", type=int, default=int(os.getenv("POLL_SECONDS", "0")),
                         help="背景每 N 秒自動抓票（0=關閉；雲端設 900=15 分）")
    p_serve.add_argument("-c", "--config", default=None, help="抓票用設定檔（如 config.prod.yaml）")
    p_serve.set_defaults(func=cmd_serve)

    load_dotenv()  # 若專案有 .env，自動載入 token 等設定
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
