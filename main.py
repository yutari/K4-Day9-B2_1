"""Run all 50 cases in input/ through the Coordinator and write output/.

Usage: uv run python main.py

Writes one line per case to logging/trace.jsonl (overwritten each run, not
appended — README.md section 8 asks for the latest run's trace only).
"""

import json
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.coordinator import process_case, CaseProcessingError, AGENTS_READY
from src.data_store import DataStore

ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
TRACE_PATH = ROOT / "logging" / "trace.jsonl"


def main() -> None:
    if not AGENTS_READY:
        print(
            "Aborting: customer_agent / order_product_agent / payment_agent / "
            "delivery_agent are not implemented yet (Việc A / Việc B in "
            "TASK_SPLIT.md). Nothing was written to output/ or logging/trace.jsonl."
        )
        return

    store = DataStore()
    input_files = sorted(INPUT_DIR.glob("EC_*.json"))

    ok_count = 0
    fail_count = 0

    with TRACE_PATH.open("w", encoding="utf-8") as trace_file:
        for i, input_path in enumerate(input_files, start=1):
            case_input = json.loads(input_path.read_text(encoding="utf-8"))
            case_id = case_input["case_id"]
            started_at = time.time()

            print(f"[{i}/{len(input_files)}] Processing {case_id}...", end=" ", flush=True)

            try:
                case_output = process_case(case_input, store)
                elapsed = round(time.time() - started_at, 3)
                print(f"OK ({elapsed}s)")

                output_path = OUTPUT_DIR / f"{case_id}.json"
                output_path.write_text(
                    json.dumps(case_output, indent=2, ensure_ascii=False), encoding="utf-8"
                )

                trace_file.write(
                    json.dumps(
                        {
                            "case_id": case_id,
                            "status": "ok",
                            "primary_issue": case_output["case_assessment"]["primary_issue"],
                            "elapsed_seconds": elapsed,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                ok_count += 1

            except CaseProcessingError as exc:
                elapsed = round(time.time() - started_at, 3)
                print(f"ERROR: {exc.reason} ({elapsed}s)")
                trace_file.write(
                    json.dumps(
                        {
                            "case_id": case_id,
                            "status": "error",
                            "reason": exc.reason,
                            "elapsed_seconds": elapsed,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                fail_count += 1

    print(f"done: {ok_count} ok, {fail_count} failed, {len(input_files)} total")


if __name__ == "__main__":
    main()
