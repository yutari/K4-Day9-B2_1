from collections import OrderedDict
import pandas as pd

from src.models import OrderProductPayload


def _stable_unique(values):
    """Loại bỏ phần tử trùng nhưng giữ nguyên thứ tự xuất hiện."""
    return list(OrderedDict.fromkeys(v for v in values if pd.notna(v)))


def process_order_and_product(claimed_order_id: str) -> OrderProductPayload:
    """
    Đọc orders.csv, order_items.csv, products.csv.

    Với claimed_order_id:
        - Lấy order_status.
        - Lấy toàn bộ items.
        - Xác định seller_ids.
        - Xác định product_ids.
        - Join sang products để lấy category_names.
        - Sinh các cờ:
            + is_multi_item_order
            + is_multi_seller_order
            + is_multiple_categories

    Returns
    -------
    OrderProductPayload
    """

    # ==========================
    # Load CSV
    # ==========================

    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"

    orders_df = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv")

    order_items_df = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")

    products_df = pd.read_csv(DATA_DIR / "olist_products_dataset.csv")
    # ==========================
    # Order
    # ==========================

    order = orders_df[
        orders_df["order_id"] == claimed_order_id
    ]

    if order.empty:
        raise ValueError(f"Order '{claimed_order_id}' not found.")

    order_status = order.iloc[0]["order_status"]

    # ==========================
    # Order Items
    # ==========================

    items = (
        order_items_df[
            order_items_df["order_id"] == claimed_order_id
        ]
        .sort_values("order_item_id")
        .copy()
    )

    if items.empty:
        return OrderProductPayload(
            order_status=order_status
        )

    # ==========================
    # Join Product
    # ==========================

    merged = items.merge(
        products_df[
            [
                "product_id",
                "product_category_name",
            ]
        ],
        how="left",
        on="product_id",
    )

    # ==========================
    # item_ids
    # ==========================

    item_ids = [
        f"{row.order_id}:{int(row.order_item_id)}"
        for _, row in merged.iterrows()
    ]

    # ==========================
    # seller_ids
    # ==========================

    seller_ids = _stable_unique(
        merged["seller_id"].tolist()
    )

    # ==========================
    # product_ids
    # ==========================

    product_ids = _stable_unique(
        merged["product_id"].tolist()
    )

    # ==========================
    # category_names
    # ==========================

    category_names = _stable_unique(
        merged["product_category_name"]
        .fillna("unknown")
        .tolist()
    )

    # ==========================
    # Flags
    # ==========================

    is_multi_item_order = len(item_ids) > 1

    is_multi_seller_order = len(seller_ids) > 1

    is_multiple_categories = len(category_names) > 1

    # ==========================
    # Output
    # ==========================

    return OrderProductPayload(
        item_ids=item_ids[:5],
        seller_ids=seller_ids[:3],
        product_ids=product_ids[:5],
        category_names=category_names[:5],
        is_multi_item_order=is_multi_item_order,
        is_multi_seller_order=is_multi_seller_order,
        is_multiple_categories=is_multiple_categories,
        order_status=order_status,
    )