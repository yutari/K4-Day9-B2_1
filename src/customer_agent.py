import os
import pandas as pd
from typing import Dict, Any
from src.models import CustomerPayload

ORDERS_CSV_PATH = "data/olist_orders_dataset.csv"
CUSTOMERS_CSV_PATH = "data/olist_customers_dataset.csv"

_orders_df = None
_customers_df = None

def get_orders_df():
    global _orders_df
    if _orders_df is None:
        _orders_df = pd.read_csv(ORDERS_CSV_PATH, usecols=['order_id', 'customer_id'])
    return _orders_df

def get_customers_df():
    global _customers_df
    if _customers_df is None:
        _customers_df = pd.read_csv(CUSTOMERS_CSV_PATH, usecols=['customer_id', 'customer_unique_id'])
    return _customers_df

def get_customer_orders_data(claimed_order_id: str) -> Dict[str, Any]:
    orders_df = get_orders_df()
    customers_df = get_customers_df()
    
    target_order = orders_df[orders_df['order_id'] == claimed_order_id]
    if target_order.empty:
        return {"error": f"Order {claimed_order_id} not found."}
    target_customer_id = target_order.iloc[0]['customer_id']
    
    target_customer = customers_df[customers_df['customer_id'] == target_customer_id]
    if target_customer.empty:
        return {"error": f"Customer ID {target_customer_id} not found."}
    customer_unique_id = target_customer.iloc[0]['customer_unique_id']
    
    related_customers = customers_df[customers_df['customer_unique_id'] == customer_unique_id]
    related_customer_ids = related_customers['customer_id'].tolist()
    
    all_orders = orders_df[orders_df['customer_id'].isin(related_customer_ids)]
    all_order_ids = all_orders['order_id'].tolist()
    
    related_order_ids = [oid for oid in all_order_ids if oid != claimed_order_id][:5]
    
    return {
        "customer_unique_id": str(customer_unique_id),
        "related_order_ids": related_order_ids,
        "total_orders_count": len(all_order_ids)
    }

def process_customer(claimed_order_id: str) -> CustomerPayload:
    """
    Customer Agent: Phân tích danh tính và lịch sử mua hàng của khách.
    """
    data = get_customer_orders_data(claimed_order_id)
    if "error" in data:
        return CustomerPayload()
    
    unique_id = data.get("customer_unique_id")
    related = data.get("related_order_ids", [])[:5]
    total_count = data.get("total_orders_count", 0)
    is_repeat = total_count >= 2
    
    return CustomerPayload(
        customer_unique_id=unique_id,
        related_order_ids=related,
        is_repeat_customer=is_repeat
    )
