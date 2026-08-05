from typing import List, Optional
from pydantic import BaseModel

# --- 1. Payload từ các Agent (Domain Context) ---

class CustomerPayload(BaseModel):
    customer_unique_id: Optional[str] = None
    related_order_ids: List[str] = []
    is_repeat_customer: bool = False

class OrderProductPayload(BaseModel):
    item_ids: List[str] = []
    seller_ids: List[str] = []
    product_ids: List[str] = []
    category_names: List[str] = []
    is_multi_item_order: bool = False
    is_multi_seller_order: bool = False
    is_multiple_categories: bool = False

class PaymentPayload(BaseModel):
    expected_total_brl: Optional[float] = None
    payment_total_brl: Optional[float] = None
    difference_brl: Optional[float] = None
    reconciled: Optional[bool] = None
    is_split_payment: bool = False
    payment_types: List[str] = []

class SellerHandoff(BaseModel):
    seller_id: str
    shipping_limit_at: str
    handoff_variance_hours: float
    late_handoff: bool

class DeliveryPayload(BaseModel):
    delivered_at: Optional[str] = None
    estimated_delivery_at: Optional[str] = None
    carrier_handoff_at: Optional[str] = None
    delivery_variance_hours: Optional[float] = None
    seller_handoff_analysis: List[SellerHandoff] = []
    late_handoff_seller_ids: List[str] = []

# --- 2. Dữ liệu tổng hợp (Aggregated Context) truyền cho Policy Agent ---

class AggregatedContext(BaseModel):
    case_id: str
    claimed_order_id: str
    customer_context: CustomerPayload
    order_product_context: OrderProductPayload
    payment_context: PaymentPayload
    delivery_context: DeliveryPayload

# --- 3. Output Schema (Đầu ra cuối cùng) ---

class ResponsibleParty(BaseModel):
    party_type: str
    party_id: str

class RootCause(BaseModel):
    cause_code: str
    rank: int

class ResolutionOutput(BaseModel):
    case_id: str
    primary_issue: str
    secondary_issues: List[str] = []
    case_status: str
    confidence: float
    affected_entities: dict
    customer_context: dict
    product_context: dict
    delivery_analysis: dict
    payment_reconciliation: dict
    root_cause_analysis: dict
    evidence_ids: List[str] = []
    financial_resolution: dict
    resolution_actions: List[str] = []
