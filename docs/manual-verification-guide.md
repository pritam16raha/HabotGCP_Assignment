# Manual verification guide

Author: Pritam Raha  
Contact: rahapritam32@gmail.com

This guide separates evidence that can be reproduced locally from evidence that requires GitHub or a billable Google Cloud staging project. A local pass proves syntax, policy, contract, and business-rule behaviour. It does not prove that a real cloud account has successfully created the resources.

## Level 1: Local acceptance test

This level is safe: it does not create Google Cloud resources.

### Prerequisites

- Python 3.12
- Terraform 1.14 or later
- Internet access for the first dependency and provider installation

### Run

```bash
make install
make validate
```

### Pass criteria

Confirm all of these in the output:

| Control | Required result |
|---|---|
| Ruff formatter | All files already formatted |
| Ruff linter | All checks passed |
| Bandit | No issues identified |
| Django deployment check | No issues |
| Django serializer, persistence, and mapping suite | 13 tests passed |
| Independent credential scanner suite | 2 tests passed |
| Python dependency audit | No known vulnerabilities found |
| Contract comparison | 23 source leaves plus 4 system fields equal 27 fields |
| Repository credential scan | No credential patterns detected |
| Terraform validation | Configuration is valid |
| Terraform mocked plan | 1 passed, 0 failed |
| Checkov | 41 passed, 0 failed, 1 documented terminal-log exception |
| Negative credential demonstration | One synthetic unsafe input blocked |

The Checkov exception applies only to the terminal access-log bucket. Making that bucket log into itself would create recursive logs. The raw landing bucket itself has access logging enabled and passes the logging policy.

### Demonstrate the serializer manually

```bash
.venv/bin/python scripts/manual_serializer_demo.py
```

Expected behaviour:

1. The valid request is accepted and rules 001 through 006 all print `YES`.
2. The string `"yes"` is rejected because the field accepts only the JavaScript Object Notation boolean `true` or `false`.
3. A contradictory support decision is rejected with rule `DCYN-004`.

### Demonstrate the build quarantine manually

```bash
make demo-fail-closed
```

Expected result:

```text
Fail-closed demonstration: PASSED — a synthetic hardcoded credential produced 1 finding and a non-deployable result.
```

The insecure input exists only in a temporary directory and is deleted automatically.

### Verify submission-format requirements

```bash
make install-artifacts
.venv/bin/python scripts/build_submission_artifacts.py
unzip -t submission/Pritam_Raha_Junior_Cloud_DevOps_Assignment.zip
```

The builder fails if any populated workbook cell does not have Wrap Text enabled. It creates a 13-slide presentation, which is below the 15-slide limit. The archive integrity command must end with `No errors detected`.

Optional structural checks:

```bash
test -f infrastructure/main.tf
test -f .github/workflows/quality-security-gate.yml
test -f backend/onboarding/serializers.py
test -f backend/onboarding/dcyn.py
test -f submission/Pritam_Raha_Engineering_Blueprint.pptx
test -f submission/Pritam_Raha_Schema_Mapping.xlsx
```

Every command must return exit status zero.

## Level 2: GitHub fail-closed demonstration

This level verifies the actual workflow graph. Use a temporary branch and synthetic content only. Never use a real credential.

### Passing case

1. Create a GitHub repository and push the project.
2. Open the repository Actions page.
3. Run `Quality and Security Fail-Closed Gate` manually or open a clean pull request.
4. Confirm `Mandatory quality and security gate` succeeds.
5. Confirm `Emit release authorisation only after every gate passes` runs only after the first job succeeds.

### Failing case

Create a temporary branch, then generate an unsafe test file without placing the complete credential-shaped line in this documentation:

```bash
git switch -c demonstrate-fail-closed
python3 -c 'from pathlib import Path; name="api"+"_key"; value="synthetic-embedded-value-7Q9w2L4p"; Path("temporary_insecure_demo.py").write_text(f"{name} = \"{value}\"\n")'
git add temporary_insecure_demo.py
git commit -m "Demonstrate fail-closed credential gate"
git push --set-upstream origin demonstrate-fail-closed
```

Open a pull request and verify:

- The credential detection step fails.
- Later quality steps do not run.
- The release-authorisation job is skipped.
- A `quarantined-build` artifact contains `status.txt` and the redacted scan report.

Close the pull request and delete the temporary branch after the demonstration. Do not merge it.

## Level 3: Live Google Cloud verification

This level creates billable resources. Run it only in a staging project you own and are authorised to change. Obtain budget approval first. It requires the Google Cloud command-line interface (including `gcloud` and `bq`), `jq`, and `curl`. The operator needs permission to create the resources in the Terraform plan. Service-account impersonation tests additionally require the Service Account Token Creator role on the three test identities.

### Deploy the reviewed plan

Follow `docs/deployment-runbook.md` to create the remote-state bucket. Then run:

```bash
export TF_VAR_project_id="habot-staging-pritam-raha-2026"
export TF_STATE_BUCKET="${TF_VAR_project_id}-terraform-state"
terraform -chdir=infrastructure init -backend-config="bucket=${TF_STATE_BUCKET}"
terraform -chdir=infrastructure plan -out=staging.tfplan
terraform -chdir=infrastructure show staging.tfplan
terraform -chdir=infrastructure apply staging.tfplan
```

Do not apply until the plan shows the intended project and `me-central1` region and no unexpected deletion or broad Identity and Access Management grant.

Capture outputs:

```bash
export RAW_BUCKET="$(terraform -chdir=infrastructure output -raw raw_landing_bucket)"
export RAW_INGESTOR="$(terraform -chdir=infrastructure output -raw raw_ingestor_service_account)"
export DATA_PIPELINE="$(terraform -chdir=infrastructure output -raw data_pipeline_service_account)"
export ANALYTICS_READER="$(terraform -chdir=infrastructure output -raw analytics_reader_service_account)"
export STAGED_TABLE="$(terraform -chdir=infrastructure output -raw staged_table)"
export VALIDATED_TOPIC="$(terraform -chdir=infrastructure output -raw validated_topic)"
```

### Verify Cloud Storage controls

Inspect the bucket:

```bash
gcloud storage buckets describe "gs://${RAW_BUCKET}" --format=yaml
```

Required observations:

- Location is `ME-CENTRAL1`.
- Uniform bucket-level access is enabled.
- Public access prevention is enforced.
- A Cloud Key Management Service key is present.
- Versioning, retention, soft deletion, and a separate logging bucket are configured.

Test allowed and denied actions using short-lived impersonated credentials:

```bash
export TEST_OBJECT="incoming/manual/student-$(date -u +%Y%m%dT%H%M%SZ).json"
export TEST_OBJECT_ENCODED="$(jq -rn --arg value "${TEST_OBJECT}" '$value|@uri')"

curl --fail-with-body --silent --show-error \
  --request POST \
  --header "Authorization: Bearer $(gcloud auth print-access-token --impersonate-service-account="${RAW_INGESTOR}")" \
  --header "Content-Type: application/json" \
  --data-binary @examples/student_onboarding.valid.json \
  --write-out "\nHTTP:%{http_code}\n" \
  "https://storage.googleapis.com/upload/storage/v1/b/${RAW_BUCKET}/o?uploadType=media&name=${TEST_OBJECT_ENCODED}&ifGenerationMatch=0"

gcloud storage cp examples/student_onboarding.valid.json \
  "gs://${RAW_BUCKET}/quarantine/should-be-denied.json" \
  --impersonate-service-account="${RAW_INGESTOR}"

gcloud storage cat "gs://${RAW_BUCKET}/${TEST_OBJECT}" \
  --impersonate-service-account="${RAW_INGESTOR}"

gcloud storage rm "gs://${RAW_BUCKET}/${TEST_OBJECT}" \
  --impersonate-service-account="${RAW_INGESTOR}"
```

The create-only media upload must return Hypertext Transfer Protocol `200`. It uses an in-memory short-lived impersonated token and the generation precondition prevents overwrite. This direct request is intentional: `gcloud storage cp` may perform a destination-read preflight that is incompatible with a strictly write-only identity. The other three commands must return permission denied. Also request the object without authentication; the Hypertext Transfer Protocol response must not be `200`:

```bash
curl --output /dev/null --silent --write-out "%{http_code}\n" \
  "https://storage.googleapis.com/${RAW_BUCKET}/${TEST_OBJECT}"
```

### Verify BigQuery schema and row policies

List the table schema and policies:

```bash
export DATASET_ID="$(printf '%s' "${STAGED_TABLE}" | cut -d. -f2)"
export TABLE_ID="$(printf '%s' "${STAGED_TABLE}" | cut -d. -f3)"
bq --project_id="${TF_VAR_project_id}" show --schema --format=prettyjson \
  "${DATASET_ID}.${TABLE_ID}"
bq --project_id="${TF_VAR_project_id}" show --format=prettyjson \
  "${DATASET_ID}.${TABLE_ID}"
bq --project_id="${TF_VAR_project_id}" ls --row_access_policies \
  "${DATASET_ID}.${TABLE_ID}"
```

Required observations:

- The schema contains exactly 27 fields.
- `pipeline_full_access` has predicate `TRUE`.
- `dubai_analytics_only` has predicate `emirate = 'DUBAI'`.
- The table is partitioned by `ingested_at` and clustered by organisation and student identifiers.

After the two valid synthetic rows in the next section are delivered through the validated topic, query using service-account impersonation:

```bash
CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT="${ANALYTICS_READER}" \
  bq query --use_legacy_sql=false \
  "SELECT emirate, COUNT(*) AS row_count FROM \`${STAGED_TABLE}\` GROUP BY emirate"
```

The analytics result must contain Dubai only. Google recommends service-account impersonation when testing row access policies. A pipeline-identity query should see both synthetic rows.

```bash
CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT="${DATA_PIPELINE}" \
  bq query --use_legacy_sql=false \
  "SELECT emirate, COUNT(*) AS row_count FROM \`${STAGED_TABLE}\` GROUP BY emirate"
```

The pipeline result must contain both `DUBAI` and `SHARJAH`.

### Verify Pub/Sub schema enforcement

Generate two valid canonical events and one deliberately invalid event. The files contain synthetic identities only and are written below the ignored `build/` directory:

```bash
RAW_BUCKET="${RAW_BUCKET}" make generate-cloud-test-events
export TOPIC_ID="${VALIDATED_TOPIC##*/}"

gcloud pubsub topics publish "${TOPIC_ID}" \
  --project="${TF_VAR_project_id}" \
  --message="$(jq -c . build/manual-cloud-events/valid-dubai.json)"

gcloud pubsub topics publish "${TOPIC_ID}" \
  --project="${TF_VAR_project_id}" \
  --message="$(jq -c . build/manual-cloud-events/valid-sharjah.json)"

gcloud pubsub topics publish "${TOPIC_ID}" \
  --project="${TF_VAR_project_id}" \
  --message="$(jq -c . build/manual-cloud-events/invalid-wrong-type.json)"
```

The first two commands must return a message identifier. The third must return `INVALID_ARGUMENT`, Pub/Sub's documented response for a schema mismatch. Do not proceed if the invalid event is accepted. Allow normal subscription delivery time, then run the two BigQuery queries in the previous section.

### Verify encryption and deletion protection

```bash
gcloud kms keys list \
  --keyring="habot-onboarding-staging-data" \
  --location="me-central1" \
  --project="${TF_VAR_project_id}"

terraform -chdir=infrastructure plan -destroy
```

Required observations:

- Three encryption keys exist and have 90-day rotation.
- The destroy plan is blocked by protected keys, the protected BigQuery table, retained objects, or row-policy deletion protection. Do not attempt to weaken these controls merely to make destruction succeed.

## Requirement-to-evidence matrix

| Assignment requirement | Static evidence | Behavioural verification | Passing condition |
|---|---|---|---|
| Structured Terraform and `main.tf` | `infrastructure/main.tf` and reusable module | Terraform validation, plan test, optional live plan | Valid configuration; intended project and region only |
| Secure raw landing bucket | Storage resource, conditional member, encryption and logging resources | Impersonated create/read/delete/prefix tests | Incoming create succeeds; all disallowed operations fail |
| BigQuery staged dataset | Dataset and 27-field table resources | Schema inspection and event delivery | Exact schema; valid event arrives |
| Strict Identity and Access Management | Separate identities and narrow roles | Impersonation tests | Each identity performs only its documented actions |
| Row-level security | Two Terraform row-access-policy resources | Query as analytics identity | Dubai rows only |
| Fail-closed linter and secret gate | GitHub workflow and credential scanner | Clean and deliberately failing pull requests | Clean release authorised; insecure release skipped and quarantined |
| Data mapping without loss | Python mapping, Apache Avro and BigQuery contracts | Contract validator | 23 input leaves plus 4 system fields equal 27 fields |
| Deconstruction of Compliance into Yes or No | Six-rule library | Manual serializer demonstration and tests | Six Yes results for valid input; exact rule identifiers for invalid input |
| Exact Django REST Framework validation | Model serializer and database constraints | Valid, wrong-type, unknown-field, limit, and cross-field tests | Valid accepted; every invalid class rejected |
| Maximum 15 slides | Generated presentation | Render or inspect slide count | 13 slides |
| Workbook Wrap Text and full forms | Artifact builder and workbook | Reopen workbook or rebuild | Every populated cell wrapped; narrative uses full forms |
| Author and contact | File headers and document metadata | Inspect representative files and Office metadata | Pritam Raha and email present |

## Final sign-off

Mark the implementation package as locally and pipeline verified only when Levels 1 and 2 pass. Mark all requirements as end-to-end verified only when Level 3 also passes in an authorised project. If Level 3 was not performed, state this honestly during the presentation: the infrastructure was provider-validated and policy-tested, but no unauthorised cloud deployment was made.
