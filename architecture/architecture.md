# Architecture and trust boundaries

Author: Pritam Raha  
Contact: rahapritam32@gmail.com

## Decision summary

The system separates untrusted capture, deterministic validation, schema-enforced transport, and governed analytics. Each boundary rejects uncertainty; no stage infers a missing value or silently drops an unknown field.

| Boundary | Input | Enforced decision | Output |
|---|---|---|---|
| Application boundary | Student onboarding JSON | Closed serializer, types, lengths, choices, timestamps | Validated nested Python data or structured rejection |
| Compliance boundary | Validated data | Six Deconstruction of Compliance into Yes or No rules | All Yes, or quarantine with exact failed rule identifiers |
| Raw landing boundary | Accepted source JSON | `incoming/` prefix condition, create-only identity, immutable object generation | Versioned and encrypted D0 object |
| Mapping boundary | Accepted payload and object generation | One-to-one mapping of 23 leaves; four explicit system fields | 27-field canonical event |
| Messaging boundary | Canonical event | Pub/Sub Avro schema using JSON encoding | Only schema-valid messages |
| Analytics boundary | Schema-valid event | BigQuery subscription with unknown-field dropping disabled | Partitioned D1 row or retained undelivered message |
| Query boundary | Authenticated query | Dataset role plus row access policy | Full pipeline rows or Dubai-only analytics rows |

## Security controls

### Confidentiality

- Cloud Storage, Pub/Sub, and BigQuery use separate customer-managed encryption keys.
- Google-managed service agents receive encrypt and decrypt permission only on the corresponding key.
- Public access prevention and uniform bucket-level access eliminate object access control lists.
- No application or pipeline credential is stored in source control. Workloads use service identities.
- The Doha region is the default for raw, streaming, staged, and encryption resources.

### Integrity

- Raw upload permission is `storage.objectCreator` conditioned to `incoming/`; it cannot overwrite, read, list, or delete objects.
- Object versioning, seven-day retention, seven-day soft deletion, and access logging support recovery and accountability.
- Pub/Sub rejects messages that violate the Avro contract.
- BigQuery refuses unknown fields because `drop_unknown_fields` is false.
- The BigQuery table has deletion protection and 96-hour time travel.
- CI checks contract name, type, mode, order, and mapping cardinality.

### Availability and cost

- Managed regional services remove server administration from this staging scope.
- BigQuery partitions by ingestion day, clusters by organisation and student identifier, and expires partitions after 90 days.
- Pub/Sub retains unacknowledged messages for seven days and the subscription expires after 31 idle days.
- The raw quarantine prefix expires after 30 days; access logs expire after 90 days.

## Identity matrix

| Identity | Scope | Allowed | Explicitly not allowed |
|---|---|---|---|
| Raw ingestor | D0 `incoming/` objects | Create new objects | Read, list, overwrite, delete, access D1 |
| Data pipeline | D0 `incoming/`; D1 dataset; BigQuery jobs | Read raw objects, transform, maintain staged data | Manage Identity and Access Management, keys, or buckets |
| Pub/Sub service agent | D1 dataset; Pub/Sub key | Deliver schema-valid events, encrypt topic data | Query analytics data or manage infrastructure |
| Dubai analytics reader | D1 dataset and BigQuery jobs | Query rows where emirate equals Dubai | See rows from other emirates or modify data |
| Storage and BigQuery service agents | One corresponding key | Encrypt and decrypt managed data | Administer the key ring or other keys |

## Failure behaviour

| Failure | System response | Recovery evidence |
|---|---|---|
| Unknown JSON field | Request rejected; nothing persisted or published | Serializer field error |
| Invalid binary or cross-field state | Request rejected with one or more rule identifiers | Deconstruction of Compliance into Yes or No result list |
| Pub/Sub schema drift | Publish rejected | Publisher error and retained D0 generation |
| BigQuery incompatibility | Delivery remains unsuccessful; message retained | Subscription delivery metrics and D0 lineage URI |
| Hardcoded credential or formatting issue | CI job fails immediately; downstream authorisation never runs | Quarantine artifact retained for 14 days |
| Accidental table or key destroy | Terraform refuses the operation | Plan failure and protected state |

