# Author: Pritam Raha <rahapritam32@gmail.com>
import re
import unicodedata
from collections.abc import Mapping
from datetime import UTC, timedelta
from typing import Any, ClassVar

from django.utils import timezone
from rest_framework import serializers

from . import dcyn
from .models import (
    Emirate,
    GuardianRelationship,
    PreferredLanguage,
    StudentOnboarding,
    SupportArea,
)

NAME_PATTERN = re.compile(r"^[^\W\d_]+(?:[ .'-][^\W\d_]+)*$", re.UNICODE)
STUDENT_IDENTIFIER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{5,31}$")
DIAGNOSIS_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{1,11}$")
E164_PATTERN = re.compile(r"^\+[1-9][0-9]{7,14}$")


class RejectUnknownFieldsMixin:
    """Fail closed instead of silently discarding unexpected client data."""

    def to_internal_value(self, data: Any) -> Any:
        if isinstance(data, Mapping):
            unknown_fields = sorted(set(data) - set(self.fields))
            if unknown_fields:
                raise serializers.ValidationError(
                    {
                        field: ["Unknown field; the request schema is closed."]
                        for field in unknown_fields
                    }
                )
        return super().to_internal_value(data)


class StrictBooleanField(serializers.BooleanField):
    default_error_messages: ClassVar[dict[str, str]] = {
        "invalid": "Must be a JSON boolean: true or false."
    }

    def to_internal_value(self, data: Any) -> bool:
        if type(data) is not bool:
            self.fail("invalid")
        return super().to_internal_value(data)


def validate_person_name(value: str) -> str:
    if not NAME_PATTERN.fullmatch(value):
        raise serializers.ValidationError(
            "Use letters separated only by single spaces, apostrophes, periods, or hyphens."
        )
    return value


def validate_printable_text(value: str) -> str:
    if any(unicodedata.category(character).startswith("C") for character in value):
        raise serializers.ValidationError("Control characters are not permitted.")
    return value


class StudentSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    external_id = serializers.RegexField(STUDENT_IDENTIFIER_PATTERN, min_length=6, max_length=32)
    first_name = serializers.CharField(
        min_length=1, max_length=50, trim_whitespace=True, validators=[validate_person_name]
    )
    last_name = serializers.CharField(
        min_length=1, max_length=50, trim_whitespace=True, validators=[validate_person_name]
    )
    date_of_birth = serializers.DateField()
    emirate = serializers.ChoiceField(choices=Emirate.values)
    school_name = serializers.CharField(
        min_length=2, max_length=120, trim_whitespace=True, validators=[validate_printable_text]
    )
    learning_support_required = StrictBooleanField()
    has_formal_diagnosis = StrictBooleanField()
    diagnosis_codes = serializers.ListField(
        child=serializers.RegexField(DIAGNOSIS_CODE_PATTERN, min_length=2, max_length=12),
        allow_empty=True,
        max_length=10,
    )


class GuardianSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    full_name = serializers.CharField(
        min_length=3, max_length=101, trim_whitespace=True, validators=[validate_person_name]
    )
    email = serializers.EmailField(max_length=254)
    phone_e164 = serializers.RegexField(E164_PATTERN, min_length=9, max_length=16)
    relationship = serializers.ChoiceField(choices=GuardianRelationship.values)
    consent_to_process = StrictBooleanField()
    consent_timestamp = serializers.DateTimeField(default_timezone=UTC)


class SupportSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    areas = serializers.ListField(
        child=serializers.ChoiceField(choices=SupportArea.values),
        allow_empty=True,
        max_length=len(SupportArea.values),
    )
    requested_hours_per_week = serializers.IntegerField(min_value=0, max_value=40)
    preferred_language = serializers.ChoiceField(choices=PreferredLanguage.values)
    wheelchair_access_required = StrictBooleanField()


class StudentOnboardingSerializer(RejectUnknownFieldsMixin, serializers.ModelSerializer):
    """Closed, nested contract with deterministic cross-field validation."""

    schema_version = serializers.ChoiceField(choices=("1.0",))
    submission_id = serializers.UUIDField()
    submitted_at = serializers.DateTimeField(default_timezone=UTC)
    organisation_id = serializers.UUIDField()
    student = StudentSerializer(write_only=True)
    guardian = GuardianSerializer(write_only=True)
    support = SupportSerializer(write_only=True)

    class Meta:
        model = StudentOnboarding
        fields = (
            "schema_version",
            "submission_id",
            "submitted_at",
            "organisation_id",
            "student",
            "guardian",
            "support",
        )

    def validate(self, attributes: dict[str, Any]) -> dict[str, Any]:
        submitted_at = attributes["submitted_at"]
        current_time = timezone.now()
        if submitted_at > current_time + timedelta(minutes=5):
            raise serializers.ValidationError(
                {"submitted_at": "Must not be more than 5 minutes in the future."}
            )
        if submitted_at < current_time - timedelta(hours=24):
            raise serializers.ValidationError(
                {"submitted_at": "Must not be more than 24 hours old."}
            )

        results = dcyn.evaluate(attributes)
        failed_results = dcyn.failed(results)
        if failed_results:
            raise serializers.ValidationError(
                {
                    "dcyn": [
                        f"{result.rule_id}: {result.failure_message}" for result in failed_results
                    ]
                }
            )
        return attributes

    def create(self, validated_data: dict[str, Any]) -> StudentOnboarding:
        student = validated_data.pop("student")
        guardian = validated_data.pop("guardian")
        support = validated_data.pop("support")
        return StudentOnboarding.objects.create(
            **validated_data,
            student_external_id=student["external_id"],
            student_first_name=student["first_name"],
            student_last_name=student["last_name"],
            student_date_of_birth=student["date_of_birth"],
            emirate=student["emirate"],
            school_name=student["school_name"],
            learning_support_required=student["learning_support_required"],
            has_formal_diagnosis=student["has_formal_diagnosis"],
            diagnosis_codes=student["diagnosis_codes"],
            guardian_full_name=guardian["full_name"],
            guardian_email=guardian["email"],
            guardian_phone_e164=guardian["phone_e164"],
            guardian_relationship=guardian["relationship"],
            consent_to_process=guardian["consent_to_process"],
            consent_timestamp=guardian["consent_timestamp"],
            support_areas=support["areas"],
            requested_hours_per_week=support["requested_hours_per_week"],
            preferred_language=support["preferred_language"],
            wheelchair_access_required=support["wheelchair_access_required"],
            dcyn_all_rules_passed=True,
            dcyn_failed_rule_ids=[],
        )
