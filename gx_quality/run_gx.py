"""Run all GX validations and build Data Docs."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from context import get_context
from setup_expectations import setup_all, CHECKPOINT_GROUPS


def main():
    print("Setting up suites & checkpoints...")
    setup_all()

    print("Running checkpoints...")
    context = get_context()
    for name in CHECKPOINT_GROUPS:
        r = context.checkpoints.get(name).run()
        s = r.to_json_dict().get("statistics", {})
        p = s.get("successful_expectations", 0)
        t = s.get("evaluated_expectations", 0)
        status = "PASS" if r.success else "FAIL"
        print(f"  [{name}] {status} ({p}/{t})")

    print("Building Data Docs...")
    context.build_data_docs()
    print("Done! Data Docs at uncommitted/data_docs/")


if __name__ == "__main__":
    main()
