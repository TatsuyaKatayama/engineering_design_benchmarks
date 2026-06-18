from __future__ import annotations

import argparse
import json
from pathlib import Path

from .solvers import design_from_dict, evaluate_design


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a precision arm design.")
    parser.add_argument("input_json", type=Path)
    args = parser.parse_args()

    with args.input_json.open("r", encoding="utf-8") as f:
        data = json.load(f)

    design = design_from_dict(data)
    result = evaluate_design(design)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

