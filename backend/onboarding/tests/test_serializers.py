# Author: Pritam Raha <rahapritam32@gmail.com>
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from onboarding.serializers import StudentOnboardingSerializer


def valid_payload() -> dict:
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


class StudentOnboardingSerializerTests(TestCase):
    def assert_rejected(self, payload: dict, expected_text: str) -> None:
        serializer = StudentOnboardingSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn(expected_text, str(serializer.errors))

    def test_valid_payload_passes_every_gate(self) -> None:
        serializer = StudentOnboardingSerializer(data=valid_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_payload_persists_the_flattened_model(self) -> None:
        serializer = StudentOnboardingSerializer(data=valid_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        record = serializer.save()
        self.assertEqual(record.student_external_id, "STU-DXB-2048")
        self.assertTrue(record.dcyn_all_rules_passed)
        self.assertEqual(record.dcyn_failed_rule_ids, [])

    def test_unknown_field_fails_closed(self) -> None:
        payload = valid_payload()
        payload["student"]["unreviewed_note"] = "silently ignoring this would lose data"
        self.assert_rejected(payload, "Unknown field")

    def test_string_boolean_is_rejected(self) -> None:
        payload = valid_payload()
        payload["guardian"]["consent_to_process"] = "yes"
        self.assert_rejected(payload, "JSON boolean")

    def test_consent_no_is_rejected_by_binary_rule(self) -> None:
        payload = valid_payload()
        payload["guardian"]["consent_to_process"] = False
        self.assert_rejected(payload, "DCYN-001")

    def test_diagnosis_decision_requires_codes(self) -> None:
        payload = valid_payload()
        payload["student"]["diagnosis_codes"] = []
        self.assert_rejected(payload, "DCYN-005")

    def test_no_support_requires_empty_areas_and_zero_hours(self) -> None:
        payload = valid_payload()
        payload["student"]["learning_support_required"] = False
        self.assert_rejected(payload, "DCYN-004")

    def test_duplicates_are_rejected(self) -> None:
        payload = valid_payload()
        payload["support"]["areas"].append("COMMUNICATION")
        self.assert_rejected(payload, "DCYN-006")

    def test_student_older_than_21_is_rejected(self) -> None:
        payload = valid_payload()
        submitted_date = timezone.now().date()
        payload["student"]["date_of_birth"] = submitted_date.replace(
            year=submitted_date.year - 22
        ).isoformat()
        self.assert_rejected(payload, "DCYN-003")

    def test_payload_older_than_24_hours_is_rejected(self) -> None:
        payload = deepcopy(valid_payload())
        payload["submitted_at"] = (timezone.now() - timedelta(hours=25)).isoformat()
        self.assert_rejected(payload, "24 hours old")
