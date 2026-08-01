# Deconstruction of Compliance into Yes or No data contract

Author: Pritam Raha  
Contact: rahapritam32@gmail.com

The library turns each judgement into one executable question with only `YES` or `NO` output. Acceptance is the logical conjunction of all six results. A single `NO` rejects the request; all failed identifiers are returned so correction is objective.

| Rule | Binary question | Yes condition | No action |
|---|---|---|---|
| DCYN-001 | Did the guardian explicitly consent to processing? | Value is the JSON boolean `true` | Reject |
| DCYN-002 | Was consent recorded no more than 30 days before submission? | Consent is between submission minus 30 days and submission | Reject |
| DCYN-003 | Is the student between 3 and 21 years old on the submission date? | Completed age is within the inclusive range | Reject |
| DCYN-004 | Do support details exactly match the support decision? | Yes means one to eight areas and 1 to 40 hours; No means empty areas and zero hours | Reject |
| DCYN-005 | Do diagnosis codes exactly match the diagnosis decision? | Yes means one to ten codes; No means an empty list | Reject |
| DCYN-006 | Does each controlled list contain unique values only? | Both lists contain no duplicate | Reject |

## Entry contract

- The top-level object contains exactly seven fields.
- Nested objects are closed; unknown fields fail.
- Booleans accept JSON `true` or `false` only. Strings and integers fail.
- Enumerations are case-sensitive controlled codes.
- Timestamps require an offset and are normalised to Coordinated Universal Time.
- Submission time is no more than 24 hours old and no more than five minutes in the future.
- Person names contain letters separated only by a space, apostrophe, period, or hyphen.
- Free text rejects control characters.

Every field limit, target type, and rejection rule is in the wrapped worksheet `submission/Pritam_Raha_Schema_Mapping.xlsx`.

## Exit contract and losslessness

The validated payload has 23 source leaves. `SOURCE_TO_CANONICAL_FIELDS` maps every leaf to one unique destination. The system adds four explicit fields:

- `dcyn_all_rules_passed`
- `dcyn_failed_rule_ids`
- `ingested_at`
- `source_object_uri`

The result has exactly 27 fields. The contract check compares those fields, in order, across Python mapping, Avro, and BigQuery. Unknown-field dropping is disabled at the BigQuery subscription. This makes schema mismatch observable instead of lossy.

