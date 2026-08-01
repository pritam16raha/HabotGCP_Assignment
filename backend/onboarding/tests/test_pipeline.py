# Author: Pritam Raha <rahapritam32@gmail.com>
from datetime import UTC, datetime

from django.test import SimpleTestCase

from onboarding.pipeline import SOURCE_TO_CANONICAL_FIELDS, to_pubsub_event
from onboarding.serializers import StudentOnboardingSerializer
from onboarding.tests.test_serializers import valid_payload


class PipelineMappingTests(SimpleTestCase):
    def test_every_source_leaf_has_one_canonical_destination(self) -> None:
        self.assertEqual(len(SOURCE_TO_CANONICAL_FIELDS), 23)
        self.assertEqual(
            len(SOURCE_TO_CANONICAL_FIELDS.values()), len(set(SOURCE_TO_CANONICAL_FIELDS.values()))
        )

    def test_validated_payload_maps_without_field_loss(self) -> None:
        serializer = StudentOnboardingSerializer(data=valid_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = to_pubsub_event(
            serializer.validated_data,
            source_object_uri="gs://habot-onboarding-d0/incoming/2026/07/record.json#172233",
            ingested_at=datetime.now(UTC),
        )
        self.assertEqual(len(event), 27)
        self.assertTrue(event["dcyn_all_rules_passed"])
        self.assertEqual(event["dcyn_failed_rule_ids"], [])
        self.assertIsInstance(event["submitted_at"], int)
        self.assertIsInstance(event["student_date_of_birth"], int)

    def test_mutable_source_uri_is_rejected(self) -> None:
        serializer = StudentOnboardingSerializer(data=valid_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaisesRegex(ValueError, "immutable generation"):
            to_pubsub_event(
                serializer.validated_data,
                source_object_uri="gs://habot-onboarding-d0/incoming/record.json",
                ingested_at=datetime.now(UTC),
            )
