"""Customer Agent: resolve customer identity and related orders."""

from src.data_store import DataStore


class CustomerAgentError(ValueError):
    """Raised when customer data cannot be resolved."""
    pass


def analyze_customer(order_id: str, store: DataStore) -> dict:
    """
    Analyze customer information from order_id.

    Returns:
    {
        "customer_unique_id": "...",
        "related_order_ids": [...],
        "repeat_customer": True/False
    }
    """

    # 1. Tìm thông tin order để lấy customer_id
    order_rows = store.orders[
        store.orders["order_id"] == order_id
    ]

    if order_rows.empty:
        raise CustomerAgentError(
            f"Order not found: {order_id}"
        )

    customer_id = order_rows.iloc[0]["customer_id"]


    # 2. Tìm customer_unique_id từ bảng customers
    customer_rows = store.customers[
        store.customers["customer_id"] == customer_id
    ]

    if customer_rows.empty:
        raise CustomerAgentError(
            f"Customer not found: {customer_id}"
        )

    customer_unique_id = customer_rows.iloc[0]["customer_unique_id"]


    # 3. Tìm các customer_id khác có cùng unique id
    same_customers = store.customers[
        store.customers["customer_unique_id"] == customer_unique_id
    ]

    customer_ids = same_customers["customer_id"].tolist()


    # Tìm các đơn hàng liên quan (related orders)
    related_orders = store.orders[
        store.orders["customer_id"].isin(customer_ids)
    ]["order_id"].tolist()


    # Loại bỏ đơn hàng hiện tại, giữ đúng thứ tự như trong CSV
    related_order_ids = [
        oid for oid in related_orders
        if oid != order_id
    ][:5]


    # 4. Kiểm tra xem có phải khách hàng cũ quay lại không (repeat customer)
    repeat_customer = len(related_order_ids) > 0


    return {
        "customer_unique_id": customer_unique_id,
        "related_order_ids": related_order_ids,
        "repeat_customer": repeat_customer,
    }