"""Verifier Agent: validates a finished case JSON before it is written to disk.

Input : the fully assembled case dict (Coordinator's final output, matching
        README.md section 6's schema).
Output: (is_valid: bool, errors: list[str]). Coordinator must not write the
        file to output/ if is_valid is False.

Checked here: evidence ID format, array size limits (README "Giới hạn"),
confidence range, case_status enum, and that money fields are already rounded
to 2 decimals. This does NOT re-derive any business number — it only checks
shapes/limits/formatting of what the other agents already computed.
"""

from __future__ import annotations

import re

EVIDENCE_ID_PATTERN = re.compile(
    r"^(order:[^:]+|item:[^:]+:[^:]+|payment:[^:]+:[^:]+|seller:[^:]+|policy:[A-Z_]+)$"
)

LIMITS = {
    "affected_entities.order_ids": 5,
    "affected_entities.item_ids": 5,
    "affected_entities.seller_ids": 3,
    "affected_entities.payment_ids": 5,
    "customer_context.related_order_ids": 5,
    "product_context.product_ids": 5,
    "product_context.category_names": 5,
    "root_cause_analysis.ranked_causes": 3,
    "root_cause_analysis.responsible_parties": 3,
    "evidence_ids": 20,
    "resolution_actions": 5,
}

VALID_CASE_STATUS = {"action_required", "no_action"}


def _get(d: dict, dotted_path: str):
    node = d
    for part in dotted_path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _is_money_rounded(value) -> bool:
    if value is None:
        return True
    return round(value, 2) == value


def validate(case: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []

    for path, max_len in LIMITS.items():
        value = _get(case, path)
        if value is not None and len(value) > max_len:
            errors.append(f"{path} has {len(value)} items, max is {max_len}")

    confidence = _get(case, "case_assessment.confidence")
    if confidence is None or not (0.0 <= confidence <= 1.0):
        errors.append(f"case_assessment.confidence out of [0,1]: {confidence}")

    case_status = _get(case, "case_assessment.case_status")
    if case_status not in VALID_CASE_STATUS:
        errors.append(f"case_assessment.case_status invalid: {case_status}")

    evidence_ids = case.get("evidence_ids", [])
    for eid in evidence_ids:
        if not EVIDENCE_ID_PATTERN.match(eid):
            errors.append(f"evidence_id has invalid format: {eid}")

    for money_path in (
        "payment_reconciliation.item_total_brl",
        "payment_reconciliation.freight_total_brl",
        "payment_reconciliation.expected_total_brl",
        "payment_reconciliation.payment_total_brl",
        "payment_reconciliation.difference_brl",
        "financial_resolution.recommended_refund_brl",
        "delivery_analysis.delivery_variance_hours",
    ):
        value = _get(case, money_path)
        if not _is_money_rounded(value):
            errors.append(f"{money_path} not rounded to 2 decimals: {value}")

    return (len(errors) == 0, errors)


def check_evidence_ids_exist(evidence_ids: list[str], known_ids: set[str]) -> list[str]:
    """Extra check the Coordinator should run: every evidence id must have been
    built from a real lookup, not guessed. `known_ids` is the set of ids the
    Coordinator actually constructed while gathering data for this case.
    Returns the list of evidence ids that are NOT backed by real data (should
    always be empty; anything here is a hard-gate risk per README section 5).
    """
    return [eid for eid in evidence_ids if eid not in known_ids]
