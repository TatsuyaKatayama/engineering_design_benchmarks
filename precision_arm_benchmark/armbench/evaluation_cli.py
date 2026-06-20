from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluation import DEFAULT_DOE_CSV, evaluate_report_files, evaluate_single_report_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate strategy/result report JSON files.")
    parser.add_argument("strategy_or_single_report", type=Path)
    parser.add_argument("result_report", type=Path, nargs="?")
    parser.add_argument("--doe-csv", type=Path, default=DEFAULT_DOE_CSV)
    args = parser.parse_args()

    if args.result_report is None:
        result = evaluate_single_report_file(args.strategy_or_single_report, args.doe_csv)
    else:
        result = evaluate_report_files(args.strategy_or_single_report, args.result_report, args.doe_csv)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
