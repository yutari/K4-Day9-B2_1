import os
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from langchain_core.tools import tool
# pyrefly: ignore [missing-import]
from langchain_openai import ChatOpenAI
# pyrefly: ignore [missing-import]
from langchain.agents import create_tool_calling_agent, AgentExecutor
# pyrefly: ignore [missing-import]
from langchain_core.prompts import ChatPromptTemplate
from src.models import DeliveryPayload, SellerHandoff

load_dotenv()

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

@tool
def get_delivery_timestamps(claimed_order_id: str) -> Dict[str, Any]:
    """
    Look up the delivery timestamps and seller shipping limits for an order.
    Returns delivered_at, estimated_delivery_at, carrier_handoff_at, and seller_limits.
    """
    orders_df = get_orders_df()
    items_df = get_items_df()
    
    target_order = orders_df[orders_df['order_id'] == claimed_order_id]
    if target_order.empty:
        return {"error": "Order not found."}
        
    delivered_at = target_order.iloc[0]['order_delivered_customer_date']
    estimated_delivery_at = target_order.iloc[0]['order_estimated_delivery_date']
    carrier_handoff_at = target_order.iloc[0]['order_delivered_carrier_date']
    
    delivered_at = delivered_at if pd.notna(delivered_at) else None
    estimated_delivery_at = estimated_delivery_at if pd.notna(estimated_delivery_at) else None
    carrier_handoff_at = carrier_handoff_at if pd.notna(carrier_handoff_at) else None
    
    target_items = items_df[items_df['order_id'] == claimed_order_id]
    seller_limits_raw = target_items.groupby('seller_id')['shipping_limit_date'].min().to_dict()
    
    seller_limits = {
        str(k): (str(v) if pd.notna(v) else None)
        for k, v in seller_limits_raw.items()
    }
    
    return {
        "delivered_at": str(delivered_at) if delivered_at else None,
        "estimated_delivery_at": str(estimated_delivery_at) if estimated_delivery_at else None,
        "carrier_handoff_at": str(carrier_handoff_at) if carrier_handoff_at else None,
        "seller_limits": seller_limits
    }

@tool
def calculate_hours_difference(end_date_str: str, start_date_str: str) -> Optional[float]:
    """
    Calculates the difference in hours between end_date_str and start_date_str.
    Format: YYYY-MM-DD HH:MM:SS. Returns difference rounded to 2 decimal places.
    """
    try:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
        return round((end_date - start_date).total_seconds() / 3600.0, 2)
    except Exception:
        return None

def process_delivery(claimed_order_id: str) -> DeliveryPayload:
    """
    Router Agent for Delivery Domain.
    Uses LLM to evaluate delivery times and seller late handoffs.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(DeliveryPayload)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the Delivery Agent in an e-commerce dispute resolution system.
Your task is to calculate delivery variance and determine late handoffs for a given order ID.
You must use the provided tools to fetch timestamps and calculate time differences.

Calculation Rules for final output:
1. delivery_variance_hours = delivered_at - estimated_delivery_at (in hours). Use calculate_hours_difference tool to compute this.
2. For each seller in seller_limits:
   handoff_variance_hours = carrier_handoff_at - shipping_limit_at. Use calculate_hours_difference tool to compute this.
   late_handoff = true IF carrier_handoff_at > shipping_limit_at.
3. late_handoff_seller_ids is a list of seller_ids where late_handoff is true.
4. If any timestamp is null/missing, the corresponding variance should be null/missing.

In your final answer, detail the computed values clearly so they can be parsed into a structured payload.
"""),
        ("human", "Evaluate order ID: {claimed_order_id}"),
        ("placeholder", "{agent_scratchpad}")
    ])
    
    agent = create_tool_calling_agent(llm, [get_delivery_timestamps, calculate_hours_difference], prompt)
    agent_executor = AgentExecutor(agent=agent, tools=[get_delivery_timestamps, calculate_hours_difference], verbose=False)
    
    result = agent_executor.invoke({"claimed_order_id": claimed_order_id})
    
    final_output = structured_llm.invoke(f"Extract the delivery payload from this result: {result['output']}")
    return final_output
