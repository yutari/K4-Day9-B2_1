from src.models import AggregatedContext, ResolutionOutput

def evaluate_policy(context: AggregatedContext) -> ResolutionOutput:
    """
    Ngân: Nhận data tổng hợp từ các agent khác (context).
    Áp dụng EC_POLICY_V2 để xác định Root Cause, phân hạng Primary/Secondary issues,
    và trả về format ResolutionOutput chuẩn.
    """
    # TODO: Implement EC_POLICY_V2 logic
    # Ưu tiên: canceled -> unavailable -> late_delivery_seller -> late_delivery_logistics -> valid_split_payment
    pass
