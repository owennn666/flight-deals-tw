"""把 Deal 轉成 API/儲存用的純 dict（JSON 友善，前後端型別對齊的單一來源）。"""
from __future__ import annotations

from .models import Deal


def deal_to_dict(deal: Deal) -> dict:
    f = deal.fare
    return {
        "type": deal.deal_type.value,
        "route": {"origin": f.route.origin, "destination": f.route.destination},
        "route_str": str(f.route),
        "price": f.price,
        "currency": f.currency,
        "cabin": f.cabin.value,
        "depart_date": f.depart_date.isoformat() if f.depart_date else None,
        "return_date": f.return_date.isoformat() if f.return_date else None,
        "baseline_median": deal.baseline_median,
        "discount_pct": deal.discount_pct,
        "tier": deal.tier,
        "needs_verification": deal.needs_verification,
        "reasons": list(deal.reasons),
        "deep_link": f.deep_link,
        "source": f.source,
        "dedupe_key": deal.dedupe_key(),
    }
