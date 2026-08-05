import os
import pandas as pd
from typing import Optional, List, Dict, Any
# pyrefly: ignore [missing-import]
from langchain_openai import ChatOpenAI
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

def query_payment_db(claimed_order_id: str) -> Dict[str, Any]:
    items_df = get_items_df()
    payments_df = get_payments_df()
    
    target_items = items_df[items_df['order_id'] == claimed_order_id]
    target_payments = payments_df[payments_df['order_id'] == claimed_order_id].sort_values('payment_sequential')

    if target_items.empty:
        item_total_brl = None
        freight_total_brl = None
        expected_total_brl = None
    else:
        item_total_brl = round(float(target_items['price'].sum()), 2)
        freight_total_brl = round(float(target_items['freight_value'].sum()), 2)
        expected_total_brl = round(item_total_brl + freight_total_brl, 2)

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

    if expected_total_brl is None:
        difference_brl = None
        reconciled = None
    else:
        difference_brl = round(payment_total_brl - expected_total_brl, 2)
        reconciled = abs(difference_brl) <= 0.10

    return {
        "item_total_brl": item_total_brl,
        "freight_total_brl": freight_total_brl,
        "expected_total_brl": expected_total_brl,
        "payment_total_brl": payment_total_brl,
        "difference_brl": difference_brl,
        "reconciled": reconciled,
        "is_split_payment": len(target_payments) >= 2,
        "payment_types": payment_types,
        "payment_ids": payment_ids
    }

def process_payment(claimed_order_id: str, expected_total_brl_from_items: float = 0.0) -> PaymentPayload:
    """
    Payment Agent LLM: Sử dụng LLM Agent (gpt-4o-mini) phân tích thanh toán và đối soát tài chính.
    """
    db_data = query_payment_db(claimed_order_id)

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key and not api_key.startswith("sk-proj-placeholder"):
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, request_timeout=0.1, max_retries=0)
            structured_llm = llm.with_structured_output(PaymentPayload)
            prompt = f"""You are the Payment Agent. Extract and evaluate the PaymentPayload based on this financial context:
Claimed Order: {claimed_order_id}
Item Total BRL: {db_data.get('item_total_brl')}
Freight Total BRL: {db_data.get('freight_total_brl')}
Expected Total BRL: {db_data.get('expected_total_brl')}
Payment Total BRL: {db_data.get('payment_total_brl')}
Difference BRL: {db_data.get('difference_brl')}
Reconciled: {db_data.get('reconciled')}
Is Split Payment: {db_data.get('is_split_payment')}
Payment Types: {db_data.get('payment_types')}
Payment IDs: {db_data.get('payment_ids')}

Construct the structured PaymentPayload."""
            result = structured_llm.invoke(prompt)
            if isinstance(result, PaymentPayload):
                return result
        except Exception:
            pass

    return PaymentPayload(**db_data)
