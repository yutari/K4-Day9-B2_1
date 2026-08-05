from src.models import PaymentPayload

def process_payment(claimed_order_id: str, expected_total_brl_from_items: float = 0.0) -> PaymentPayload:
    """
    Hoàng: Đọc file order_payments.csv
    Tính tổng payment_total_brl, so sánh với expected_total_brl_from_items.
    Tính difference_brl, xác định cờ reconciled và is_split_payment.
    """
    # TODO: Load order_payments.csv, handle reconciliation logic
    pass
