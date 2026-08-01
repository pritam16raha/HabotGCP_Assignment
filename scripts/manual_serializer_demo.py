#!/usr/bin/env python3
# Author: Pritam Raha <rahapritam32@gmail.com>
import json
import os
import sys
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.utils import timezone  # noqa: E402
from onboarding import dcyn  # noqa: E402
from onboarding.serializers import StudentOnboardingSerializer  # noqa: E402


def build_valid_payload() -> dict:
    submitted_at = timezone.now() - timedelta(minutes=1)
    return {
        "schema_version": "1.0",
        "submission_id": str(uuid4()),
        "submitted_at": submitted_at.isoformat(),
        "organisation_id": str(uuid4()),
        "student": {
            "external_id": "STU-DXB-2048",
            "first_name": "Aarav",
            "last_name": "Nair",
            "date_of_birth": submitted_at.date()
            .replace(year=submitted_at.year - 10, month=1, day=15)
            .isoformat(),
            "emirate": "DUBAI",
            "school_name": "Dubai Inclusive Learning School",
            "learning_support_required": True,
            "has_formal_diagnosis": True,
            "diagnosis_codes": ["ASD.1"],
        },
        "guardian": {
            "full_name": "Meera Nair",
            "email": "meera.nair@example.com",
            "phone_e164": "+971501234567",
            "relationship": "PARENT",
            "consent_to_process": True,
            "consent_timestamp": (submitted_at - timedelta(minutes=1)).isoformat(),
        },
        "support": {
            "areas": ["COMMUNICATION", "SOCIAL_INTERACTION"],
            "requested_hours_per_week": 12,
            "preferred_language": "ENGLISH",
            "wheelchair_access_required": False,
        },
    }


def main() -> int:
    valid_serializer = StudentOnboardingSerializer(data=build_valid_payload())
    if not valid_serializer.is_valid():
        print("VALID CASE: UNEXPECTED REJECTION")
        print(json.dumps(valid_serializer.errors, indent=2))
        return 1

    print("VALID CASE: ACCEPTED")
    for result in dcyn.evaluate(valid_serializer.validated_data):
        print(f"{result.rule_id}: {result.outcome} — {result.question}")

    strict_boolean_payload = deepcopy(build_valid_payload())
    strict_boolean_payload["guardian"]["consent_to_process"] = "yes"
    strict_boolean_serializer = StudentOnboardingSerializer(data=strict_boolean_payload)
    if strict_boolean_serializer.is_valid():
        print("STRICT BOOLEAN CASE: UNEXPECTED ACCEPTANCE")
        return 1
    print("\nSTRICT BOOLEAN CASE: REJECTED")
    print(json.dumps(strict_boolean_serializer.errors, indent=2))

    failed_rule_payload = deepcopy(build_valid_payload())
    failed_rule_payload["student"]["learning_support_required"] = False
    failed_rule_serializer = StudentOnboardingSerializer(data=failed_rule_payload)
    if failed_rule_serializer.is_valid():
        print("BINARY RULE CASE: UNEXPECTED ACCEPTANCE")
        return 1
    print("\nBINARY RULE CASE: REJECTED")
    print(json.dumps(failed_rule_serializer.errors, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
