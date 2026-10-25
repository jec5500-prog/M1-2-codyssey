from typing import List, Dict, Any
from math import isfinite

TREND_WINDOW = 7

def _compute_trend(values: List[float]) -> Dict[str, Any]:
    window = min(len(values), TREND_WINDOW)
    if window < 2:
        return {
            "direction": "insufficient",
            "label": "데이터 부족 (2건 이상 필요)",
            "window": window,
            "slope": None,
            "change_percent": None,
            "recent_average": values[-1] if values else None,
        }

    recent = values[-window:]
    mean_x = (window - 1) / 2
    mean_y = sum(recent) / window
    num = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(recent))
    den = sum((x - mean_x) ** 2 for x in range(window))
    slope = num / den if den else 0.0

    base = abs(mean_y)
    if base > 0:
        rel = slope / base
    else:
        rel = 1.0 if slope > 0 else (-1.0 if slope < 0 else 0.0)

    if rel > 0.01:
        direction, label = "up", "상승 추세"
    elif rel < -0.01:
        direction, label = "down", "하락 추세"
    else:
        direction, label = "flat", "보합 (큰 변화 없음)"

    first, last = recent[0], recent[-1]
    change_percent = ((last - first) / abs(first) * 100) if first != 0 else None
    if change_percent is not None and not isfinite(change_percent):
        change_percent = None

    return {
        "direction": direction,
        "label": label,
        "window": window,
        "slope": round(slope, 4),
        "change_percent": round(change_percent, 2) if change_percent is not None else None,
        "recent_average": round(mean_y, 4),
    }


def compute_summary(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """건수 / 평균 / 최소·최대 / 최근 추세 요약 (챗 시스템 프롬프트에서도 재사용)."""
    pts = sorted(points, key=lambda p: p["date"])
    n = len(pts)
    if n == 0:
        return {
            "count": 0,
            "average": None,
            "total": None,
            "minimum": None,
            "maximum": None,
            "latest": None,
            "first_date": None,
            "last_date": None,
            "trend": _compute_trend([]),
        }

    values = [p["value"] for p in pts]
    total = sum(values)
    min_p = min(pts, key=lambda p: p["value"])
    max_p = max(pts, key=lambda p: p["value"])

    def ref(p):
        return {"date": p["date"], "value": p["value"], "memo": p.get("memo", "")}

    return {
        "count": n,
        "average": round(total / n, 4),
        "total": round(total, 4),
        "minimum": ref(min_p),
        "maximum": ref(max_p),
        "latest": ref(pts[-1]),
        "first_date": pts[0]["date"],
        "last_date": pts[-1]["date"],
        "trend": _compute_trend(values),
    }
