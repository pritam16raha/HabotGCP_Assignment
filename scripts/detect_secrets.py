#!/usr/bin/env python3
# Author: Pritam Raha <rahapritam32@gmail.com>
import argparse
import json
import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

TEXT_SUFFIXES = {
    ".cfg",
    ".env",
    ".hcl",
    ".html",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".tf",
    ".tfvars",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_PARTS = {".git", ".terraform", ".venv", "__pycache__", "build"}
SAFE_VALUE_MARKERS = (
    "${",
    "example",
    "getenv",
    "local-validation-only",
    "not-a-secret",
    "os.environ",
    "redacted",
    "runtime",
)

KNOWN_SECRET_PATTERNS = {
    "Amazon Web Services access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Google Cloud API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "GitHub access token": re.compile(r"\bgh[opusr]_[0-9A-Za-z]{36,255}\b"),
    "Slack access token": re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"),
    "Private key header": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
GENERIC_ASSIGNMENT = re.compile(
    r"(?i)\b(?:api[_-]?key|client[_-]?secret|secret[_-]?key|access[_-]?token|auth[_-]?token)"
    r"\b\s*[:=]\s*['\"]([^'\"]{8,})['\"]"
)
HIGH_ENTROPY_ASSIGNMENT = re.compile(
    r"(?i)\b(?:password|passwd|credential)\b\s*[:=]\s*['\"]([^'\"]{16,})['\"]"
)


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    line: int
    rule: str
    evidence: str


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    frequencies = Counter(value)
    return -sum(
        (count / len(value)) * math.log2(count / len(value)) for count in frequencies.values()
    )


def _redact(value: str) -> str:
    if len(value) <= 8:
        return "[redacted]"
    return f"{value[:4]}…{value[-4:]}"


def _candidate_files(paths: Iterable[Path]) -> Iterable[Path]:
    for supplied_path in paths:
        if supplied_path.is_file():
            yield supplied_path
            continue
        for path in supplied_path.rglob("*"):
            if (
                path.is_file()
                and path.suffix.lower() in TEXT_SUFFIXES
                and not EXCLUDED_PARTS.intersection(path.parts)
            ):
                yield path


def scan_paths(paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(set(_candidate_files(paths))):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, start=1):
            for rule_name, pattern in KNOWN_SECRET_PATTERNS.items():
                match = pattern.search(line)
                if match:
                    findings.append(
                        Finding(str(path), line_number, rule_name, _redact(match.group(0)))
                    )
            generic_match = GENERIC_ASSIGNMENT.search(line)
            if generic_match and not any(
                marker in generic_match.group(1).lower() for marker in SAFE_VALUE_MARKERS
            ):
                findings.append(
                    Finding(
                        str(path),
                        line_number,
                        "Hardcoded secret assignment",
                        _redact(generic_match.group(1)),
                    )
                )
            entropy_match = HIGH_ENTROPY_ASSIGNMENT.search(line)
            if (
                entropy_match
                and not any(
                    marker in entropy_match.group(1).lower() for marker in SAFE_VALUE_MARKERS
                )
                and shannon_entropy(entropy_match.group(1)) >= 3.5
            ):
                findings.append(
                    Finding(
                        str(path),
                        line_number,
                        "High-entropy credential assignment",
                        _redact(entropy_match.group(1)),
                    )
                )
    return findings


def write_report(output_path: Path, findings: list[Finding]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "FAILED" if findings else "PASSED",
        "finding_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
    }
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail closed on likely hardcoded credentials.")
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--output", type=Path, default=Path("build/reports/secret-scan.json"))
    arguments = parser.parse_args()

    repository_root = Path(__file__).resolve().parents[1]
    scan_targets = arguments.paths or [repository_root]
    findings = scan_paths(scan_targets)
    write_report(arguments.output, findings)

    if findings:
        print(f"Secret scan: FAILED — {len(findings)} finding(s); build is quarantined.")
        for finding in findings:
            print(f"{finding.path}:{finding.line}: {finding.rule}: {finding.evidence}")
        return 2
    print("Secret scan: PASSED — no hardcoded credential patterns detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
