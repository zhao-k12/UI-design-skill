"""Export one exact native script from a verified V0.2 Adapter byte lock."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapters.byte_lock import script_for_page, verify_execution_script
from validators.ui_ir import load_json


def prepare(run_dir, platform, output_dir, *, page_index=0, page_reference=None):
    run_dir, output_dir = Path(run_dir).resolve(), Path(output_dir).resolve()
    artifacts = (ROOT / "artifacts").resolve()
    if not run_dir.is_relative_to(artifacts) or not output_dir.is_relative_to(artifacts):
        raise ValueError("Run and execution output must stay in artifacts")
    if output_dir == run_dir:
        raise ValueError("Execution output needs its own directory")
    lock_path = run_dir / "adapter-execution-lock.json"
    lock = load_json(lock_path)
    plans = {platform: load_json(run_dir / f"{platform}_preflight.json")["plan"]}
    script = script_for_page(platform, plans[platform], page_index,
                             page_reference=page_reference)
    receipt = verify_execution_script(lock, plans, platform, script, page_index,
                                      page_reference=page_reference)
    receipt.update({"scope": "v02-verified-adapter-execution-intent",
                    "status": "READY_TO_EXECUTE",
                    "lockSha256": sha256(lock_path.read_bytes()).hexdigest(),
                    "fileReference": plans[platform]["fileReference"],
                    "uiIrSha256": plans[platform]["uiIrSha256"],
                    "nativeExecution": "NOT_RUN", "releaseReady": False})
    script_bytes = script.encode("utf-8")
    receipt_bytes = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, data in ((output_dir / "execution.js", script_bytes),
                       (output_dir / "execution-intent.json", receipt_bytes)):
        if path.exists() and path.read_bytes() != data:
            raise ValueError("Existing execution artifact differs; use a new directory")
    (output_dir / "execution.js").write_bytes(script_bytes)
    (output_dir / "execution-intent.json").write_bytes(receipt_bytes)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--platform", choices=("figma", "penpot"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--page-index", type=int, default=0)
    parser.add_argument("--page-reference")
    args = parser.parse_args()
    try:
        receipt = prepare(args.run_dir, args.platform, args.output_dir,
                          page_index=args.page_index,
                          page_reference=args.page_reference)
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
