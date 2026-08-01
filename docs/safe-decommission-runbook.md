# Safe Google Cloud decommission runbook

Author: Pritam Raha  
Contact: rahapritam32@gmail.com  
Prepared: 1 August 2026

## Purpose

Use this runbook only after the recruitment and presentation process is complete. It stops further billable use and removes the assignment deployment without affecting the existing email application.

| Item | Required value |
|---|---|
| Project to decommission | `habot-staging-pritam-raha-2026` |
| Project number | `32724954916` |
| Display name | `Habot GCP Assignment` |
| Authenticated account | The account that owns the assignment project |
| Protected project that must not be changed | `outloop-email-backend` |
| Dedicated Google Cloud CLI configuration | `habot-assignment` |

## Recommended strategy

Delete the dedicated assignment project as one unit. Do not use `terraform destroy` and do not weaken KMS `prevent_destroy`, BigQuery deletion protection, row-policy deletion prevention, bucket retention, or soft deletion merely to remove individual resources.

This recommendation is safe here because the project was created only for this assignment. Google states that project shutdown stops billing and resource usage, disconnects the billing account, and enters a 30-day recovery window. Google also recommends disabling billing manually before shutdown to reduce the risk of unexpected charges. Some resources, including Cloud Storage and Pub/Sub data, can disappear earlier than the 30-day project window, so preserve evidence first.

Official references:

- [Delete and restore Google Cloud projects](https://docs.cloud.google.com/resource-manager/docs/delete-restore-projects)
- [Disable billing for one project](https://docs.cloud.google.com/billing/docs/how-to/modify-project)
- [`gcloud billing projects unlink` reference](https://docs.cloud.google.com/sdk/gcloud/reference/billing/projects/unlink)

## Safety rules

1. Never close the Cloud Billing account. It is shared with `outloop-email-backend`.
2. Never run a delete, billing, IAM, Storage, BigQuery, Pub/Sub, or KMS mutation against `outloop-email-backend`.
3. Never replace the project identifier in this document with a wildcard, variable from an unknown shell, or a project selected only by display name.
4. Verify both the project ID and project number before disabling billing.
5. Preserve the GitHub repository and final submission ZIP. They do not incur Google Cloud resource charges.
6. Do not rely on the 30-day project recovery window as a data backup.
7. Do not delete anything while the recruitment process is still active.

## Phase 1: preserve presentation evidence

Complete this phase before disabling billing. The cloud Console links and live queries will stop working after shutdown.

### 1. Record the decision

| Record | Value |
|---|---|
| Selection process completed on | ____________________ |
| Decommission approved by | ____________________ |
| Planned decommission date | ____________________ |
| Operator | ____________________ |
| Final Git commit | `9f4b953c85ada0d09e47fdc5b06b66397a97e749` or newer: ____________________ |

### 2. Preserve these files

- `submission/Pritam_Raha_Junior_Cloud_DevOps_Assignment.zip`
- `submission/SHA256SUMS.txt`
- `docs/deployment-evidence.md`
- `docs/manual-verification-guide.md`
- this runbook
- the GitHub repository and its successful Actions run

Store one copy outside Google Cloud, such as the local workstation and GitHub. Do not export or commit Application Default Credentials, access tokens, Terraform state, saved plan files, or Google Cloud CLI configuration files.

### 3. Capture final screenshots

Capture screenshots of:

1. Project dashboard showing `Habot GCP Assignment` and the project ID.
2. Raw Storage bucket protection, retention, logging, and encryption settings.
3. Pub/Sub schema-bound topic and active BigQuery subscription.
4. BigQuery table schema, partitioning, clustering, and row policies.
5. KMS key ring showing three 90-day rotating keys.
6. GitHub Actions showing both jobs green.
7. Terraform output showing `No changes`.

Use the presentation order in `docs/deployment-evidence.md`.

## Phase 2: mandatory target verification

Run these read-only commands from a terminal. Stop immediately if any expected value differs.

```bash
gcloud config configurations activate habot-assignment
gcloud config set project habot-staging-pritam-raha-2026

gcloud auth list --filter=status:ACTIVE --format='value(account)'
gcloud config get-value project
gcloud projects describe habot-staging-pritam-raha-2026 \
  --format='yaml(projectId,projectNumber,name,lifecycleState)'
gcloud billing projects describe habot-staging-pritam-raha-2026 \
  --format='yaml(projectId,billingAccountName,billingEnabled)'
```

Required output:

- Account: the account that owns the assignment project
- Project ID: `habot-staging-pritam-raha-2026`
- Project number: `32724954916`
- Name: `Habot GCP Assignment`
- Lifecycle state: `ACTIVE`
- Billing enabled: `true`

Use this additional shell guard before proceeding:

```bash
DECOMMISSION_PROJECT_ID='habot-staging-pritam-raha-2026'
DECOMMISSION_PROJECT_NUMBER='32724954916'

ACTIVE_PROJECT_ID="$(gcloud config get-value project 2>/dev/null)"
RESOLVED_PROJECT_NUMBER="$(gcloud projects describe "${DECOMMISSION_PROJECT_ID}" --format='value(projectNumber)')"

if [[ "${ACTIVE_PROJECT_ID}" != "${DECOMMISSION_PROJECT_ID}" || \
      "${RESOLVED_PROJECT_NUMBER}" != "${DECOMMISSION_PROJECT_NUMBER}" ]]; then
  echo 'STOP: project identity verification failed.'
  exit 1
fi

echo 'Target verification passed: assignment project only.'
```

Do not proceed unless the last line is printed exactly.

## Phase 3: stop billing on the assignment project

This is the first destructive step. It stops billable services in the assignment project. Previously accrued charges can still appear later because Google Cloud usage reporting is delayed.

Run without `--quiet` so the command can display errors and reauthentication prompts:

```bash
gcloud billing projects unlink habot-staging-pritam-raha-2026
```

Verify immediately:

```bash
gcloud billing projects describe habot-staging-pritam-raha-2026 \
  --format='yaml(projectId,billingAccountName,billingEnabled)'
```

Required result: `billingEnabled: false` and no active billing-account association.

If the unlink command fails, do not close the shared billing account. Use the Console method instead:

1. Open [Billing for the assignment project](https://console.cloud.google.com/billing/linkedaccount?project=habot-staging-pritam-raha-2026).
2. Confirm the selected project is `Habot GCP Assignment`.
3. Choose **Disable billing** for this project only.
4. Re-run the verification command above.

Disabling billing stops project services and might make some resources non-recoverable. That is why Phase 1 is mandatory.

## Phase 4: shut down the dedicated project

Only continue after billing is confirmed disabled.

### Preferred Console procedure

1. Open [Project settings](https://console.cloud.google.com/iam-admin/settings?project=habot-staging-pritam-raha-2026).
2. Confirm the page shows project ID `habot-staging-pritam-raha-2026` and project number `32724954916`.
3. Select **Shut down**.
4. When Google asks for confirmation, type the full project ID: `habot-staging-pritam-raha-2026`.
5. Confirm shutdown.

### Command-line alternative

The command is intentionally interactive. Do not add `--quiet`.

```bash
gcloud projects delete habot-staging-pritam-raha-2026
```

Read the displayed target, confirm it is the assignment project, and then approve the prompt.

No destructive or billing command should ever contain the protected project ID `outloop-email-backend`. If that identifier appears in a pending command, cancel it immediately.

## Phase 5: verify shutdown and billing isolation

Check the project lifecycle:

```bash
gcloud projects describe habot-staging-pritam-raha-2026 \
  --format='yaml(projectId,projectNumber,name,lifecycleState)'
```

Expected lifecycle state: `DELETE_REQUESTED`. A later `NOT_FOUND` response is normal after permanent deletion.

Check billing again:

```bash
gcloud billing projects describe habot-staging-pritam-raha-2026 \
  --format='yaml(projectId,billingAccountName,billingEnabled)'
```

Expected result: billing disabled or the project no longer available.

Finally, open the existing application and confirm it is still healthy:

- [Outloop Email Backend Cloud Run](https://console.cloud.google.com/run/overview?project=outloop-email-backend)

This is a read-only operational check. Do not change its services, billing, APIs, IAM, or project settings.

## Phase 6: monitor delayed charges

Google states that usage incurred before billing was disabled can take up to two days to appear. For at least 48 hours:

1. Open [Cloud Billing reports](https://console.cloud.google.com/billing).
2. Filter by project `habot-staging-pritam-raha-2026` only.
3. Confirm no new usage occurs after the shutdown time.
4. Record any delayed charges as pre-shutdown usage.
5. Do not close the billing account; it continues to fund the existing email project.

## Recovery within 30 days

If the project was shut down accidentally, restore it as soon as possible:

```bash
gcloud projects undelete habot-staging-pritam-raha-2026
```

After restoration, billing is not automatically re-enabled. Re-link it only if the assignment must become operational again:

```bash
gcloud billing accounts list --filter=open=true
gcloud billing projects link habot-staging-pritam-raha-2026 \
  --billing-account='<APPROVED_BILLING_ACCOUNT_ID>'
```

Then re-run the live verification guide. Google warns that some Storage and Pub/Sub resources might not recover fully and that service restoration can take time. After 30 days, project deletion is permanent and the project ID cannot be reused.

## Why `terraform destroy` is not the cleanup method

The configuration deliberately contains:

- `prevent_destroy` on three KMS keys;
- BigQuery table deletion protection;
- row-policy deletion prevention;
- retained and soft-deleted Storage objects;
- non-force-destroy buckets.

A live destroy-plan test correctly failed on the protected KMS keys. Removing these safeguards would require multiple high-risk changes and waiting for retention periods. Because every assignment resource is isolated in one dedicated project, billing disablement followed by project shutdown is simpler, safer, and easier to prove.

## Cost control before the selection process ends

Do not disable billing while a live presentation might still be required. Until then:

1. Avoid publishing more events or uploading additional objects.
2. Do not create Cloud Run, Compute Engine, Google Kubernetes Engine, Cloud SQL, or other runtime resources in this project.
3. Review Billing reports with a project filter.
4. Optionally create a budget scoped only to `habot-staging-pritam-raha-2026`.

A Google Cloud budget sends alerts but does not automatically cap usage or spending. Do not create a billing-account-wide automation because the billing account is shared with the existing application. See [Google Cloud budgets and alerts](https://docs.cloud.google.com/billing/docs/how-to/budgets).

## Final decommission record

Complete and retain this table with the submission evidence:

| Check | Recorded value |
|---|---|
| Evidence preserved | Yes / No |
| Target project ID verified | ____________________ |
| Target project number verified | ____________________ |
| Billing disabled at | ____________________ |
| Project shutdown requested at | ____________________ |
| Observed lifecycle state | ____________________ |
| Existing email application checked | Healthy / Not checked |
| 48-hour billing review completed at | ____________________ |
| Operator signature | ____________________ |
