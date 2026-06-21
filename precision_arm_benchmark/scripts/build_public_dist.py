from __future__ import annotations

import argparse
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_ROOT = PROJECT_ROOT / "public"
DEFAULT_DIST_ROOT = PROJECT_ROOT / "dist" / "precision_arm_benchmark_public"

FORBIDDEN_NAMES = {
    "armbench_eval",
    "evaluation.py",
    "evaluation_cli.py",
    "evaluation_guide.md",
    "hidden_oracle.json",
    "doe_sorted_regulation.csv",
    "doe_summary.md",
    "generate_doe_report.py",
}

FORBIDDEN_TEXT = (
    "hidden_oracle",
    "doe_sorted_regulation",
    "doe_summary",
    "evaluation_cli",
    "armbench_eval",
    "現在の評価用DOE基準解",
    "最安PASS",
)


def build_public_dist(dist_root: Path = DEFAULT_DIST_ROOT) -> Path:
    if not PUBLIC_ROOT.exists():
        raise FileNotFoundError(f"public source directory not found: {PUBLIC_ROOT}")

    if dist_root.exists():
        shutil.rmtree(dist_root)
    shutil.copytree(PUBLIC_ROOT, dist_root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    check_public_dist(dist_root)
    return dist_root


def check_public_dist(dist_root: Path = DEFAULT_DIST_ROOT) -> None:
    if not dist_root.exists():
        raise FileNotFoundError(f"public dist directory not found: {dist_root}")

    violations: list[str] = []
    for path in dist_root.rglob("*"):
        if any(part in FORBIDDEN_NAMES for part in path.parts):
            violations.append(str(path.relative_to(dist_root)))
            continue
        if path.is_file() and path.suffix.lower() in {".py", ".md", ".json", ".jsonl", ".csv", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(marker in text for marker in FORBIDDEN_TEXT):
                violations.append(str(path.relative_to(dist_root)))

    if violations:
        joined = "\n".join(f"- {item}" for item in sorted(set(violations)))
        raise RuntimeError(f"forbidden private benchmark information found in public dist:\n{joined}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the public Precision Arm Benchmark distribution.")
    parser.add_argument("--dist-root", type=Path, default=DEFAULT_DIST_ROOT)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    if args.check_only:
        check_public_dist(args.dist_root)
        print(f"public dist check passed: {args.dist_root}")
        return

    dist_root = build_public_dist(args.dist_root)
    print(f"public dist built: {dist_root}")


if __name__ == "__main__":
    main()
