# Live Google Cloud deployment evidence

Author: Pritam Raha  
Contact: rahapritam32@gmail.com  
Verified: 1 August 2026

## Deployment boundary

The assignment is deployed in the dedicated Google Cloud project `habot-staging-pritam-raha-2026` (`Habot GCP Assignment`) in `me-central1`. Terraform state is isolated in `gs://habot-staging-pritam-raha-2026-terraform-state` with uniform bucket-level access, public access prevention, versioning, and seven-day soft deletion.

The separate project `outloop-email-backend` was not selected or mutated. The reviewed initial plan contained 123 references to the assignment project and zero references to the existing email project. The dedicated `habot-assignment` Google Cloud CLI configuration and Application Default Credentials quota project were pinned to the assignment project before deployment.

No service-account key was created. Live identity checks used short-lived service-account impersonation. The operator has `roles/iam.serviceAccountTokenCreator` only on the three assignment test identities so the demonstrations can be repeated without a project-wide impersonation grant.

Project console: [Habot GCP Assignment](https://console.cloud.google.com/home/dashboard?project=habot-staging-pritam-raha-2026)

## Deployment result

| Control | Observed live result | Status |
|---|---|---|
| Terraform remote state | Dedicated `ME-CENTRAL1` bucket; uniform access, public access prevention, versioning, and soft deletion enabled | Pass |
| Terraform apply | Reviewed create-only plans applied; no update or destroy action was approved | Pass |
| Drift | Final detailed-exit-code plan returned `0` and `No changes` | Pass |
| Destruction resistance | Read-only destroy plan failed on all three KMS keys because `prevent_destroy` is enabled; it was not saved or applied | Pass |
| Project isolation | Machine-readable plan contained zero `outloop-email-backend` references | Pass |

## Storage evidence

Raw bucket: `habot-staging-pritam-raha-2026-d0-raw-staging`

| Test | Observed result | Status |
|---|---|---|
| Location | `ME-CENTRAL1` | Pass |
| Public access prevention | `enforced` | Pass |
| Uniform bucket-level access | `true` | Pass |
| Customer-managed encryption | `d0-raw-storage` KMS key, key version 1 observed on the test object | Pass |
| Recovery controls | Versioning enabled; seven-day retention and seven-day soft deletion | Pass |
| Audit path | Separate security-log bucket and `d0-raw-access/` prefix configured | Pass |
| Raw ingestor create under `incoming/` | Direct media upload with `ifGenerationMatch=0` returned HTTP `200` | Pass |
| Raw ingestor create under `quarantine/` | HTTP `403`, `storage.objects.create` denied | Pass |
| Raw ingestor read | HTTP `403`, `storage.objects.get` denied | Pass |
| Raw ingestor delete | Permission denied | Pass |
| Anonymous object request | HTTP `403` | Pass |
| Pipeline read under `incoming/` | Succeeded | Pass |
| Pipeline object creation | HTTP `403`, `storage.objects.create` denied | Pass |

The retained synthetic object is `incoming/manual/verification-rest-20260801t181000z.json`. Its observed retention expiry is 8 August 2026. It contains only the repository's synthetic example data.

## Pub/Sub and BigQuery evidence

Topic: `student-onboarding-validated-v1`  
Subscription: `student-onboarding-bigquery-v1`  
Table: `student_onboarding_d1_staging.student_onboarding_enforced`

| Test | Observed result | Status |
|---|---|---|
| Pub/Sub schema binding | Avro schema `student-onboarding-v1`, JSON encoding | Pass |
| Pub/Sub encryption | `validated-events` customer-managed KMS key | Pass |
| BigQuery subscription | State `ACTIVE`; topic schema enabled; unknown fields are not dropped | Pass |
| Valid Dubai event | Published and delivered | Pass |
| Valid Sharjah event | Published and delivered | Pass |
| Wrong-type event | Rejected with `INVALID_ARGUMENT` and `INVALID_JSON_AVRO_MESSAGE` | Pass |
| Table schema | Exactly 27 fields | Pass |
| Table layout | Daily partition on `ingested_at`; clustered by `organisation_id` and `student_external_id` | Pass |
| BigQuery encryption | `d1-bigquery` customer-managed KMS key | Pass |
| Pipeline row policy | Predicate `TRUE`; impersonated query returned one Dubai and one Sharjah row | Pass |
| Analytics row policy | Predicate `emirate = 'DUBAI'`; impersonated query returned the Dubai row only | Pass |

The two delivered rows are synthetic verification records. A direct operator query returned no rows because the deployed row policies grant filtered-data access only to the two workload identities; the impersonated identity queries are the authoritative behavioural evidence.

## Encryption evidence

The `habot-onboarding-staging-data` key ring contains three `ENCRYPT_DECRYPT` keys:

- `d0-raw-storage`
- `d1-bigquery`
- `validated-events`

All three use a `7776000s` rotation period (90 days) and reported their next rotation on 30 October 2026.

## Presentation sequence

1. Open the dedicated project dashboard and state that it is isolated from the existing email project.
2. Show the raw bucket protection, logging, retention, and customer-managed encryption fields.
3. Show the schema-bound Pub/Sub topic and active BigQuery subscription.
4. Show the 27-field partitioned and clustered BigQuery table.
5. List the two row policies, then run the pipeline and analytics impersonated queries from `docs/manual-verification-guide.md`.
6. Publish the invalid wrong-type event and show the schema rejection.
7. Finish with a Terraform plan showing `No changes` and the GitHub fail-closed workflow evidence.

## Operational note

These resources are billable and intentionally difficult to destroy. No billing-account-wide budget was created because the billing account is shared with another application; any budget or alert must be scoped explicitly to this project and approved separately. Do not run `terraform destroy`, weaken deletion protection, or remove retention controls merely to simplify cleanup.
