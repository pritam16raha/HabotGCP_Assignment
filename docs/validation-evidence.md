# Validation evidence

Author: Pritam Raha  
Contact: rahapritam32@gmail.com  
Evidence captured: 1 August 2026

| Check | Result |
|---|---|
| Ruff format and lint | Passed |
| Bandit Python security scan | Passed with zero findings |
| Python dependency vulnerability audit | Passed with no known vulnerabilities |
| Django model migration consistency | Passed; no changes detected |
| Django serializer, persistence, and mapping tests | Passed: 13 |
| Independent secret-scanner tests | Passed: 2 |
| Contract comparison | Passed: 23 source leaves plus 4 system fields equal 27 Pub/Sub and BigQuery fields |
| Repository credential scan | Passed: zero findings |
| Synthetic fail-closed demonstration | Passed: insecure temporary input generated one blocking finding |
| Terraform format | Passed |
| Terraform provider validation | Passed with Google and Google Beta provider 7.42.0 |
| Terraform mocked plan test | Passed: 1 |
| Checkov infrastructure security scan | Passed: 41; failed: 0; documented terminal-log-bucket skip: 1 |

These local results are reproducible with `make validate` and do not require cloud access. A separate live `terraform apply` was subsequently performed in the author's authorised, isolated staging project; no employer-owned project was used or modified. The cloud results are recorded in [deployment-evidence.md](deployment-evidence.md).
