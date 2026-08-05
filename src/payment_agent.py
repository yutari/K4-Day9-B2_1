"""Payment Agent — B1.

Nhận order_id + items (từ output Order & Product Agent) + DataStore,
trả về dict payment_reconciliation đúng "hợp đồng dữ liệu" trong TASK_SPLIT mục 0.

Công thức (EC_POLICY_V2, README mục 4):
    item_total_brl     = sum(items.price)
    freight_total_brl  = sum(items.freight_value)
    expected_total_brl = item_total_brl + freight_total_brl
    payment_total_brl  = sum(order_payments.payment_value)
    difference_brl     = payment_total_brl - expected_total_brl
    reconciled         = abs(difference_brl) <= 0.10

Edge case — items rỗng (không có item row):
    expected_total_brl, difference_brl, reconciled = None
    payment_total_brl và payment_types vẫn tính bình thường.
"""

from __future__ import annotations

from src.data_store import DataStore


class PaymentAgentError(ValueError):
    """Raised when the payment agent cannot process the given order_id."""


def analyze_payment(
    order_id: str,
    items: list[dict],
    store: DataStore,
) -> dict:
    """Compute payment reconciliation for one order.

    Args:
        order_id: Olist order ID.
        items:    List of item dicts from order_product_agent output.
                  Each item must have keys: "price", "freight_value".
                  Pass [] when the order has no item rows.
        store:    Shared DataStore instance.

    Returns:
        Dict matching the "payment" key of case_facts contract.

    Raises:
        PaymentAgentError: If order_id has no payment rows at all
                           (unexpected — even cancelled orders can have payments).
    """
    # ── 1. Lọc payment rows theo order_id ─────────────────────────────────────
    df = store.order_payments[store.order_payments["order_id"] == order_id].copy()

    # CSV không đảm bảo payment_sequential tăng dần (9/50 case của đề bị đảo,
    # ví dụ EC_008 là 2 rồi mới tới 1). payment_sequential chính là số thứ tự
    # của payment nên "thứ tự theo dữ liệu nguồn" là thứ tự tăng dần của nó.
    df = df.sort_values("payment_sequential", key=lambda s: s.astype(int))

    # payment_ids: danh sách payment_sequential (string), giữ thứ tự nguồn
    payment_ids: list[str] = df["payment_sequential"].tolist()

    # payment_total: tổng payment_value (BRL), làm tròn 2 chữ số
    payment_total_brl = round(
        df["payment_value"].astype(float).sum(), 2
    )

    # payment_types: unique, giữ thứ tự xuất hiện đầu tiên
    seen: dict[str, None] = {}
    for pt in df["payment_type"].tolist():
        seen[pt] = None
    payment_types: list[str] = list(seen.keys())

    # ── 2. Tính item/freight nếu có items ─────────────────────────────────────
    if not items:
        # README mục 4 chỉ yêu cầu null cho ĐÚNG 3 trường: expected_total_brl,
        # difference_brl, reconciled. item_total_brl/freight_total_brl là tổng
        # trên tập rỗng nên vẫn là số (0.0), không phải null.
        return {
            "payment_ids": payment_ids,
            "item_total_brl": 0.0,
            "freight_total_brl": 0.0,
            "expected_total_brl": None,
            "payment_total_brl": payment_total_brl,
            "difference_brl": None,
            "reconciled": None,
            "payment_types": payment_types,
        }

    item_total_brl = round(
        sum(float(item["price"]) for item in items), 2
    )
    freight_total_brl = round(
        sum(float(item["freight_value"]) for item in items), 2
    )
    expected_total_brl = round(item_total_brl + freight_total_brl, 2)
    difference_brl = round(payment_total_brl - expected_total_brl, 2)
    reconciled = bool(abs(difference_brl) <= 0.10)

    return {
        "payment_ids": payment_ids,
        "item_total_brl": item_total_brl,
        "freight_total_brl": freight_total_brl,
        "expected_total_brl": expected_total_brl,
        "payment_total_brl": payment_total_brl,
        "difference_brl": difference_brl,
        "reconciled": reconciled,
        "payment_types": payment_types,
    }
