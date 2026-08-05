import json
import glob
from src.models import AggregatedContext
from src.customer_agent import process_customer
from src.order_agent import process_order_and_product
from src.payment_agent import process_payment
from src.delivery_agent import process_delivery
from src.policy_agent import evaluate_policy
from src.verifier_agent import verify_and_save

def coordinate_investigation(input_filepath: str):
    """
    Đăng: Đọc file input/EC_xxx.json
    Gọi các hàm Sub-agent (Hoàng, Hiếu) gom thành AggregatedContext.
    Truyền vào Policy Agent (Ngân), rồi đưa qua Verifier (Đăng).
    """
    with open(input_filepath, 'r', encoding='utf-8') as f:
        case_data = json.load(f)
    
    case_id = case_data.get('case_id')
    claimed_order_id = case_data.get('customer_request', {}).get('claimed_order_id')

    print(f"[{case_id}] Bắt đầu điều tra order: {claimed_order_id}")

    # Bước 1: Parallel Context Extraction
    customer_payload = process_customer(claimed_order_id)
    order_payload = process_order_and_product(claimed_order_id)
    
    # Truyền hờ expected_total = 0.0, Hoàng sẽ tính bên order_agent hoặc payment_agent phối hợp
    payment_payload = process_payment(claimed_order_id)
    delivery_payload = process_delivery(claimed_order_id)

    # Bước 2: Aggregation
    context = AggregatedContext(
        case_id=case_id,
        claimed_order_id=claimed_order_id,
        customer_context=customer_payload,
        order_product_context=order_payload,
        payment_context=payment_payload,
        delivery_context=delivery_payload
    )

    # Bước 3: Policy Decision
    resolution = evaluate_policy(context)

    # Bước 4: Validation & Output
    verify_and_save(resolution, case_id)

def run_all():
    input_files = glob.glob('input/EC_*.json')
    for file in sorted(input_files):
        coordinate_investigation(file)
