import os
import pandas as pd
from typing import Dict, Any, List
from src.models import OrderProductPayload

ORDERS_CSV_PATH = "data/olist_orders_dataset.csv"
ORDER_ITEMS_CSV_PATH = "data/olist_order_items_dataset.csv"
PRODUCTS_CSV_PATH = "data/olist_products_dataset.csv"
TRANSLATION_CSV_PATH = "data/product_category_name_translation.csv"

_orders_df = None
_items_df = None
_products_df = None
_translation_df = None

def get_orders_df():
    global _orders_df
    if _orders_df is None:
        _orders_df = pd.read_csv(ORDERS_CSV_PATH, usecols=['order_id', 'order_status'])
    return _orders_df

def get_items_df():
    global _items_df
    if _items_df is None:
        _items_df = pd.read_csv(ORDER_ITEMS_CSV_PATH, usecols=['order_id', 'order_item_id', 'product_id', 'seller_id'])
    return _items_df

def get_products_df():
    global _products_df
    if _products_df is None:
        _products_df = pd.read_csv(PRODUCTS_CSV_PATH, usecols=['product_id', 'product_category_name'])
    return _products_df

def get_translation_df():
    global _translation_df
    if _translation_df is None:
        _translation_df = pd.read_csv(TRANSLATION_CSV_PATH)
    return _translation_df

def process_order_and_product(claimed_order_id: str) -> OrderProductPayload:
    """
    Hoàng: Đọc file order_items.csv, products.csv, sellers.csv, orders.csv
    Tìm tất cả items của claimed_order_id.
    Đếm số lượng để xác định cờ: is_multi_item_order, is_multi_seller_order, is_multiple_categories.
    """
    orders_df = get_orders_df()
    items_df = get_items_df()
    products_df = get_products_df()
    translation_df = get_translation_df()
    
    trans_map = dict(zip(translation_df['product_category_name'], translation_df['product_category_name_english']))

    # Order Status
    target_order = orders_df[orders_df['order_id'] == claimed_order_id]
    order_status = ""
    if not target_order.empty:
        order_status = str(target_order.iloc[0]['order_status']) if pd.notna(target_order.iloc[0]['order_status']) else ""

    # Items
    target_items = items_df[items_df['order_id'] == claimed_order_id].sort_values('order_item_id')

    if target_items.empty:
        return OrderProductPayload(
            item_ids=[],
            seller_ids=[],
            product_ids=[],
            category_names=[],
            is_multi_item_order=False,
            is_multi_seller_order=False,
            is_multiple_categories=False,
            order_status=order_status
        )

    item_ids = [f"{claimed_order_id}:{row['order_item_id']}" for _, row in target_items.iterrows()]
    
    # Seller IDs (unique, stable order)
    seller_ids = []
    for s_id in target_items['seller_id']:
        if pd.notna(s_id) and str(s_id) not in seller_ids:
            seller_ids.append(str(s_id))
            
    # Product IDs & Categories
    product_ids = []
    category_names = []
    
    merged_items = target_items.merge(products_df, on='product_id', how='left')
    
    for _, row in merged_items.iterrows():
        p_id = str(row['product_id']) if pd.notna(row['product_id']) else None
        if p_id and p_id not in product_ids:
            product_ids.append(p_id)
            
        raw_cat = row['product_category_name'] if pd.notna(row['product_category_name']) else None
        if raw_cat:
            cat_name = trans_map.get(raw_cat, raw_cat)
            if cat_name not in category_names:
                category_names.append(cat_name)

    is_multi_item = len(target_items) >= 2
    is_multi_seller = len(seller_ids) >= 2
    is_multiple_categories = len(category_names) >= 2

    return OrderProductPayload(
        item_ids=item_ids,
        seller_ids=seller_ids,
        product_ids=product_ids,
        category_names=category_names,
        is_multi_item_order=is_multi_item,
        is_multi_seller_order=is_multi_seller,
        is_multiple_categories=is_multiple_categories,
        order_status=order_status
    )
