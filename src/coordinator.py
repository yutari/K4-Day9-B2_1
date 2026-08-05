"""Coordinator: chạy một case từ đầu đến cuối qua từng agent và tập hợp
file JSON case cuối cùng (theo schema ở phần 6 của README.md).

Phụ thuộc vào src/customer_agent.py, src/order_product_agent.py,
src/payment_agent.py, src/delivery_agent.py (Việc A / Việc B trong
TASK_SPLIT.md) — các file này chưa tồn tại, vì vậy module này sẽ raise ImportError
cho đến khi chúng được thêm vào. Logic orchestration/assembly bên dưới được viết dựa trên
data contract đã thỏa thuận (phần 0 của TASK_SPLIT.md) nên không cần
thay đổi khi các module thực sự được thêm vào; chỉ cần khối import bên dưới
khớp với tên hàm thực tế là được.
"""

from __future__ import annotations

from .data_store import DataStore
from .policy_agent import decide
from .verifier import validate

try:
    from .customer_agent import analyze_customer
    from .order_product_agent import analyze_order_product
    from .payment_agent import analyze_payment
    from .delivery_agent import analyze_delivery

    AGENTS_READY = True
except ImportError:
    AGENTS_READY = False

MAX_ORDER_IDS = 5
MAX_ITEM_IDS = 5
MAX_SELLER_IDS = 3
MAX_PAYMENT_IDS = 5
MAX_EVIDENCE_IDS = 20


class CaseProcessingError(Exception):
    def __init__(self, case_id: str, reason: str):
        self.case_id = case_id
        self.reason = reason
        super().__init__(f"{case_id}: {reason}")


def _build_evidence_ids(order_id: str, order_product: dict, payment: dict, decision: dict) -> list[str]:
    evidence = [f"order:{order_id}"]
    for item in order_product["items"]:
        evidence.append(f"item:{order_id}:{item['order_item_id']}")
    for pid in payment["payment_ids"]:
        evidence.append(f"payment:{order_id}:{pid}")
    for party in decision["root_cause_analysis"]["responsible_parties"]:
        if party["party_type"] == "seller":
            evidence.append(f"seller:{party['party_id']}")
    evidence.append(f"policy:{decision['_root_cause_code']}")
    # xóa trùng lặp (de-dupe), giữ nguyên thứ tự
    seen = set()
    deduped = []
    for eid in evidence:
        if eid not in seen:
            seen.add(eid)
            deduped.append(eid)
    return deduped[:MAX_EVIDENCE_IDS]


def process_case(case_input: dict, store: DataStore) -> dict:
    """case_input là một dict đã parse từ file input/EC_0xx.json. Trả về dict JSON
    case hoàn chỉnh, sẵn sàng để ghi vào thư mục output/. Gây ra lỗi CaseProcessingError
    khi có bất kỳ thất bại nào (không tìm thấy order, verifier từ chối kết quả, ...) —
    batch runner sẽ chịu trách nhiệm log lại lỗi đó và chuyển sang case tiếp theo
    thay vì làm crash toàn bộ quá trình chạy.
    """
    if not AGENTS_READY:
        raise RuntimeError(
            "customer_agent / order_product_agent / payment_agent / delivery_agent "
            "are not implemented yet (Việc A / Việc B in TASK_SPLIT.md)."
        )

    case_id = case_input["case_id"]
    order_id = case_input["customer_request"]["claimed_order_id"]

    try:
        customer = analyze_customer(order_id, store)
        order_product = analyze_order_product(order_id, store)
        payment = analyze_payment(order_id, order_product["items"], store)
        delivery = analyze_delivery(order_id, order_product["items"], store)
    except Exception as exc:  # noqa: BLE001 - surfaced as a case-level failure
        raise CaseProcessingError(case_id, f"agent failure: {exc}") from exc

    case_facts = {
        "order_id": order_id,
        "order_status": store.get_order_status(order_id),
        "customer": customer,
        "order_product": order_product,
        "payment": payment,
        "delivery": delivery,
    }

    decision = decide(case_facts)

    evidence_ids = _build_evidence_ids(order_id, order_product, payment, decision)

    case = {
        "case_id": case_id,
        "case_assessment": decision["case_assessment"],
        "affected_entities": {
            "order_ids": [order_id][:MAX_ORDER_IDS],
            "item_ids": [f"{order_id}:{i['order_item_id']}" for i in order_product["items"]][:MAX_ITEM_IDS],
            "seller_ids": order_product["seller_ids"][:MAX_SELLER_IDS],
            "payment_ids": [f"{order_id}:{p}" for p in payment["payment_ids"]][:MAX_PAYMENT_IDS],
        },
        "customer_context": {
            "customer_unique_id": customer["customer_unique_id"],
            "related_order_ids": customer["related_order_ids"],
        },
        "product_context": {
            "product_ids": order_product["product_ids"],
            "category_names": order_product["category_names"],
        },
        "delivery_analysis": delivery,
        "payment_reconciliation": {
            "currency": "BRL",
            "item_total_brl": payment["item_total_brl"],
            "freight_total_brl": payment["freight_total_brl"],
            "expected_total_brl": payment["expected_total_brl"],
            "payment_total_brl": payment["payment_total_brl"],
            "difference_brl": payment["difference_brl"],
            "reconciled": payment["reconciled"],
            "payment_types": payment["payment_types"],
        },
        "root_cause_analysis": decision["root_cause_analysis"],
        "evidence_ids": evidence_ids,
        "financial_resolution": decision["financial_resolution"],
        "resolution_actions": decision["resolution_actions"],
    }

    is_valid, errors = validate(case)
    if not is_valid:
        raise CaseProcessingError(case_id, f"verifier rejected output: {errors}")

    return case
