from src.models import DeliveryPayload

def process_delivery(claimed_order_id: str) -> DeliveryPayload:
    """
    Hiếu: Đọc file orders.csv và order_items.csv
    Tính toán chênh lệch thời gian delivery_variance_hours, handoff_variance_hours.
    Xác định late_handoff_seller_ids.
    """
    # TODO: Parse datetimes, calculate variance hours
    pass
