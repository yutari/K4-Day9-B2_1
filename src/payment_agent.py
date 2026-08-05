import os
import pandas as pd
from typing import Optional, List
from src.models import PaymentPayload

ORDER_ITEMS_CSV_PATH = "data/olist_order_items_dataset.csv"
ORDER_PAYMENTS_CSV_PATH = "data/olist_order_payments_dataset.csv"

_items_df = None
_payments_df = None

def get_items_df():
    global _items_df
    if _items_df is None:
        _items_df = pd.read_csv(ORDER_ITEMS_CSV_PATH, usecols=['order_id', 'price', 'freight_value'])
    return _items_df

def get_payments_df():
    global _payments_df
    if _payments_df is None:
        _payments_df = pd.read_csv(ORDER_PAYMENTS_CSV_PATH, usecols=['order_id', 'payment_sequential', 'payment_type', 'payment_value'])
    return _payments_df

def process_payment(claimed_order_id: str, expected_total_brl_from_items: float = 0.0) -> PaymentPayload:
    """
    Hoàng: Đọc file order_items.csv và order_payments.csv
    Tính tổng payment_total_brl, so sánh với expected_total_brl.
    Tính difference_brl, xác định cờ reconciled và is_split_payment.
    """
    items_df = get_items_df()
    payments_df = get_payments_df()
    
    target_items = items_df[items_df['order_id'] == claimed_order_id]
    target_payments = payments_df[payments_df['order_id'] == claimed_order_id].sort_values('payment_sequential')

    # Item total & Freight total
    if target_items.empty:
        item_total_brl = None
        freight_total_brl = None
        expected_total_brl = None
    else:
        item_total_brl = round(float(target_items['price'].sum()), 2)
        freight_total_brl = round(float(target_items['freight_value'].sum()), 2)
        expected_total_brl = round(item_total_brl + freight_total_brl, 2)

    # Payments
    if target_payments.empty:
        payment_total_brl = 0.0
        payment_types = []
        payment_ids = []
    else:
        payment_total_brl = round(float(target_payments['payment_value'].sum()), 2)
        payment_types = []
        for p_type in target_payments['payment_type']:
            if pd.notna(p_type) and str(p_type) not in payment_types:
                payment_types.append(str(p_type))
        payment_ids = [f"{claimed_order_id}:{row['payment_sequential']}" for _, row in target_payments.iterrows()]

    # Difference & Reconciled
    if expected_total_brl is None:
        difference_brl = None
        reconciled = None
    else:
        difference_brl = round(payment_total_brl - expected_total_brl, 2)
        reconciled = abs(difference_brl) <= 0.10

    is_split_payment = len(target_payments) >= 2

    return PaymentPayload(
        item_total_brl=item_total_brl,
        freight_total_brl=freight_total_brl,
        expected_total_brl=expected_total_brl,
        payment_total_brl=payment_total_brl,
        difference_brl=difference_brl,
        reconciled=reconciled,
        is_split_payment=is_split_payment,
        payment_types=payment_types,
        payment_ids=payment_ids
    )
