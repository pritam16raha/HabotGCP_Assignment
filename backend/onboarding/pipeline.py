# Author: Pritam Raha <rahapritam32@gmail.com>
import re
from datetime import UTC, date, datetime
from typing import Any

from . import dcyn

IMMUTABLE_STORAGE_URI_PATTERN = re.compile(r"^gs://[a-z0-9][a-z0-9._-]+/incoming/.+#[1-9][0-9]*$")
UNIX_EPOCH_DATE = date(1970, 1, 1)

# Every accepted input leaf appears exactly once in this canonical mapping.
SOURCE_TO_CANONICAL_FIELDS = {
    "schema_version": "schema_version",
    "submission_id": "submission_id",
    "submitted_at": "submitted_at",
    "organisation_id": "organisation_id",
    "student.external_id": "student_external_id",
    "student.first_name": "student_first_name",
    "student.last_name": "student_last_name",
    "student.date_of_birth": "student_date_of_birth",
    "student.emirate": "emirate",
    "student.school_name": "school_name",
    "student.learning_support_required": "learning_support_required",
    "student.has_formal_diagnosis": "has_formal_diagnosis",
    "student.diagnosis_codes": "diagnosis_codes",
    "guardian.full_name": "guardian_full_name",
    "guardian.email": "guardian_email",
    "guardian.phone_e164": "guardian_phone_e164",
    "guardian.relationship": "guardian_relationship",
    "guardian.consent_to_process": "consent_to_process",
    "guardian.consent_timestamp": "consent_timestamp",
    "support.areas": "support_areas",
    "support.requested_hours_per_week": "requested_hours_per_week",
    "support.preferred_language": "preferred_language",
    "support.wheelchair_access_required": "wheelchair_access_required",
}


def datetime_to_epoch_microseconds(value: datetime) -> int:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("All pipeline timestamps must include a UTC offset.")
    return int(value.astimezone(UTC).timestamp() * 1_000_000)


def date_to_epoch_days(value: date) -> int:
    return (value - UNIX_EPOCH_DATE).days


def to_pubsub_event(
    validated_data: dict[str, Any], *, source_object_uri: str, ingested_at: datetime
) -> dict[str, Any]:
    """Map one serializer-approved payload to the exact Pub/Sub and BigQuery contract."""
    if not IMMUTABLE_STORAGE_URI_PATTERN.fullmatch(source_object_uri):
        raise ValueError(
            "source_object_uri must include incoming/ and an immutable generation number."
        )

    results = dcyn.evaluate(validated_data)
    failed_results = dcyn.failed(results)
    if failed_results:
        failed_ids = ", ".join(result.rule_id for result in failed_results)
        raise ValueError(f"Refusing to publish a failed DCYN record: {failed_ids}")

    student = validated_data["student"]
    guardian = validated_data["guardian"]
    support = validated_data["support"]
    return {
        "schema_version": validated_data["schema_version"],
        "submission_id": str(validated_data["submission_id"]),
        "submitted_at": datetime_to_epoch_microseconds(validated_data["submitted_at"]),
        "organisation_id": str(validated_data["organisation_id"]),
        "student_external_id": student["external_id"],
        "student_first_name": student["first_name"],
        "student_last_name": student["last_name"],
        "student_date_of_birth": date_to_epoch_days(student["date_of_birth"]),
        "emirate": student["emirate"],
        "school_name": student["school_name"],
        "learning_support_required": student["learning_support_required"],
        "has_formal_diagnosis": student["has_formal_diagnosis"],
        "diagnosis_codes": student["diagnosis_codes"],
        "guardian_full_name": guardian["full_name"],
        "guardian_email": guardian["email"],
        "guardian_phone_e164": guardian["phone_e164"],
        "guardian_relationship": guardian["relationship"],
        "consent_to_process": guardian["consent_to_process"],
        "consent_timestamp": datetime_to_epoch_microseconds(guardian["consent_timestamp"]),
        "support_areas": support["areas"],
        "requested_hours_per_week": support["requested_hours_per_week"],
        "preferred_language": support["preferred_language"],
        "wheelchair_access_required": support["wheelchair_access_required"],
        "dcyn_all_rules_passed": True,
        "dcyn_failed_rule_ids": [],
        "ingested_at": datetime_to_epoch_microseconds(ingested_at),
        "source_object_uri": source_object_uri,
    }
