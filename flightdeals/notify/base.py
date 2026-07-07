"""通知介面 + 共用的訊息格式化。新增管道只要實作 send()。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Deal, DealType

_BADGE = {
    DealType.CHEAP: "💰 便宜票",
    DealType.ERROR_FARE: "🐞 疑似 BUG 票",
    DealType.NESTED: "🧩 構票",
}


def format_deal(deal: Deal) -> str:
    """把 Deal 轉成一段人看得懂的文字（各通知管道共用）。"""
    f = deal.fare
    badge = _BADGE.get(deal.deal_type, "✈️ 好康")
    lines = [
        f"{badge}｜{f.route}",
        f"價格 {f.price:.0f} {f.currency}（基準 {deal.baseline_median:.0f}，省 {deal.discount_pct * 100:.0f}%）",
    ]
    if f.depart_date:
        lines.append(f"出發：{f.depart_date}")
    for r in deal.reasons:
        lines.append(f"• {r}")
    if deal.needs_verification:
        lines.append("⚠️ 疑似標錯價，航司不保證出票，訂票風險自負，建議先別訂旅館。")
    if f.deep_link:
        lines.append(f"訂票：{f.deep_link}")
    return "\n".join(lines)


class Notifier(ABC):
    name: str = "base"

    @abstractmethod
    def send(self, deal: Deal) -> bool:
        """送出通知，成功回傳 True。"""
        raise NotImplementedError
