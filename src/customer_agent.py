from src.models import CustomerPayload

def process_customer(claimed_order_id: str) -> CustomerPayload:
    """
    Hiếu: Đọc file orders.csv và customers.csv
    Lấy customer_id -> customer_unique_id.
    Quét danh sách các đơn khác của cùng customer_unique_id.
    """
    # TODO: Extract customer context and related_order_ids
    pass
