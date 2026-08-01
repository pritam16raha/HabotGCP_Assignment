# Author: Pritam Raha <rahapritam32@gmail.com>
from typing import ClassVar

from django.db import models
from django.db.models import Q


class Emirate(models.TextChoices):
    ABU_DHABI = "ABU_DHABI", "Abu Dhabi"
    AJMAN = "AJMAN", "Ajman"
    DUBAI = "DUBAI", "Dubai"
    FUJAIRAH = "FUJAIRAH", "Fujairah"
    RAS_AL_KHAIMAH = "RAS_AL_KHAIMAH", "Ras Al Khaimah"
    SHARJAH = "SHARJAH", "Sharjah"
    UMM_AL_QUWAIN = "UMM_AL_QUWAIN", "Umm Al Quwain"


class GuardianRelationship(models.TextChoices):
    FOSTER_GUARDIAN = "FOSTER_GUARDIAN", "Foster guardian"
    LEGAL_GUARDIAN = "LEGAL_GUARDIAN", "Legal guardian"
    PARENT = "PARENT", "Parent"


class PreferredLanguage(models.TextChoices):
    ARABIC = "ARABIC", "Arabic"
    ENGLISH = "ENGLISH", "English"
    HINDI = "HINDI", "Hindi"
    MALAYALAM = "MALAYALAM", "Malayalam"
    TAMIL = "TAMIL", "Tamil"
    URDU = "URDU", "Urdu"


class SupportArea(models.TextChoices):
    ACADEMIC_SKILLS = "ACADEMIC_SKILLS", "Academic skills"
    ATTENTION = "ATTENTION", "Attention"
    COMMUNICATION = "COMMUNICATION", "Communication"
    EMOTIONAL_REGULATION = "EMOTIONAL_REGULATION", "Emotional regulation"
    MOBILITY = "MOBILITY", "Mobility"
    SELF_CARE = "SELF_CARE", "Self care"
    SOCIAL_INTERACTION = "SOCIAL_INTERACTION", "Social interaction"
    SENSORY_PROCESSING = "SENSORY_PROCESSING", "Sensory processing"


class StudentOnboarding(models.Model):
    """Validated transactional record; transport nesting is flattened for persistence."""

    submission_id = models.UUIDField(primary_key=True, editable=False)
    schema_version = models.CharField(max_length=3, choices=[("1.0", "1.0")])
    submitted_at = models.DateTimeField()
    organisation_id = models.UUIDField(db_index=True)

    student_external_id = models.CharField(max_length=32)
    student_first_name = models.CharField(max_length=50)
    student_last_name = models.CharField(max_length=50)
    student_date_of_birth = models.DateField()
    emirate = models.CharField(max_length=18, choices=Emirate.choices)
    school_name = models.CharField(max_length=120)
    learning_support_required = models.BooleanField()
    has_formal_diagnosis = models.BooleanField()
    diagnosis_codes = models.JSONField(default=list)

    guardian_full_name = models.CharField(max_length=101)
    guardian_email = models.EmailField(max_length=254)
    guardian_phone_e164 = models.CharField(max_length=16)
    guardian_relationship = models.CharField(max_length=16, choices=GuardianRelationship.choices)
    consent_to_process = models.BooleanField()
    consent_timestamp = models.DateTimeField()

    support_areas = models.JSONField(default=list)
    requested_hours_per_week = models.PositiveSmallIntegerField()
    preferred_language = models.CharField(max_length=9, choices=PreferredLanguage.choices)
    wheelchair_access_required = models.BooleanField()

    dcyn_all_rules_passed = models.BooleanField(default=True, editable=False)
    dcyn_failed_rule_ids = models.JSONField(default=list, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_onboarding"
        ordering: ClassVar[list[str]] = ["-submitted_at"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(requested_hours_per_week__gte=0) & Q(requested_hours_per_week__lte=40),
                name="onboarding_hours_between_0_and_40",
            ),
            models.CheckConstraint(
                condition=Q(consent_to_process=True),
                name="onboarding_requires_processing_consent",
            ),
            models.CheckConstraint(
                condition=Q(dcyn_all_rules_passed=True),
                name="onboarding_requires_all_dcyn_rules",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["organisation_id", "student_external_id"],
                name="onboard_org_student_idx",
            )
        ]
