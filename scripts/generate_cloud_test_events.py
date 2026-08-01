#!/usr/bin/env python3
# Author: Pritam Raha <rahapritam32@gmail.com>
import argparse
import json
import os
import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.utils import timezone  # noqa: E402
from onboarding.pipeline import to_pubsub_event  # noqa: E402
from onboarding.serializers import StudentOnboardingSerializer  # noqa: E402


def build_valid_payload(*, emirate: str, external_id: str) -> dict:
    submitted_at = timezone.now() - timedelta(minutes=1)
    return {
        "schema_version": "1.0",
        "submission_id": str(uuid4()),
        "submitted_at": submitted_at.isoformat(),
        "organisation_id": str(uuid4()),
        "student": {
            "external_id": external_id,
            "first_name": "Test",
            "last_name": "Student",
            "date_of_birth": submitted_at.date()
            .replace(year=submitted_at.year - 10, month=1, day=15)
            .isoformat(),
            "emirate": emirate,
            "school_name": "Synthetic Integration Test School",
            "learning_support_required": True,
            "has_formal_diagnosis": True,
            "diagnosis_codes": ["TEST.1"],
        },
        "guardian": {
            "full_name": "Test Guardian",
            "email": "guardian@example.com",
            "phone_e164": "+971500000001",
            "relationship": "PARENT",
            "consent_to_process": True,
            "consent_timestamp": (submitted_at - timedelta(minutes=1)).isoformat(),
        },
        "support": {
            "areas": ["COMMUNICATION"],
            "requested_hours_per_week": 1,
            "preferred_language": "ENGLISH",
            "wheelchair_access_required": False,
        },
    }


def canonical_event(*, bucket: str, emirate: str, external_id: str) -> dict:
    serializer = StudentOnboardingSerializer(
        data=build_valid_payload(emirate=emirate, external_id=external_id)
    )
    serializer.is_valid(raise_exception=True)
    return to_pubsub_event(
        serializer.validated_data,
        source_object_uri=f"gs://{bucket}/incoming/manual/{external_id.lower()}.json#1",
        ingested_at=datetime.now(UTC),
    )


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate synthetic Pub/Sub messages for live schema and row-policy tests."
    )
    parser.add_argument("--bucket", required=True, help="Deployed raw bucket name without gs://")
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=REPOSITORY_ROOT / "build" / "manual-cloud-events",
    )
    arguments = parser.parse_args()

    dubai = canonical_event(bucket=arguments.bucket, emirate="DUBAI", external_id="TEST-DXB-0001")
    sharjah = canonical_event(
        bucket=arguments.bucket, emirate="SHARJAH", external_id="TEST-SHJ-0001"
    )
    invalid = deepcopy(dubai)
    invalid["submission_id"] = str(uuid4())
    invalid["requested_hours_per_week"] = "wrong-type"

    if len(dubai) != 27 or len(sharjah) != 27 or len(invalid) != 27:
        raise RuntimeError("The generated canonical contract must contain exactly 27 fields.")

    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    write_json(arguments.output_directory / "valid-dubai.json", dubai)
    write_json(arguments.output_directory / "valid-sharjah.json", sharjah)
    write_json(arguments.output_directory / "invalid-wrong-type.json", invalid)

    print(f"Generated three synthetic events in {arguments.output_directory}")
    print("valid-dubai.json: 27 fields, expected publish success")
    print("valid-sharjah.json: 27 fields, expected publish success")
    print("invalid-wrong-type.json: 27 fields, expected INVALID_ARGUMENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
