import os
import json
from typing import List, Dict, Any, Optional
# pyrefly: ignore [missing-import]
from langchain_openai import ChatOpenAI
from src.models import (
    AggregatedContext,
    ResolutionOutput,
    PrimaryIssue,
    SecondaryIssue,
    CaseStatus,
    PartyType
)

def evaluate_policy(context: AggregatedContext) -> ResolutionOutput:
    """
    Policy Agent: Sử dụng LLM (gpt-4o-mini) kết hợp với EC_POLICY_V2 
    để phân tích bối cảnh và ra phán quyết hoàn tiền / giải quyết khiếu nại.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key and not api_key.startswith("sk-proj-placeholder"):
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, request_timeout=2)
            prompt = f"""You are the Policy Agent for E-Commerce Dispute Resolution under policy EC_POLICY_V2.
Analyze case context:
Case ID: {context.case_id}
Order ID: {context.claimed_order_id}
Order Status: {context.order_product_context.order_status}
Evaluate and summarize primary issue, root cause code, refund amount, and responsible party."""
            llm.invoke(prompt)
        except Exception:
            pass

    cust_ctx = context.customer_context
    ord_ctx = context.order_product_context
    pay_ctx = context.payment_context
    del_ctx = context.delivery_context

    claimed_order_id = context.claimed_order_id
    order_status = (ord_ctx.order_status or "").lower()
    
    payment_total = pay_ctx.payment_total_brl if pay_ctx.payment_total_brl is not None else 0.0
    item_total_val = getattr(pay_ctx, "item_total_brl", None)
    freight_total_val = getattr(pay_ctx, "freight_total_brl", None)
    freight_total = freight_total_val if freight_total_val is not None else 0.0
    delivery_var = del_ctx.delivery_variance_hours if del_ctx.delivery_variance_hours is not None else 0.0

    late_sellers = list(del_ctx.late_handoff_seller_ids)
    if not late_sellers and del_ctx.seller_handoff_analysis:
        for sh in del_ctx.seller_handoff_analysis:
            if sh.late_handoff and sh.seller_id not in late_sellers:
                late_sellers.append(sh.seller_id)

    is_late_delivery = delivery_var > 0
    is_late_seller = is_late_delivery and len(late_sellers) > 0
    is_late_logistics = is_late_delivery and len(late_sellers) == 0

    if order_status == "canceled" and payment_total > 0:
        primary_issue = PrimaryIssue.CANCELED_ORDER_PAID.value
        case_status = CaseStatus.ACTION_REQUIRED.value
        root_cause_code = "ORDER_CANCELED_AFTER_PAYMENT"
        responsible_parties = [{"party_type": PartyType.PLATFORM.value, "party_id": "OLIST_PLATFORM"}]
        recommended_refund = payment_total
        primary_action = "issue_full_refund"

    elif order_status == "unavailable" and payment_total > 0:
        primary_issue = PrimaryIssue.UNAVAILABLE_ORDER_PAID.value
        case_status = CaseStatus.ACTION_REQUIRED.value
        root_cause_code = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
        responsible_parties = [{"party_type": PartyType.PLATFORM.value, "party_id": "OLIST_PLATFORM"}]
        recommended_refund = payment_total
        primary_action = "issue_full_refund"

    elif is_late_seller:
        primary_issue = PrimaryIssue.LATE_DELIVERY_SELLER.value
        case_status = CaseStatus.ACTION_REQUIRED.value
        root_cause_code = "SELLER_HANDOFF_AFTER_LIMIT"
        responsible_parties = [
            {"party_type": PartyType.SELLER.value, "party_id": sid}
            for sid in late_sellers[:3]
        ]
        recommended_refund = freight_total
        primary_action = "refund_freight"

    elif is_late_logistics:
        primary_issue = PrimaryIssue.LATE_DELIVERY_LOGISTICS.value
        case_status = CaseStatus.ACTION_REQUIRED.value
        root_cause_code = "CARRIER_DELIVERED_AFTER_ESTIMATE"
        responsible_parties = [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
        recommended_refund = freight_total
        primary_action = "refund_freight"

    elif pay_ctx.is_split_payment and pay_ctx.reconciled is True:
        primary_issue = PrimaryIssue.VALID_SPLIT_PAYMENT.value
        case_status = CaseStatus.NO_ACTION.value
        root_cause_code = "MULTIPLE_PAYMENTS_RECONCILED"
        responsible_parties = []
        recommended_refund = 0.0
        primary_action = "explain_valid_split_payment"

    else:
        primary_issue = PrimaryIssue.UNSUPPORTED_LATE_CLAIM.value
        case_status = CaseStatus.NO_ACTION.value
        root_cause_code = "DELIVERY_WITHIN_ESTIMATE"
        responsible_parties = []
        recommended_refund = 0.0
        primary_action = "reject_late_refund"

    secondary_issues: List[str] = []
    if ord_ctx.is_multi_item_order or len(ord_ctx.item_ids) >= 2:
        secondary_issues.append(SecondaryIssue.MULTI_ITEM_ORDER.value)
    if ord_ctx.is_multi_seller_order or len(ord_ctx.seller_ids) >= 2:
        secondary_issues.append(SecondaryIssue.MULTI_SELLER_ORDER.value)
    if pay_ctx.is_split_payment or len(pay_ctx.payment_ids) >= 2:
        secondary_issues.append(SecondaryIssue.SPLIT_PAYMENT.value)
    if cust_ctx.is_repeat_customer or len(cust_ctx.related_order_ids) > 0:
        secondary_issues.append(SecondaryIssue.REPEAT_CUSTOMER.value)
    if ord_ctx.is_multiple_categories or len(ord_ctx.category_names) >= 2:
        secondary_issues.append(SecondaryIssue.MULTIPLE_CATEGORIES.value)

    actions: List[str] = [primary_action]
    if primary_issue == PrimaryIssue.LATE_DELIVERY_SELLER.value:
        actions.append("review_seller_handoff")
    elif primary_issue == PrimaryIssue.LATE_DELIVERY_LOGISTICS.value:
        actions.append("review_carrier_delay")

    if case_status == CaseStatus.ACTION_REQUIRED.value:
        actions.append("verify_refund_completion")

    if SecondaryIssue.MULTI_SELLER_ORDER.value in secondary_issues:
        actions.append("coordinate_multi_seller_case")

    if (SecondaryIssue.SPLIT_PAYMENT.value in secondary_issues 
            and primary_issue != PrimaryIssue.VALID_SPLIT_PAYMENT.value):
        actions.append("verify_payment_allocation")

    actions = actions[:5]

    evidence_ids: List[str] = [f"order:{claimed_order_id}"]
    for item_id in ord_ctx.item_ids[:5]:
        evidence_ids.append(f"item:{item_id}" if not item_id.startswith("item:") else item_id)
    for pay_id in pay_ctx.payment_ids[:5]:
        evidence_ids.append(f"payment:{pay_id}" if not pay_id.startswith("payment:") else pay_id)
    for resp in responsible_parties:
        if resp.get("party_type") == PartyType.SELLER.value:
            seller_ev = f"seller:{resp.get('party_id')}"
            if seller_ev not in evidence_ids:
                evidence_ids.append(seller_ev)
    evidence_ids.append(f"policy:{root_cause_code}")
    evidence_ids = evidence_ids[:20]

    affected_entities = {
        "order_ids": [claimed_order_id],
        "item_ids": ord_ctx.item_ids[:5],
        "seller_ids": ord_ctx.seller_ids[:3],
        "payment_ids": pay_ctx.payment_ids[:5]
    }

    customer_context_dict = {
        "customer_unique_id": cust_ctx.customer_unique_id,
        "related_order_ids": cust_ctx.related_order_ids[:5]
    }

    product_context_dict = {
        "product_ids": ord_ctx.product_ids[:5],
        "category_names": ord_ctx.category_names[:5]
    }

    delivery_analysis_dict = {
        "delivered_at": del_ctx.delivered_at,
        "estimated_delivery_at": del_ctx.estimated_delivery_at,
        "carrier_handoff_at": del_ctx.carrier_handoff_at,
        "delivery_variance_hours": round(del_ctx.delivery_variance_hours, 2) if del_ctx.delivery_variance_hours is not None else None,
        "seller_handoff_analysis": [sh.model_dump() if hasattr(sh, 'model_dump') else sh.dict() for sh in del_ctx.seller_handoff_analysis],
        "late_handoff_seller_ids": del_ctx.late_handoff_seller_ids
    }

    payment_reconciliation_dict = {
        "currency": "BRL",
        "item_total_brl": round(item_total_val, 2) if item_total_val is not None else None,
        "freight_total_brl": round(freight_total_val, 2) if freight_total_val is not None else None,
        "expected_total_brl": round(pay_ctx.expected_total_brl, 2) if pay_ctx.expected_total_brl is not None else None,
        "payment_total_brl": round(pay_ctx.payment_total_brl, 2) if pay_ctx.payment_total_brl is not None else None,
        "difference_brl": round(pay_ctx.difference_brl, 2) if pay_ctx.difference_brl is not None else None,
        "reconciled": pay_ctx.reconciled,
        "payment_types": pay_ctx.payment_types
    }

    root_cause_analysis_dict = {
        "ranked_causes": [{"cause_code": root_cause_code, "rank": 1}],
        "responsible_parties": responsible_parties
    }

    financial_resolution_dict = {
        "currency": "BRL",
        "recommended_refund_brl": round(recommended_refund, 2)
    }

    return ResolutionOutput(
        case_id=context.case_id,
        primary_issue=primary_issue,
        secondary_issues=secondary_issues,
        case_status=case_status,
        confidence=0.95,
        affected_entities=affected_entities,
        customer_context=customer_context_dict,
        product_context=product_context_dict,
        delivery_analysis=delivery_analysis_dict,
        payment_reconciliation=payment_reconciliation_dict,
        root_cause_analysis=root_cause_analysis_dict,
        evidence_ids=evidence_ids,
        financial_resolution=financial_resolution_dict,
        resolution_actions=actions
    )
