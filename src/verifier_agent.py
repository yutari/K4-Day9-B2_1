from src.models import ResolutionOutput

def verify_and_save(resolution: ResolutionOutput, case_id: str):
    """
    Đăng: Kiểm tra lại các điều kiện mảng (tối đa 5 orders, 5 items, v.v.).
    Kiểm tra làm tròn số, null handling.
    Sau đó ghi thành JSON chuẩn vào thư mục output/ và append vào logging/trace.jsonl.
    """
    # TODO: Validate schema constraints and round variables
    # TODO: Write to output/{case_id}.json
    pass
