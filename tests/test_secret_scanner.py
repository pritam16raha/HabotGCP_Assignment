# Author: Pritam Raha <rahapritam32@gmail.com>
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from detect_secrets import scan_paths  # noqa: E402


class SecretScannerTests(unittest.TestCase):
    def test_environment_lookup_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            test_file = Path(temporary_directory) / "safe.py"
            name = "api" + "_key"
            test_file.write_text(f'{name} = os.environ["SERVICE_CREDENTIAL"]\n', encoding="utf-8")
            self.assertEqual(scan_paths([test_file]), [])

    def test_hardcoded_api_credential_is_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            test_file = Path(temporary_directory) / "unsafe.py"
            name = "api" + "_key"
            value = "embedded-credential-6Vn8sP2q"
            test_file.write_text(f'{name} = "{value}"\n', encoding="utf-8")
            findings = scan_paths([test_file])
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].rule, "Hardcoded secret assignment")
            self.assertNotIn(value, findings[0].evidence)


if __name__ == "__main__":
    unittest.main()
