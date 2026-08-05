import os
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime
from src.models import DeliveryPayload, SellerHandoff

ORDERS_CSV_PATH = "data/olist_orders_dataset.csv"
ORDER_ITEMS_CSV_PATH = "data/olist_order_items_dataset.csv"

_orders_df = None
_items_df = None

def get_orders_df():
    global _orders_df
    if _orders_df is None:
        _orders_df = pd.read_csv(ORDERS_CSV_PATH)
    return _orders_df

def get_items_df():
    global _items_df
    if _items_df is None:
        _items_df = pd.read_csv(ORDER_ITEMS_CSV_PATH)
    return _items_df

def calculate_hours_difference(end_date_str: Optional[str], start_date_str: Optional[str]) -> Optional[float]:
    if not end_date_str or not start_date_str:
        return None
    try:
        end_date = datetime.strptime(str(end_date_str), "%Y-%m-%d %H:%M:%S")
        start_date = datetime.strptime(str(start_date_str), "%Y-%m-%d %H:%M:%S")
        return round((end_date - start_date).total_seconds() / 3600.0, 2)
    except Exception:
        return None

def process_delivery(claimed_order_id: str) -> DeliveryPayload:
    """
    Delivery Agent: Phân tích mốc thời gian giao hàng và trễ hạn seller.
    """
    orders_df = get_orders_df()
    items_df = get_items_df()
    
    target_order = orders_df[orders_df['order_id'] == claimed_order_id]
    if target_order.empty:
        return DeliveryPayload()
        
    delivered_at = target_order.iloc[0]['order_delivered_customer_date']
    estimated_delivery_at = target_order.iloc[0]['order_estimated_delivery_date']
    carrier_handoff_at = target_order.iloc[0]['order_delivered_carrier_date']
    
    delivered_at_str = str(delivered_at) if pd.notna(delivered_at) else None
    estimated_delivery_at_str = str(estimated_delivery_at) if pd.notna(estimated_delivery_at) else None
    carrier_handoff_at_str = str(carrier_handoff_at) if pd.notna(carrier_handoff_at) else None
    
    delivery_variance_hours = calculate_hours_difference(delivered_at_str, estimated_delivery_at_str)
    
    target_items = items_df[items_df['order_id'] == claimed_order_id]
    seller_limits_raw = target_items.groupby('seller_id')['shipping_limit_date'].min().to_dict()
    
    seller_handoff_analysis: List[SellerHandoff] = []
    late_handoff_seller_ids: List[str] = []
    
    for seller_id_raw, limit_raw in seller_limits_raw.items():
        s_id = str(seller_id_raw)
        limit_str = str(limit_raw) if pd.notna(limit_raw) else None
        
        handoff_var = calculate_hours_difference(carrier_handoff_at_str, limit_str)
        is_late = (handoff_var is not None) and (handoff_var > 0)
        
        if is_late:
            late_handoff_seller_ids.append(s_id)
            
        seller_handoff_analysis.append(
            SellerHandoff(
                seller_id=s_id,
                shipping_limit_at=limit_str,
                handoff_variance_hours=handoff_var if handoff_var is not None else 0.0,
                late_handoff=is_late
            )
        )
        
    return DeliveryPayload(
        delivered_at=delivered_at_str,
        estimated_delivery_at=estimated_delivery_at_str,
        carrier_handoff_at=carrier_handoff_at_str,
        delivery_variance_hours=delivery_variance_hours,
        seller_handoff_analysis=seller_handoff_analysis,
        late_handoff_seller_ids=late_handoff_seller_ids
    )
