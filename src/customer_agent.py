import os
import pandas as pd
from typing import Dict, Any
# pyrefly: ignore [missing-import]
from langchain_openai import ChatOpenAI
from src.models import CustomerPayload

try:
    # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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

def query_customer_db(claimed_order_id: str) -> Dict[str, Any]:
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
        "customer_unique_id": customer_unique_id,
        "related_order_ids": related_order_ids,
        "total_orders_count": len(all_order_ids)
    }

def process_customer(claimed_order_id: str) -> CustomerPayload:
    """
    Customer Agent LLM: Sử dụng LLM Agent (gpt-4o-mini) phân tích bối cảnh khách hàng.
    """
    db_data = query_customer_db(claimed_order_id)
    if "error" in db_data:
        return CustomerPayload()

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key and not api_key.startswith("sk-proj-placeholder"):
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            structured_llm = llm.with_structured_output(CustomerPayload)
            prompt = f"Customer Agent analysis for order {claimed_order_id}: customer {db_data.get('customer_unique_id')}, count {db_data.get('total_orders_count')}."
            result = structured_llm.invoke(prompt)
            if isinstance(result, CustomerPayload):
                return result
        except Exception:
            pass

    return CustomerPayload(
        customer_unique_id=db_data.get("customer_unique_id"),
        related_order_ids=db_data.get("related_order_ids", [])[:5],
        is_repeat_customer=db_data.get("total_orders_count", 0) >= 2
    )
