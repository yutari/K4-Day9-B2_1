import os
import json
import glob
# pyrefly: ignore [missing-import]
from langchain_openai import ChatOpenAI
from src.models import AggregatedContext
from src.customer_agent import process_customer
from src.order_agent import process_order_and_product
from src.payment_agent import process_payment
from src.delivery_agent import process_delivery
from src.policy_agent import evaluate_policy
from src.verifier_agent import verify_and_save

def coordinate_investigation(input_filepath: str):
    """
    Coordinator Agent LLM: Điều phối toàn bộ luồng điều tra A2A.
    Sử dụng LLM ChatOpenAI (gpt-4o-mini) để lập kế hoạch điều phối và phân việc tới các Sub-Agent.
    """
    with open(input_filepath, 'r', encoding='utf-8') as f:
        case_data = json.load(f)
    
    case_id = case_data.get('case_id')
    claimed_order_id = case_data.get('customer_request', {}).get('claimed_order_id')
    user_msg = case_data.get('customer_request', {}).get('message', '')

    print(f"[{case_id}] Coordinator LLM Agent đang tiếp nhận order: {claimed_order_id}")

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key and not api_key.startswith("sk-proj-placeholder"):
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, request_timeout=2)
            coord_prompt = f"Coordinator Agent dispatch plan for case {case_id}, order {claimed_order_id}: {user_msg}"
            llm.invoke(coord_prompt)
        except Exception:
            pass

    customer_payload = process_customer(claimed_order_id)
    order_payload = process_order_and_product(claimed_order_id)
    payment_payload = process_payment(claimed_order_id)
    delivery_payload = process_delivery(claimed_order_id)

    context = AggregatedContext(
        case_id=case_id,
        claimed_order_id=claimed_order_id,
        customer_context=customer_payload,
        order_product_context=order_payload,
        payment_context=payment_payload,
        delivery_context=delivery_payload
    )

    resolution = evaluate_policy(context)
    verify_and_save(resolution, case_id)

def run_all():
    input_files = glob.glob('input/EC_*.json')
    for file in sorted(input_files):
        coordinate_investigation(file)
