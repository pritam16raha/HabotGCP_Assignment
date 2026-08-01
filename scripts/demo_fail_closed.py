#!/usr/bin/env python3
# Author: Pritam Raha <rahapritam32@gmail.com>
import tempfile
from pathlib import Path

from detect_secrets import scan_paths


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="habot-fail-closed-") as temporary_directory:
        insecure_file = Path(temporary_directory) / "insecure_commit.py"
        setting_name = "api" + "_key"
        unsafe_value = "candidate-embedded-credential-7Q9w2L4p"
        insecure_file.write_text(
            f'{setting_name} = "{unsafe_value}"\n',
            encoding="utf-8",
        )
        findings = scan_paths([insecure_file])

    if not findings:
        print("Fail-closed demonstration: FAILED — insecure input was not blocked.")
        return 1
    print(
        "Fail-closed demonstration: PASSED — a synthetic hardcoded credential produced "
        f"{len(findings)} finding and a non-deployable result."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
