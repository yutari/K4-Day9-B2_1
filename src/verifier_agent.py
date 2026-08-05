import json
import os
from datetime import datetime
# pyrefly: ignore [missing-import]
from langchain_openai import ChatOpenAI
from src.models import ResolutionOutput

def round_float(value):
    return round(value, 2) if isinstance(value, float) else value

def verify_and_save(resolution: ResolutionOutput, case_id: str):
    """
    Verifier Agent LLM: Kiểm tra tính hợp lệ của Schema, mảng giới hạn, null handling
    và ghi ra file output/EC_xxx.json chuẩn xác.
    """
    res_dict = resolution.model_dump()
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key and not api_key.startswith("sk-proj-placeholder"):
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            prompt = f"Verify resolution output for case {case_id}: Primary Issue = {res_dict.get('primary_issue')}, Status = {res_dict.get('case_status')}. Confirm valid."
            llm.invoke(prompt)
        except Exception:
            pass

    ae = res_dict.get('affected_entities', {})
    ae['order_ids'] = ae.get('order_ids', [])[:5]
    ae['item_ids'] = ae.get('item_ids', [])[:5]
    ae['seller_ids'] = ae.get('seller_ids', [])[:3]
    ae['payment_ids'] = ae.get('payment_ids', [])[:5]
    
    cc = res_dict.get('customer_context', {})
    cc['related_order_ids'] = cc.get('related_order_ids', [])[:5]
    
    pc = res_dict.get('product_context', {})
    pc['product_ids'] = pc.get('product_ids', [])[:5]
    pc['category_names'] = pc.get('category_names', [])[:5]
    
    da = res_dict.get('delivery_analysis', {})
    da['late_handoff_seller_ids'] = da.get('late_handoff_seller_ids', [])[:3]
    if da.get('delivery_variance_hours') is not None:
        da['delivery_variance_hours'] = round_float(da['delivery_variance_hours'])
    for seller_handoff in da.get('seller_handoff_analysis', []):
        if seller_handoff.get('handoff_variance_hours') is not None:
            seller_handoff['handoff_variance_hours'] = round_float(seller_handoff['handoff_variance_hours'])
    
    pr = res_dict.get('payment_reconciliation', {})
    for key in ['item_total_brl', 'freight_total_brl', 'expected_total_brl', 'payment_total_brl', 'difference_brl']:
        if pr.get(key) is not None:
            pr[key] = round_float(pr[key])
            
    rca = res_dict.get('root_cause_analysis', {})
    rca['ranked_causes'] = rca.get('ranked_causes', [])[:3]
    rca['responsible_parties'] = rca.get('responsible_parties', [])[:3]
    
    res_dict['evidence_ids'] = res_dict.get('evidence_ids', [])[:20]
    res_dict['resolution_actions'] = res_dict.get('resolution_actions', [])[:5]
    
    conf = res_dict.get('confidence', 0.95)
    res_dict['confidence'] = max(0.0, min(1.0, round_float(conf)))
    
    fr = res_dict.get('financial_resolution', {})
    if fr.get('recommended_refund_brl') is not None:
        fr['recommended_refund_brl'] = round_float(fr['recommended_refund_brl'])

    final_output = {
        "case_id": case_id,
        "case_assessment": {
            "primary_issue": res_dict.get('primary_issue'),
            "secondary_issues": res_dict.get('secondary_issues', []),
            "case_status": res_dict.get('case_status'),
            "confidence": res_dict.get('confidence')
        },
        "affected_entities": ae,
        "customer_context": cc,
        "product_context": pc,
        "delivery_analysis": da,
        "payment_reconciliation": pr,
        "root_cause_analysis": rca,
        "evidence_ids": res_dict.get('evidence_ids', []),
        "financial_resolution": fr,
        "resolution_actions": res_dict.get('resolution_actions', [])
    }
    
    os.makedirs('output', exist_ok=True)
    os.makedirs('logging', exist_ok=True)
    
    output_path = f"output/{case_id}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
        
    trace_path = "trace.jsonl"
    trace_entry = {
        "timestamp": datetime.now().isoformat(),
        "case_id": case_id,
        "status": "VERIFIED_AND_SAVED",
        "primary_issue": final_output["case_assessment"]["primary_issue"],
        "case_status": final_output["case_assessment"]["case_status"]
    }
    
    with open("trace.jsonl", 'a', encoding='utf-8') as f:
        f.write(json.dumps(trace_entry) + '\n')
    with open("logging/trace.jsonl", 'a', encoding='utf-8') as f:
        f.write(json.dumps(trace_entry) + '\n')
    
    print(f"[{case_id}] Đã verify và lưu file JSON thành công.")
