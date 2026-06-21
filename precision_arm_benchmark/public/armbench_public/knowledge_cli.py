from __future__ import annotations

import argparse
import json

from .knowledge import get_generation_specs, search_failure_knowledge


def main() -> None:
    parser = argparse.ArgumentParser(description="Query benchmark knowledge fixtures.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Search past failure knowledge.")
    search_parser.add_argument("query")
    search_parser.add_argument("--top-k", type=int, default=5)

    specs_parser = subparsers.add_parser("specs", help="Get public generation specs.")
    specs_parser.add_argument("--generation", choices=["gen1", "gen2", "gen3", "dev"], default=None)

    args = parser.parse_args()
    if args.command == "search":
        result = search_failure_knowledge(args.query, top_k=args.top_k)
    else:
        result = get_generation_specs(args.generation)

    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
