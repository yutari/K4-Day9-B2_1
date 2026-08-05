import os
import pandas as pd
from typing import Dict, Any
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
from src.models import CustomerPayload

load_dotenv()

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

@tool
def get_customer_orders_data(claimed_order_id: str) -> Dict[str, Any]:
    """
    Look up the customer's unique ID and all their related orders.
    Returns the customer_unique_id, a list of related_order_ids (excluding the claimed one), and total_orders_count.
    """
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
    Router Agent for Customer Domain.
    Uses LLM to evaluate customer context based on tool output.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(CustomerPayload)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the Customer Agent in an e-commerce dispute resolution system.
Your task is to extract customer context for a given order ID.
You must use the provided tools to query the database.

Rules for CustomerPayload:
- is_repeat_customer is true if total_orders_count >= 2.
- related_order_ids must be at most 5 orders.

In your final answer, detail the customer_unique_id, related_order_ids, and whether they are a repeat customer.
"""),
        ("human", "Evaluate order ID: {claimed_order_id}"),
        ("placeholder", "{agent_scratchpad}")
    ])
    
    agent = create_tool_calling_agent(llm, [get_customer_orders_data], prompt)
    agent_executor = AgentExecutor(agent=agent, tools=[get_customer_orders_data], verbose=False)
    
    result = agent_executor.invoke({"claimed_order_id": claimed_order_id})
    
    final_output = structured_llm.invoke(f"Extract the customer payload from this result: {result['output']}")
    return final_output
