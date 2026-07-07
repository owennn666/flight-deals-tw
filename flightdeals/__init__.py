"""便宜機票偵測平台 — 模組化骨架。

四層可插拔架構：
    ingest（資料源） → storage（儲存/基準線） → detectors（偵測器） → notify（通知）
各層都以介面（ABC）定義，實作可透過 registry 以名稱抽換。
"""

__version__ = "0.1.0"
