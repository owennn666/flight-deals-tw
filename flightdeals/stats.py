"""基準線用的穩健統計（獨立、純函式、好測試）。"""
from __future__ import annotations

import statistics
from typing import Optional, Sequence


def median(xs: Sequence[float]) -> float:
    return statistics.median(xs)


def mad(xs: Sequence[float], med: Optional[float] = None) -> float:
    """Median Absolute Deviation：抗離群值的離散度指標。"""
    if not xs:
        return 0.0
    m = med if med is not None else statistics.median(xs)
    return statistics.median([abs(x - m) for x in xs])


def robust_z(x: float, med: float, mad_val: float) -> float:
    """穩健 z 分數。值越『正』代表 x 越低於中位數（越便宜）。

    mad 為 0（資料無離散）時退化回傳 0，避免除零。
    """
    if mad_val <= 0:
        return 0.0
    return 0.6745 * (med - x) / mad_val
