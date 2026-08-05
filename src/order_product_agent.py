"""Order and Product Agent: resolve order items, sellers and categories."""

from src.data_store import DataStore


class OrderProductAgentError(ValueError):
    """Raised when order/product data cannot be resolved."""
    pass


def _unique_keep_order(values, limit):
    """
    Return unique values while keeping original order.
    """
    result = []

    for value in values:
        if value not in result:
            result.append(value)

        if len(result) >= limit:
            break

    return result



def analyze_order_product(
    order_id: str,
    store: DataStore
) -> dict:
    """
    Analyze order items and product information.

    Returns:
    {
        "items": [],
        "seller_ids": [],
        "product_ids": [],
        "category_names": []
    }
    """


    # Find items
    order_items = store.order_items[
        store.order_items["order_id"] == order_id
    ]


    # Empty item is valid case
    if order_items.empty:
        return {
            "items": [],
            "seller_ids": [],
            "product_ids": [],
            "category_names": [],
        }


    # ----------------------
    # 1. Items
    # ----------------------

    items = []

    for _, row in order_items.head(5).iterrows():

        items.append(
            {
                "order_item_id": str(row["order_item_id"]),
                "product_id": row["product_id"],
                "seller_id": row["seller_id"],
                "price": round(float(row["price"]), 2),
                "freight_value": round(float(row["freight_value"]), 2),
                "shipping_limit_date": row["shipping_limit_date"],
            }
        )



    # ----------------------
    # 2. Seller IDs
    # ----------------------

    seller_ids = _unique_keep_order(
        order_items["seller_id"].tolist(),
        3
    )



    # ----------------------
    # 3. Product IDs
    # ----------------------

    product_ids = _unique_keep_order(
        order_items["product_id"].tolist(),
        5
    )



    # ----------------------
    # 4. Category names
    # ----------------------

    category_names = []


    products = store.products[
        store.products["product_id"].isin(product_ids)
    ]


    for _, product in products.iterrows():

        raw_category = product["product_category_name"]


        if not raw_category or raw_category == "nan":
            continue


        # Keep the raw product_category_name straight from products.csv.
        # Translating to English would emit a value that does not exist in the
        # source data, which README section 1 explicitly rules out ("không tự
        # tạo ra sự kiện không tồn tại") and the schema's <category_name>
        # placeholder maps to the products.csv column, not the translation.
        category = raw_category


        if category not in category_names:
            category_names.append(category)


        if len(category_names) >= 5:
            break



    return {
        "items": items,
        "seller_ids": seller_ids,
        "product_ids": product_ids,
        "category_names": category_names,
    }