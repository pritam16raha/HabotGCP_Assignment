# Staging deployment runbook

Author: Pritam Raha  
Contact: rahapritam32@gmail.com

## Preconditions

- An existing billed Google Cloud project owned by the deploying organisation.
- An operator authenticated with permission to enable services, administer the listed resources, create service identities, and manage project policy.
- Google Cloud command-line interface and Terraform 1.14 or later.
- A reviewed successful commit on the main branch.

## One-time remote state bootstrap

Terraform cannot create the bucket that stores its own initial state. An authorised platform administrator performs this once:

```bash
export TF_VAR_project_id="habot-staging-pritam-raha-2026"
export TF_STATE_BUCKET="${TF_VAR_project_id}-terraform-state"
gcloud storage buckets create "gs://${TF_STATE_BUCKET}" \
  --project="${TF_VAR_project_id}" \
  --location="ME-CENTRAL1" \
  --uniform-bucket-level-access \
  --public-access-prevention
gcloud storage buckets update "gs://${TF_STATE_BUCKET}" --versioning
```

Restrict bucket administration to the infrastructure automation identity and the minimum break-glass group defined by the employer. Do not grant public or all-authenticated access.

## Plan

```bash
gcloud auth application-default login
terraform -chdir=infrastructure init -backend-config="bucket=${TF_STATE_BUCKET}"
terraform -chdir=infrastructure fmt -check -recursive
terraform -chdir=infrastructure validate
terraform -chdir=infrastructure test
terraform -chdir=infrastructure plan -out=staging.tfplan
terraform -chdir=infrastructure show staging.tfplan
```

Review the exact project, region, Identity and Access Management grants, encryption keys, retention, deletion protection, and row predicates before approval.

## Apply

```bash
terraform -chdir=infrastructure apply staging.tfplan
terraform -chdir=infrastructure output
```

No service-account key file is created. Workloads use service-account impersonation or Workload Identity Federation configured by the owning organisation.

## Post-deployment verification

1. Attempt unauthenticated bucket access; expect denial.
2. Upload under `incoming/` as the raw ingestor; expect success.
3. Attempt upload outside `incoming/`; expect denial.
4. Attempt overwrite and delete as the raw ingestor; expect denial.
5. Publish one schema-valid canonical event; expect one D1 row.
6. Publish a message with an unknown or mistyped field; expect Pub/Sub rejection.
7. Query as the Dubai analytics identity after inserting rows for two emirates; expect Dubai rows only.
8. Review the access-log object and Cloud Audit Logs.
9. Run `terraform plan`; expect no drift.

## Recovery and rollback

- Application rollback uses the previous immutable release commit, not an unreviewed patch.
- Schema changes are additive by default and use a new schema version for breaking changes.
- A failed subscription delivery retains the message for seven days; the immutable D0 generation remains the replay source.
- Object versions and soft deletion support raw recovery. BigQuery time travel supports staged recovery.
- Key and table destruction are deliberately blocked. Their removal requires a separately reviewed lifecycle change and recovery plan.

