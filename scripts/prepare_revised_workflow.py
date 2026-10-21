"""Prepare the separate Tree, skeleton, default-component and fill stages."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from workflow_v03.core import prepare, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must be a new directory under artifacts")
    try:
        save(prepare(args.run_dir, args.source_dir), output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print("Prepared staged workflow at " + str(output))
    print("Native skeleton, default component page, fill and prototype proofread remain NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
