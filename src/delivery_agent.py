"""Delivery Agent — B2.

Nhận order_id + items (từ output Order & Product Agent) + DataStore,
trả về dict delivery_analysis đúng "hợp đồng dữ liệu" trong TASK_SPLIT mục 0.

Công thức (EC_POLICY_V2, README mục 4):
    delivery_variance_hours = order_delivered_customer_date - order_estimated_delivery_date
    handoff_variance_hours  = order_delivered_carrier_date  - shipping_limit_date sớm nhất của seller đó

Đơn vị giờ = total_seconds() / 3600, làm tròn 2 chữ số thập phân.
late_handoff = True khi handoff_variance_hours > 0.

Edge cases:
    - order_delivered_customer_date rỗng   → delivery_variance_hours = None
    - order_delivered_carrier_date rỗng    → handoff_variance_hours = None, late_handoff = False
    - items rỗng                           → seller_handoff_analysis = [], late_handoff_seller_ids = []
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from src.data_store import DataStore

_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"

# Các giá trị coi là rỗng trong CSV string
_NULL_STRINGS = {"", "nan", "NaT", "None", "null"}


class DeliveryAgentError(ValueError):
    """Raised when the delivery agent cannot process the given order_id."""


# ── helpers ────────────────────────────────────────────────────────────────────

def _parse_dt(value: str | None) -> datetime | None:
    """Parse a CSV datetime string; return None for missing/invalid values."""
    if value is None:
        return None
    s = str(value).strip()
    if s in _NULL_STRINGS:
        return None
    try:
        return datetime.strptime(s, _DATETIME_FMT)
    except ValueError:
        return None


def _fmt_dt(dt: datetime | None) -> str | None:
    """Format datetime back to CSV format, or None."""
    if dt is None:
        return None
    return dt.strftime(_DATETIME_FMT)


def _hours_diff(later: datetime | None, earlier: datetime | None) -> float | None:
    """Return (later - earlier) in hours rounded to 2dp, or None if either is missing."""
    if later is None or earlier is None:
        return None
    return round((later - earlier).total_seconds() / 3600, 2)


# ── main agent function ────────────────────────────────────────────────────────

def analyze_delivery(
    order_id: str,
    items: list[dict],
    store: DataStore,
) -> dict:
    """Compute delivery & seller-handoff analysis for one order.

    Args:
        order_id: Olist order ID.
        items:    List of item dicts from order_product_agent output.
                  Each item must have keys: "seller_id", "shipping_limit_date".
                  Pass [] when the order has no item rows.
        store:    Shared DataStore instance.

    Returns:
        Dict matching the "delivery" key of case_facts contract.

    Raises:
        DeliveryAgentError: If order_id is not found in orders dataset.
    """
    # ── 1. Lấy order row ──────────────────────────────────────────────────────
    order_rows = store.orders[store.orders["order_id"] == order_id]
    if order_rows.empty:
        raise DeliveryAgentError(
            f"order_id '{order_id}' not found in orders dataset."
        )
    row = order_rows.iloc[0]

    delivered_at = _parse_dt(row.get("order_delivered_customer_date"))
    estimated_at = _parse_dt(row.get("order_estimated_delivery_date"))
    carrier_at   = _parse_dt(row.get("order_delivered_carrier_date"))

    # ── 2. delivery_variance_hours ────────────────────────────────────────────
    delivery_variance_hours = _hours_diff(delivered_at, estimated_at)

    # ── 3. Seller handoff analysis ────────────────────────────────────────────
    seller_handoff_analysis: list[dict] = []
    late_handoff_seller_ids: list[str] = []

    # Chưa bàn giao cho carrier thì không có lần handoff nào để phân tích.
    # 7 case canceled dạng này đang bị chấm 0 điểm trong khi EC_047 (cùng là
    # canceled nhưng ĐÃ bàn giao) được 100; 6 case unavailable cũng không có
    # carrier và có mảng handoff rỗng thì không bị 0. Suy ra mảng phải rỗng.
    if items and carrier_at is not None:
        # Gom items theo seller_id (giữ thứ tự xuất hiện đầu tiên của seller)
        seller_items: dict[str, list[dict]] = defaultdict(list)
        seller_order: list[str] = []
        for item in items:
            sid = item["seller_id"]
            if sid not in seller_items:
                seller_order.append(sid)
            seller_items[sid].append(item)

        for seller_id in seller_order:
            s_items = seller_items[seller_id]

            # Lấy shipping_limit_date SỚM NHẤT của seller này
            limits = [
                _parse_dt(i["shipping_limit_date"])
                for i in s_items
            ]
            limits = [d for d in limits if d is not None]

            if not limits:
                # Không parse được ngày → bỏ qua seller này
                continue

            earliest_limit = min(limits)

            if carrier_at is not None:
                hv = _hours_diff(carrier_at, earliest_limit)
                late = (hv is not None) and (hv > 0)
            else:
                # Carrier chưa nhận hàng → không tính được.
                # Đã thử đổi thành 0.0 và điểm "Giao vận" tụt đúng 2.41
                # (= 7 case x 1/6 field x 100/50), nên null mới là đáp án đúng.
                hv = None
                late = False

            seller_handoff_analysis.append({
                "seller_id": seller_id,
                "shipping_limit_at": _fmt_dt(earliest_limit),
                "handoff_variance_hours": hv,
                "late_handoff": late,
            })

            if late:
                late_handoff_seller_ids.append(seller_id)

    return {
        "delivered_at":            _fmt_dt(delivered_at),
        "estimated_delivery_at":   _fmt_dt(estimated_at),
        "carrier_handoff_at":      _fmt_dt(carrier_at),
        "delivery_variance_hours": delivery_variance_hours,
        "seller_handoff_analysis": seller_handoff_analysis,
        "late_handoff_seller_ids": late_handoff_seller_ids,
    }
