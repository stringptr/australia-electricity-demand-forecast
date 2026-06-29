"""Standalone runner for GX checkpoints.

Usage:
    python run_checkpoint.py bronze_validation
    python run_checkpoint.py all
"""

import sys

from context import get_context
from setup_expectations import CHECKPOINT_GROUPS


def run_checkpoint(name: str) -> dict:
    context = get_context()
    try:
        checkpoint = context.checkpoints.get(name)
    except Exception:
        print(f"Checkpoint '{name}' not found. Run setup_expectations.setup_all() first.")
        sys.exit(1)

    result = checkpoint.run()
    passed = result.success
    stats = result.to_json_dict().get("statistics", {})
    print(f"[{name}] {'PASS' if passed else 'FAIL'}")
    print(f"  Evaluated: {stats.get('evaluated_expectations', 0)}")
    print(f"  Successful: {stats.get('successful_expectations', 0)}")
    print(f"  Failed: {stats.get('unsuccessful_expectations', 0)}")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_checkpoint.py <checkpoint_name|all>")
        sys.exit(1)

    arg = sys.argv[1]
    if arg == "all":
        for cp_name in CHECKPOINT_GROUPS:
            run_checkpoint(cp_name)
    elif arg in CHECKPOINT_GROUPS:
        run_checkpoint(arg)
    else:
        print(f"Unknown checkpoint: {arg}")
        print(f"Available: {list(CHECKPOINT_GROUPS.keys())} | all")
        sys.exit(1)
