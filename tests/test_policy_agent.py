import pytest
from src.models import (
    AggregatedContext,
    CustomerPayload,
    OrderProductPayload,
    PaymentPayload,
    DeliveryPayload,
    SellerHandoff,
    PrimaryIssue,
    SecondaryIssue,
    CaseStatus,
    PartyType
)
from src.policy_agent import evaluate_policy

def create_base_context(
    case_id: str = "EC_TEST_001",
    claimed_order_id: str = "order_test_123",
    order_status: str = "delivered",
    payment_total: float = 100.0,
    item_total: float = 80.0,
    freight_total: float = 20.0,
    delivery_variance_hours: float = 0.0,
    late_sellers: list = None,
    seller_handoff_analysis: list = None,
    is_split_payment: bool = False,
    reconciled: bool = True,
    item_ids: list = None,
    seller_ids: list = None,
    product_ids: list = None,
    category_names: list = None,
    payment_ids: list = None,
    related_order_ids: list = None,
    is_repeat_customer: bool = False
) -> AggregatedContext:
    if late_sellers is None:
        late_sellers = []
    if seller_handoff_analysis is None:
        seller_handoff_analysis = []
    if item_ids is None:
        item_ids = ["1"]
    if seller_ids is None:
        seller_ids = ["seller_1"]
    if product_ids is None:
        product_ids = ["prod_1"]
    if category_names is None:
        category_names = ["cat_1"]
    if payment_ids is None:
        payment_ids = ["1"]
    if related_order_ids is None:
        related_order_ids = []

    customer_ctx = CustomerPayload(
        customer_unique_id="cust_unique_123",
        related_order_ids=related_order_ids,
        is_repeat_customer=is_repeat_customer
    )

    order_product_ctx = OrderProductPayload(
        item_ids=item_ids,
        seller_ids=seller_ids,
        product_ids=product_ids,
        category_names=category_names,
        is_multi_item_order=len(item_ids) >= 2,
        is_multi_seller_order=len(seller_ids) >= 2,
        is_multiple_categories=len(category_names) >= 2,
        order_status=order_status
    )

    payment_ctx = PaymentPayload(
        item_total_brl=item_total,
        freight_total_brl=freight_total,
        expected_total_brl=item_total + freight_total if item_total is not None and freight_total is not None else None,
        payment_total_brl=payment_total,
        difference_brl=0.0,
        reconciled=reconciled,
        is_split_payment=is_split_payment,
        payment_types=["credit_card"],
        payment_ids=payment_ids
    )

    delivery_ctx = DeliveryPayload(
        delivered_at="2018-03-31 15:00:00",
        estimated_delivery_at="2018-03-28 00:00:00",
        carrier_handoff_at="2018-03-15 10:00:00",
        delivery_variance_hours=delivery_variance_hours,
        seller_handoff_analysis=seller_handoff_analysis,
        late_handoff_seller_ids=late_sellers
    )

    return AggregatedContext(
        case_id=case_id,
        claimed_order_id=claimed_order_id,
        customer_context=customer_ctx,
        order_product_context=order_product_ctx,
        payment_context=payment_ctx,
        delivery_context=delivery_ctx
    )


# --- NHÓM 1: 6 PRIMARY ISSUES ---

def test_canceled_order_paid():
    """Test Case 1: Order canceled and paid -> canceled_order_paid, full refund."""
    ctx = create_base_context(
        order_status="canceled",
        payment_total=150.50
    )
    res = evaluate_policy(ctx)

    assert res.primary_issue == PrimaryIssue.CANCELED_ORDER_PAID.value
    assert res.case_status == CaseStatus.ACTION_REQUIRED.value
    assert res.financial_resolution["recommended_refund_brl"] == 150.50
    assert res.root_cause_analysis["ranked_causes"][0]["cause_code"] == "ORDER_CANCELED_AFTER_PAYMENT"
    assert res.root_cause_analysis["responsible_parties"][0]["party_type"] == PartyType.PLATFORM.value
    assert res.resolution_actions[0] == "issue_full_refund"


def test_unavailable_order_paid():
    """Test Case 2: Order unavailable and paid -> unavailable_order_paid, full refund."""
    ctx = create_base_context(
        order_status="unavailable",
        payment_total=200.00
    )
    res = evaluate_policy(ctx)

    assert res.primary_issue == PrimaryIssue.UNAVAILABLE_ORDER_PAID.value
    assert res.case_status == CaseStatus.ACTION_REQUIRED.value
    assert res.financial_resolution["recommended_refund_brl"] == 200.00
    assert res.root_cause_analysis["ranked_causes"][0]["cause_code"] == "ORDER_UNAVAILABLE_AFTER_PAYMENT"
    assert res.root_cause_analysis["responsible_parties"][0]["party_type"] == PartyType.PLATFORM.value
    assert res.resolution_actions[0] == "issue_full_refund"


def test_late_delivery_seller():
    """Test Case 3: Delivery late and seller handoff late -> late_delivery_seller, freight refund."""
    seller_analysis = [
        SellerHandoff(seller_id="seller_A", shipping_limit_at="2018-03-14 00:00:00", handoff_variance_hours=12.5, late_handoff=True)
    ]
    ctx = create_base_context(
        order_status="delivered",
        delivery_variance_hours=24.0,
        late_sellers=["seller_A"],
        seller_handoff_analysis=seller_analysis,
        freight_total=25.0
    )
    res = evaluate_policy(ctx)

    assert res.primary_issue == PrimaryIssue.LATE_DELIVERY_SELLER.value
    assert res.case_status == CaseStatus.ACTION_REQUIRED.value
    assert res.financial_resolution["recommended_refund_brl"] == 25.0
    assert res.root_cause_analysis["ranked_causes"][0]["cause_code"] == "SELLER_HANDOFF_AFTER_LIMIT"
    assert res.root_cause_analysis["responsible_parties"][0]["party_type"] == PartyType.SELLER.value
    assert res.root_cause_analysis["responsible_parties"][0]["party_id"] == "seller_A"
    assert res.resolution_actions[0] == "refund_freight"
    assert "review_seller_handoff" in res.resolution_actions


def test_late_delivery_logistics():
    """Test Case 4: Delivery late but no seller handoff late -> late_delivery_logistics, freight refund."""
    ctx = create_base_context(
        order_status="delivered",
        delivery_variance_hours=48.0,
        late_sellers=[],
        freight_total=18.75
    )
    res = evaluate_policy(ctx)

    assert res.primary_issue == PrimaryIssue.LATE_DELIVERY_LOGISTICS.value
    assert res.case_status == CaseStatus.ACTION_REQUIRED.value
    assert res.financial_resolution["recommended_refund_brl"] == 18.75
    assert res.root_cause_analysis["ranked_causes"][0]["cause_code"] == "CARRIER_DELIVERED_AFTER_ESTIMATE"
    assert res.root_cause_analysis["responsible_parties"][0]["party_type"] == "logistics_provider"
    assert res.resolution_actions[0] == "refund_freight"
    assert "review_carrier_delay" in res.resolution_actions


def test_valid_split_payment():
    """Test Case 5: Valid split payment, delivered on time -> valid_split_payment, refund 0."""
    ctx = create_base_context(
        order_status="delivered",
        delivery_variance_hours=-10.0,
        is_split_payment=True,
        reconciled=True,
        payment_ids=["1", "2"]
    )
    res = evaluate_policy(ctx)

    assert res.primary_issue == PrimaryIssue.VALID_SPLIT_PAYMENT.value
    assert res.case_status == CaseStatus.NO_ACTION.value
    assert res.financial_resolution["recommended_refund_brl"] == 0.0
    assert res.root_cause_analysis["ranked_causes"][0]["cause_code"] == "MULTIPLE_PAYMENTS_RECONCILED"
    assert res.resolution_actions[0] == "explain_valid_split_payment"


def test_unsupported_late_claim():
    """Test Case 6: Standard order delivered on time -> unsupported_late_claim, refund 0."""
    ctx = create_base_context(
        order_status="delivered",
        delivery_variance_hours=0.0
    )
    res = evaluate_policy(ctx)

    assert res.primary_issue == PrimaryIssue.UNSUPPORTED_LATE_CLAIM.value
    assert res.case_status == CaseStatus.NO_ACTION.value
    assert res.financial_resolution["recommended_refund_brl"] == 0.0
    assert res.root_cause_analysis["ranked_causes"][0]["cause_code"] == "DELIVERY_WITHIN_ESTIMATE"
    assert res.resolution_actions[0] == "reject_late_refund"


# --- NHÓM 2: PRIORITY OVERRIDES ---

def test_canceled_overrides_late_delivery():
    """Test Case 7: Order canceled AND late delivery -> canceled_order_paid takes priority."""
    seller_analysis = [
        SellerHandoff(seller_id="seller_A", shipping_limit_at="2018-03-14 00:00:00", handoff_variance_hours=12.5, late_handoff=True)
    ]
    ctx = create_base_context(
        order_status="canceled",
        payment_total=100.0,
        delivery_variance_hours=50.0,
        late_sellers=["seller_A"],
        seller_handoff_analysis=seller_analysis
    )
    res = evaluate_policy(ctx)

    assert res.primary_issue == PrimaryIssue.CANCELED_ORDER_PAID.value
    assert res.financial_resolution["recommended_refund_brl"] == 100.0


def test_seller_late_overrides_logistics_late():
    """Test Case 8: Both seller late and logistics late -> late_delivery_seller takes priority over logistics."""
    seller_analysis = [
        SellerHandoff(seller_id="seller_X", shipping_limit_at="2018-03-14 00:00:00", handoff_variance_hours=5.0, late_handoff=True)
    ]
    ctx = create_base_context(
        order_status="delivered",
        delivery_variance_hours=30.0,
        late_sellers=["seller_X"],
        seller_handoff_analysis=seller_analysis
    )
    res = evaluate_policy(ctx)

    assert res.primary_issue == PrimaryIssue.LATE_DELIVERY_SELLER.value


# --- NHÓM 3: SECONDARY ISSUES ORDERING ---

def test_secondary_issues_ordering():
    """Test Case 9: All 5 secondary issue conditions met -> exact order specified in EC_POLICY_V2."""
    ctx = create_base_context(
        item_ids=["1", "2"],
        seller_ids=["s1", "s2"],
        payment_ids=["p1", "p2"],
        is_split_payment=True,
        related_order_ids=["related_1"],
        is_repeat_customer=True,
        category_names=["cat1", "cat2"]
    )
    res = evaluate_policy(ctx)

    expected_order = [
        SecondaryIssue.MULTI_ITEM_ORDER.value,
        SecondaryIssue.MULTI_SELLER_ORDER.value,
        SecondaryIssue.SPLIT_PAYMENT.value,
        SecondaryIssue.REPEAT_CUSTOMER.value,
        SecondaryIssue.MULTIPLE_CATEGORIES.value
    ]
    assert res.secondary_issues == expected_order


def test_secondary_issues_partial():
    """Test Case 10: Partial secondary issues -> strict order maintained for present flags."""
    ctx = create_base_context(
        item_ids=["1"],
        seller_ids=["s1"],
        payment_ids=["p1", "p2"],
        is_split_payment=True,
        related_order_ids=["related_1"],
        is_repeat_customer=True,
        category_names=["cat1"]
    )
    res = evaluate_policy(ctx)

    expected = [
        SecondaryIssue.SPLIT_PAYMENT.value,
        SecondaryIssue.REPEAT_CUSTOMER.value
    ]
    assert res.secondary_issues == expected


# --- NHÓM 4: RESOLUTION ACTIONS & EVIDENCE IDS ---

def test_resolution_actions_building():
    """Test Case 11: Resolution actions built correctly including secondary issue triggers."""
    seller_analysis = [
        SellerHandoff(seller_id="s1", late_handoff=True)
    ]
    ctx = create_base_context(
        order_status="delivered",
        delivery_variance_hours=10.0,
        late_sellers=["s1"],
        seller_handoff_analysis=seller_analysis,
        item_ids=["1", "2"],
        seller_ids=["s1", "s2"],
        payment_ids=["p1", "p2"],
        is_split_payment=True
    )
    res = evaluate_policy(ctx)

    assert res.resolution_actions[0] == "refund_freight"
    assert "review_seller_handoff" in res.resolution_actions
    assert "verify_refund_completion" in res.resolution_actions
    assert "coordinate_multi_seller_case" in res.resolution_actions
    assert "verify_payment_allocation" in res.resolution_actions
    assert len(res.resolution_actions) <= 5


def test_valid_split_payment_action_exclusion():
    """Test Case 12: valid_split_payment primary issue MUST NOT include verify_payment_allocation."""
    ctx = create_base_context(
        order_status="delivered",
        delivery_variance_hours=-5.0,
        is_split_payment=True,
        reconciled=True,
        payment_ids=["p1", "p2"]
    )
    res = evaluate_policy(ctx)

    assert res.primary_issue == PrimaryIssue.VALID_SPLIT_PAYMENT.value
    assert "verify_payment_allocation" not in res.resolution_actions


def test_evidence_ids_format():
    """Test Case 13: Evidence IDs formatted properly with correct prefixes."""
    seller_analysis = [
        SellerHandoff(seller_id="seller_99", late_handoff=True)
    ]
    ctx = create_base_context(
        claimed_order_id="ord_abc",
        order_status="delivered",
        delivery_variance_hours=15.0,
        late_sellers=["seller_99"],
        seller_handoff_analysis=seller_analysis,
        item_ids=["item_1"],
        payment_ids=["pay_1"]
    )
    res = evaluate_policy(ctx)

    assert "order:ord_abc" in res.evidence_ids
    assert any(ev.startswith("item:ord_abc:") for ev in res.evidence_ids)
    assert any(ev.startswith("payment:ord_abc:") for ev in res.evidence_ids)
    assert "seller:seller_99" in res.evidence_ids
    assert "policy:SELLER_HANDOFF_AFTER_LIMIT" in res.evidence_ids


# --- NHÓM 5: LIMITS, FORMATTING & NULL SAFETY ---

def test_array_truncation_limits():
    """Test Case 14: Ensure output arrays are truncated within spec limits."""
    ctx = create_base_context(
        item_ids=[f"item_{i}" for i in range(10)],
        seller_ids=[f"seller_{i}" for i in range(10)],
        product_ids=[f"prod_{i}" for i in range(10)],
        category_names=[f"cat_{i}" for i in range(10)],
        payment_ids=[f"pay_{i}" for i in range(10)],
        related_order_ids=[f"rel_{i}" for i in range(10)]
    )
    res = evaluate_policy(ctx)

    assert len(res.affected_entities["item_ids"]) <= 5
    assert len(res.affected_entities["seller_ids"]) <= 3
    assert len(res.affected_entities["payment_ids"]) <= 5
    assert len(res.product_context["product_ids"]) <= 5
    assert len(res.product_context["category_names"]) <= 5
    assert len(res.customer_context["related_order_ids"]) <= 5
    assert len(res.evidence_ids) <= 20
    assert len(res.resolution_actions) <= 5


def test_null_handling_and_rounding():
    """Test Case 15: Handle None fields gracefully and round floats to 2 decimal places."""
    ctx = create_base_context(
        delivery_variance_hours=12.34567,
        item_total=80.1234,
        freight_total=19.8765,
        payment_total=100.0000
    )
    res = evaluate_policy(ctx)

    assert res.delivery_analysis["delivery_variance_hours"] == 12.35
    assert res.payment_reconciliation["item_total_brl"] == 80.12
    assert res.payment_reconciliation["freight_total_brl"] == 19.88
    assert res.financial_resolution["recommended_refund_brl"] == 19.88
