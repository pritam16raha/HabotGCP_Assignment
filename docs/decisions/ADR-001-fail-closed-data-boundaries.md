# Architecture Decision Record 001: Fail-closed data boundaries

Author: Pritam Raha  
Contact: rahapritam32@gmail.com  
Status: Accepted  
Date: 1 August 2026

## Context

The incident combines two failures: a source credential escaped into application code, and a transactional schema change broke analytics. Both failures occurred because a permissive boundary allowed uncertain input to continue.

## Decision

Every boundary uses an allow-list and rejects uncertainty:

- repository content must pass credential, format, dependency, code, infrastructure, and contract checks;
- request objects are closed and use strict types;
- business conditions are atomic Yes or No rules;
- raw writers can create only below one prefix;
- events must match Avro before publication;
- BigQuery unknown-field dropping is disabled;
- analytics access requires both a dataset role and a row predicate;
- release authorisation depends on the complete gate.

## Consequences

Invalid changes fail earlier and produce specific evidence. Clients must coordinate breaking schema changes, and operators must deliberately approve protected-resource deletion. These costs are accepted because silent loss, unauthorised access, and accidental deployment are higher risks.
