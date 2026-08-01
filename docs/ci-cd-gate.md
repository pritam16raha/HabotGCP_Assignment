# Fail-closed build gate

Author: Pritam Raha  
Contact: rahapritam32@gmail.com

## Gate order

1. The runner checks out full history without persisting the GitHub token.
2. The standard-library scanner executes before any repository dependency or application code.
3. The runner installs only version-pinned validation dependencies.
4. Dependency audit, formatting, linting, secure-code checks, application checks, tests, and schema checks run sequentially.
5. Terraform formatting, provider validation, mocked plan tests, and Checkov policy checks run sequentially.
6. Any non-zero result fails the job. A failure-only step records the commit and run URL, then uploads reports as a quarantined artifact.
7. The release-authorisation job has `needs: quality-security-gate`; GitHub cannot schedule it after any gate failure.

The workflow has read-only repository permission, no cloud credential, no secret interpolation, a 20-minute timeout, and concurrency cancellation. This limits both token exposure and duplicate cost.

## Why the gate is mistake-proof

| Mistake | Automated prevention |
|---|---|
| Developer embeds a recognised provider credential | Exact provider-pattern rule fails before application code runs |
| Developer assigns a literal to a credential-shaped name | Generic assignment rule fails and redacts evidence |
| Developer attempts a long random password literal | High-entropy credential rule fails |
| Developer sends `"yes"` instead of JSON `true` | Strict BooleanField rejects it |
| Developer adds an unmapped form field | Closed serializer rejects it and contract cardinality test fails |
| Developer changes Avro without BigQuery | Type, mode, order, or count comparison fails |
| Developer formats code locally but not Terraform | Independent format checks fail |
| Developer weakens storage or encryption | Checkov or native Terraform assertions fail |

## Demonstration

Run:

```bash
make demo-fail-closed
```

The script composes a credential-shaped assignment at runtime inside a temporary directory. The scanner returns a finding and the demonstration passes only when that insecure input is blocked. This proves the negative path while keeping the repository itself clean.

To demonstrate in GitHub without contaminating the main branch:

1. Create a temporary branch.
2. Add a file containing a literal assigned to a credential-shaped field.
3. Open a pull request and show the failed first security step.
4. Show that `release-authorisation` is skipped and the quarantine artifact exists.
5. Close the pull request and delete the temporary branch.

Never use a real credential in the demonstration.

