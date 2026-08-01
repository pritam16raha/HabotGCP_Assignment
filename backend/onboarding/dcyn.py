# Author: Pritam Raha <rahapritam32@gmail.com>
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

MINIMUM_STUDENT_AGE_YEARS = 3
MAXIMUM_STUDENT_AGE_YEARS = 21
MAXIMUM_CONSENT_AGE_DAYS = 30


@dataclass(frozen=True, slots=True)
class DCYNResult:
    """One Deconstruction of Compliance into Yes or No result."""

    rule_id: str
    question: str
    passed: bool
    failure_message: str

    @property
    def outcome(self) -> str:
        return "YES" if self.passed else "NO"


@dataclass(frozen=True, slots=True)
class DCYNRule:
    rule_id: str
    question: str
    failure_message: str
    predicate: Callable[[dict[str, Any]], bool]

    def evaluate(self, payload: dict[str, Any]) -> DCYNResult:
        return DCYNResult(
            rule_id=self.rule_id,
            question=self.question,
            passed=bool(self.predicate(payload)),
            failure_message=self.failure_message,
        )


def age_on(date_of_birth: date, reference_date: date) -> int:
    birthday_has_occurred = (reference_date.month, reference_date.day) >= (
        date_of_birth.month,
        date_of_birth.day,
    )
    return reference_date.year - date_of_birth.year - (not birthday_has_occurred)


def _age_is_in_range(payload: dict[str, Any]) -> bool:
    age = age_on(payload["student"]["date_of_birth"], payload["submitted_at"].date())
    return MINIMUM_STUDENT_AGE_YEARS <= age <= MAXIMUM_STUDENT_AGE_YEARS


def _consent_precedes_submission(payload: dict[str, Any]) -> bool:
    consent_timestamp = payload["guardian"]["consent_timestamp"]
    submitted_at = payload["submitted_at"]
    return (
        submitted_at - timedelta(days=MAXIMUM_CONSENT_AGE_DAYS) <= consent_timestamp <= submitted_at
    )


def _support_request_is_consistent(payload: dict[str, Any]) -> bool:
    support_required = payload["student"]["learning_support_required"]
    areas = payload["support"]["areas"]
    hours = payload["support"]["requested_hours_per_week"]
    return (support_required and bool(areas) and 1 <= hours <= 40) or (
        not support_required and not areas and hours == 0
    )


def _diagnosis_is_consistent(payload: dict[str, Any]) -> bool:
    declared = payload["student"]["has_formal_diagnosis"]
    codes = payload["student"]["diagnosis_codes"]
    return (declared and bool(codes)) or (not declared and not codes)


def _controlled_lists_are_unique(payload: dict[str, Any]) -> bool:
    diagnoses = payload["student"]["diagnosis_codes"]
    support_areas = payload["support"]["areas"]
    return len(diagnoses) == len(set(diagnoses)) and len(support_areas) == len(set(support_areas))


RULES: tuple[DCYNRule, ...] = (
    DCYNRule(
        "DCYN-001",
        "Did the guardian explicitly consent to processing?",
        "consent_to_process must be true.",
        lambda payload: payload["guardian"]["consent_to_process"] is True,
    ),
    DCYNRule(
        "DCYN-002",
        "Was consent recorded no more than 30 days before submission?",
        "consent_timestamp must be on or before submitted_at and no more than 30 days old.",
        _consent_precedes_submission,
    ),
    DCYNRule(
        "DCYN-003",
        "Is the student between 3 and 21 years old on the submission date?",
        "student age must be between 3 and 21 years inclusive.",
        _age_is_in_range,
    ),
    DCYNRule(
        "DCYN-004",
        "Do the support areas and weekly hours exactly match the support decision?",
        "support details must be populated for Yes and empty with zero hours for No.",
        _support_request_is_consistent,
    ),
    DCYNRule(
        "DCYN-005",
        "Do diagnosis codes exactly match the formal diagnosis decision?",
        "diagnosis codes must be populated for Yes and empty for No.",
        _diagnosis_is_consistent,
    ),
    DCYNRule(
        "DCYN-006",
        "Does each controlled list contain unique values only?",
        "diagnosis codes and support areas must not contain duplicates.",
        _controlled_lists_are_unique,
    ),
)


def evaluate(payload: dict[str, Any]) -> tuple[DCYNResult, ...]:
    """Evaluate every rule without short-circuiting so rejection evidence is complete."""
    return tuple(rule.evaluate(payload) for rule in RULES)


def failed(results: tuple[DCYNResult, ...]) -> tuple[DCYNResult, ...]:
    return tuple(result for result in results if not result.passed)
