#!/usr/bin/env python3
# Author: Pritam Raha <rahapritam32@gmail.com>
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
BIGQUERY_SCHEMA_PATH = REPOSITORY_ROOT / "contracts/bigquery/student_onboarding.schema.json"
PUBSUB_SCHEMA_PATH = REPOSITORY_ROOT / "contracts/pubsub/student_onboarding.avsc"
EXPECTED_CANONICAL_FIELD_COUNT = 27


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source_file:
        return json.load(source_file)


def _avro_to_bigquery(avro_type: Any) -> tuple[str, str]:
    mode = "REQUIRED"
    if isinstance(avro_type, str):
        type_mapping = {
            "boolean": "BOOLEAN",
            "double": "FLOAT",
            "int": "INTEGER",
            "long": "INTEGER",
            "string": "STRING",
        }
        try:
            return type_mapping[avro_type], mode
        except KeyError as exc:
            raise ValueError(f"Unsupported Avro scalar type: {avro_type}") from exc

    if avro_type.get("type") == "array":
        element_type, _ = _avro_to_bigquery(avro_type["items"])
        return element_type, "REPEATED"

    logical_type = avro_type.get("logicalType")
    logical_mapping = {
        ("int", "date"): "DATE",
        ("long", "timestamp-micros"): "TIMESTAMP",
        ("long", "timestamp-millis"): "TIMESTAMP",
    }
    try:
        return logical_mapping[(avro_type.get("type"), logical_type)], mode
    except KeyError as exc:
        raise ValueError(f"Unsupported Avro logical type: {avro_type}") from exc


def validate_contracts() -> list[str]:
    errors: list[str] = []
    bigquery_fields = _load_json(BIGQUERY_SCHEMA_PATH)
    pubsub_fields = _load_json(PUBSUB_SCHEMA_PATH)["fields"]

    if len(bigquery_fields) != EXPECTED_CANONICAL_FIELD_COUNT:
        errors.append(
            f"BigQuery has {len(bigquery_fields)} fields; "
            f"expected {EXPECTED_CANONICAL_FIELD_COUNT}."
        )
    if len(pubsub_fields) != EXPECTED_CANONICAL_FIELD_COUNT:
        errors.append(
            f"Pub/Sub has {len(pubsub_fields)} fields; expected {EXPECTED_CANONICAL_FIELD_COUNT}."
        )

    for index, (bigquery_field, pubsub_field) in enumerate(
        zip(bigquery_fields, pubsub_fields, strict=False), start=1
    ):
        if bigquery_field["name"] != pubsub_field["name"]:
            errors.append(
                f"Field {index} name mismatch: BigQuery={bigquery_field['name']} "
                f"Pub/Sub={pubsub_field['name']}."
            )
            continue
        expected_type, expected_mode = _avro_to_bigquery(pubsub_field["type"])
        if bigquery_field["type"] != expected_type:
            errors.append(
                f"{bigquery_field['name']} type mismatch: BigQuery={bigquery_field['type']} "
                f"Pub/Sub maps to {expected_type}."
            )
        if bigquery_field["mode"] != expected_mode:
            errors.append(
                f"{bigquery_field['name']} mode mismatch: BigQuery={bigquery_field['mode']} "
                f"Pub/Sub maps to {expected_mode}."
            )
        if not bigquery_field.get("description", "").strip():
            errors.append(f"{bigquery_field['name']} is missing a BigQuery description.")

    sys.path.insert(0, str(BACKEND_ROOT))
    from onboarding.pipeline import SOURCE_TO_CANONICAL_FIELDS

    source_destinations = set(SOURCE_TO_CANONICAL_FIELDS.values())
    canonical_names = {field["name"] for field in bigquery_fields}
    system_generated = {
        "dcyn_all_rules_passed",
        "dcyn_failed_rule_ids",
        "ingested_at",
        "source_object_uri",
    }
    if source_destinations | system_generated != canonical_names:
        missing = sorted(canonical_names - source_destinations - system_generated)
        unexpected = sorted(source_destinations - canonical_names)
        errors.append(f"Source mapping mismatch; missing={missing}, unexpected={unexpected}.")
    return errors


def main() -> int:
    errors = validate_contracts()
    if errors:
        print("Contract validation: FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Contract validation: PASSED — 23 source leaves plus 4 system fields map "
        "exactly to 27 Pub/Sub and BigQuery fields."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
