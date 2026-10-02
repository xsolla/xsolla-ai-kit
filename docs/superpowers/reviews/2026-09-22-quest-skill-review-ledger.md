# Quest skill review ledger

Date: 2026-09-22  
Repository: `/Users/raufaliyev/GolandProjects/xsolla-ai-kit`  
Review target: `QP-2890-verification`, `028028f`

## Evidence boundary

- Canonical `skills/quest-setup` and `.cursor/skills/quest-setup` were reviewed
  independently and compared byte-for-byte.
- The skill was compared with the design specification and implementation plan.
- Runtime claims were spot-checked against local `adtech` source and read-only
  stage OpenAPI/qp-data responses.
- No qp-server CRUD write, event submission, activation, webhook delivery,
  wallet lookup, or settlement check was performed.
- The stage fixture returned historical evidence from 2026-08-24. It is not
  evidence of a new event run in this review.

## Findings and disposition

| Severity | Finding | Evidence | Disposition |
|---|---|---|---|
| P1 | Basic auth wording claimed every qp-server call returns 401 and did not separate service preflight. | `SKILL.md`, `auth-and-environment.md` | Fixed. The claim is scoped to the Basic CRUD lane; OpenAPI discovery, qp-server writes, event submission, and qp-data read-back now have separate boundaries. |
| P1 | Activation safety covered rewards but not repeat behavior or outbound actions. | `SKILL.md`, `quest-document.md`, `node-subtypes.md` | Fixed. Activation now requires an action-impact preview, explicit no-limit acknowledgement, and approved endpoints/fixtures for outbound actions. |
| P1 | `webshop_personalization` was described as an accepted action without its current runtime no-op behavior. | `node-subtypes.md`; local worker `Node.GetActivity()` | Fixed. It is documented as configuration-accepted but routed to `SkipExecution`, not runtime personalization. |
| P1 | Structural graph validation did not prove a usable trigger-to-action path. | `SKILL.md`, `quest-document.md` | Fixed as an agent preflight rule. The skill now checks intended reachability and orphan nodes in addition to server reference/cycle validation. |
| P1 | Condition documentation omitted runtime identity, attribute, event-history, and week-boundary prerequisites. | `conditions.md`; local worker condition activity | Fixed. Runtime prerequisites and unknown calendar semantics are explicit. |
| P2 | Verification said to retry reads but did not bound polling. | `verification.md` | Fixed with a client-side maximum of six reads over 60 seconds and a final `unverified`/`result unknown` rule. |
| P2 | `includeEventBody` could expose identifiers and arbitrary properties. | `verification.md`, `events.md` | Fixed. Read only when necessary and redact identifiers, emails, and secret-like properties. |
| P2 | Web3 example looked executable and approved. | `rewards.md` | Fixed. `XLA-000-001` and `0.01` are illustrative only; owner approval and project/SKU/recipient verification are required. |
| P2 | `inventory_item` omitted supported single-item and metadata forms. | `rewards.md`; local `InventoryItemBody` | Fixed. Both forms and runtime defaults are documented. |
| P2 | Mirror validator checked source-to-mirror but not stale mirror-only files. | `.github/scripts/validate_skills.py` | Fixed with reverse mirror file checks. |
| P2 | Registry parser and anchor checker are permissive. | `.github/scripts/validate_skills.py` | Deferred. Useful hardening, but not required to make this skill's current content safe or usable. |

## Residual unknowns

- Stage deployment revisions for qp-server, event collector, and worker are not
  pinned in the skill.
- QP-2862 Basic credential lane is still not accepted, and owner approval for
  the `quests` domain and internal host disclosure remains external work.
- No owner-approved reward, webhook, or notification fixture was available for
  a stage write test.
- The review does not prove ERC-20 settlement, wallet balances, transaction
  hashes, or Backpack visibility.

## Review agents

Four bounded read-only reviews covered contract fidelity, agent usability,
canonical/mirror consistency, and unsafe or unverifiable claims. Their findings
were consolidated here; no subagent edited the repository.
