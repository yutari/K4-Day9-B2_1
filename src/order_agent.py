from src.models import OrderProductPayload

def process_order_and_product(claimed_order_id: str) -> OrderProductPayload:
    """
    Hoàng: Đọc file order_items.csv, products.csv, sellers.csv
    Tìm tất cả items của claimed_order_id.
    Đếm số lượng để xác định cờ: is_multi_item_order, is_multi_seller_order, is_multiple_categories.
    """
    # TODO: Load CSVs and extract entities
    pass
