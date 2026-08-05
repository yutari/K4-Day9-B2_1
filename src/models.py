from typing import List, Optional, Dict, Any
# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from enum import Enum

# --- Enums cho chuẩn hóa dữ liệu ---

class PrimaryIssue(str, Enum):
    CANCELED_ORDER_PAID = "canceled_order_paid"
    UNAVAILABLE_ORDER_PAID = "unavailable_order_paid"
    LATE_DELIVERY_SELLER = "late_delivery_seller"
    LATE_DELIVERY_LOGISTICS = "late_delivery_logistics"
    VALID_SPLIT_PAYMENT = "valid_split_payment"
    UNSUPPORTED_LATE_CLAIM = "unsupported_late_claim"

class SecondaryIssue(str, Enum):
    MULTI_ITEM_ORDER = "multi_item_order"
    MULTI_SELLER_ORDER = "multi_seller_order"
    SPLIT_PAYMENT = "split_payment"
    REPEAT_CUSTOMER = "repeat_customer"
    MULTIPLE_CATEGORIES = "multiple_categories"

class CaseStatus(str, Enum):
    ACTION_REQUIRED = "action_required"
    NO_ACTION = "no_action"

class PartyType(str, Enum):
    SELLER = "seller"
    LOGISTICS = "logistics"
    CUSTOMER = "customer"
    PLATFORM = "platform"
    UNKNOWN = "unknown"

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
    order_status: str = "" # Thêm order_status để check canceled/unavailable

class PaymentPayload(BaseModel):
    item_total_brl: Optional[float] = None
    freight_total_brl: Optional[float] = None
    expected_total_brl: Optional[float] = None
    payment_total_brl: Optional[float] = None
    difference_brl: Optional[float] = None
    reconciled: Optional[bool] = None
    is_split_payment: bool = False
    payment_types: List[str] = []
    payment_ids: List[str] = [] # Cần thiết cho evidence_ids

class SellerHandoff(BaseModel):
    seller_id: str
    shipping_limit_at: Optional[str] = None
    handoff_variance_hours: Optional[float] = None
    late_handoff: bool = False

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
    party_type: PartyType
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
    affected_entities: Dict[str, Any]
    customer_context: Dict[str, Any]
    product_context: Dict[str, Any]
    delivery_analysis: Dict[str, Any]
    payment_reconciliation: Dict[str, Any]
    root_cause_analysis: Dict[str, Any]
    evidence_ids: List[str] = []
    financial_resolution: Dict[str, Any]
    resolution_actions: List[str] = []
