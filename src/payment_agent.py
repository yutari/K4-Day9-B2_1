from collections import OrderedDict
import pandas as pd

from src.models import PaymentPayload


def _stable_unique(values):
    """Loại bỏ phần tử trùng nhưng giữ nguyên thứ tự."""
    return list(OrderedDict.fromkeys(v for v in values if pd.notna(v)))


def process_payment(
    claimed_order_id: str,
    expected_total_brl_from_items: float = 0.0,
) -> PaymentPayload:
    """
    Đọc order_payments.csv.

    Với claimed_order_id:
        - Tính payment_total_brl.
        - Đối soát với expected_total_brl_from_items.
        - Tính difference_brl.
        - Xác định reconciled.
        - Xác định is_split_payment.
        - Trả về payment_ids và payment_types.
    """

    # ==========================
    # Load CSV
    # ==========================

    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"

    payments_df = pd.read_csv(
        DATA_DIR / "olist_order_payments_dataset.csv"
    )

    # ==========================
    # Payments của order
    # ==========================

    payments = (
        payments_df[
            payments_df["order_id"] == claimed_order_id
        ]
        .sort_values("payment_sequential")
        .copy()
    )

    if payments.empty:
        return PaymentPayload(
            expected_total_brl=expected_total_brl_from_items,
            payment_total_brl=0.0,
            difference_brl=-expected_total_brl_from_items,
            reconciled=False,
            is_split_payment=False,
            payment_types=[],
            payment_ids=[],
        )

    # ==========================
    # Tổng tiền thanh toán
    # ==========================

    payment_total = float(
        payments["payment_value"].sum()
    )

    # ==========================
    # Chênh lệch
    # ==========================

    difference = round(
        payment_total - expected_total_brl_from_items,
        2,
    )

    # Cho phép sai số nhỏ do float
    reconciled = abs(difference) < 0.01

    # ==========================
    # Split Payment
    # ==========================

    is_split_payment = len(payments) > 1

    # ==========================
    # Payment Types
    # ==========================

    payment_types = _stable_unique(
        payments["payment_type"].tolist()
    )

    # ==========================
    # Payment IDs
    # ==========================

    payment_ids = [
        f"{row.order_id}:{int(row.payment_sequential)}"
        for _, row in payments.iterrows()
    ]

    # ==========================
    # Output
    # ==========================

    return PaymentPayload(
        expected_total_brl=round(
            expected_total_brl_from_items,
            2,
        ),
        payment_total_brl=round(
            payment_total,
            2,
        ),
        difference_brl=difference,
        reconciled=reconciled,
        is_split_payment=is_split_payment,
        payment_types=payment_types[:5],
        payment_ids=payment_ids[:5],
    )