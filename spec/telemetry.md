---
layout: doc
title: Telemetry Conventions
section: Specification
order: 5
---

# Telemetry Conventions

Runtime evidence is the strongest evidence a conformance assessment can use: it shows what the system *did*, not what it was configured or declared to do. These conventions extend the [OpenTelemetry semantic conventions for generative AI](https://opentelemetry.io/docs/specs/semconv/gen-ai/) with the attributes the controls need. Stacks that already emit OpenTelemetry adopt them by adding attributes, not by replacing instrumentation.

Where an OpenTelemetry GenAI attribute already exists (`gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.tool.name`, `gen_ai.operation.name`, `gen_ai.agent.name`), it is used as-is and not duplicated. The GenAI conventions are still evolving; this page tracks them and will align names as they stabilise.

## Span tree

```
eas.run                         (root; one per Run)
├── eas.step                    (one per Step)
│   ├── chat / generate_content (ModelCall; gen_ai.operation.name)
│   ├── eas.policy              (PolicyDecision for a ToolRequest)
│   ├── execute_tool            (ToolCall)
│   ├── eas.intent              (ActionIntent commit)
│   └── eas.checkpoint          (Step boundary committed)
├── eas.wait                    (durable wait; no worker held)
└── eas.step ...
eas.execute                     (Executor performing an ActionIntent; linked to eas.intent)
```

## Attributes

### Run (`eas.run` span and propagated to children)

| Attribute | Type | Notes |
|---|---|---|
| `eas.run.id` | string | |
| `eas.workflow.id` / `eas.workflow.version` | string | Version is the pinned version, not the deployed one. |
| `eas.tenant.id` | string | |
| `eas.principal.type` | `user` \| `service` | Never the principal's personal identifiers in clear text (see [EAS-12](controls/observability.html)). |
| `eas.actor_chain` | string[] | Agent identities from the root to the current actor. |
| `eas.run.status` | enum | As defined in the [reference model](reference-model.html#run). |
| `eas.run.tainted` | boolean | Set on the span where taint first occurs and on all later spans. |
| `eas.budget.<dim>.limit` / `.used` | number | `<dim>` ∈ `steps`, `tokens`, `wall_time_s`, `cost_usd`. |
| `eas.workflow.rung` | enum | Declared rung, so rung checks need no manifest join. |
| `eas.run.mode` | enum | `live`, `shadow`, `canary`, `replay`, `fork`, `dry_run`. Only `live` and `canary` Runs may have `eas.execute` spans. |
| `eas.run.resumed` | boolean | Set on the root span when the Run has resumed from a Checkpoint at least once. |
| `eas.entity.refs` | string[] | Tokenised identifiers of the business entities the Run acted on, for outcome attribution. |
| `eas.subject.refs` | string[] | Tokenised identifiers of the data subjects whose data the Run touched, for deletion. |
| `eas.cost.tool_usd` / `eas.cost.human_review_s` | number | Cost components beyond model tokens (see [EAS-11.02](controls/baseline.html#eas-11-02)). |

### Step and Checkpoint

| Attribute | Type | Notes |
|---|---|---|
| `eas.step.index` | int | Stable across resumes: a resumed Run continues the index sequence rather than restarting it. |
| `eas.checkpoint` (span) | — | Emitted when a Step boundary is committed; child of `eas.step`. |
| `eas.checkpoint.mode` | `sync` \| `async` \| `exit` | Durability mode in effect for the commit. |
| `eas.state.validation_rejected` (event) | — | Model-derived state rejected by schema validation before a write. |

### ModelCall

| Attribute | Type | Notes |
|---|---|---|
| `eas.cost.usd` | number | Computed from the price table at call time. |
| `eas.context.tokens.<kind>` | int | Tokens per ContextItem kind (`static`, `slow`, `fresh`, `unstructured`, `analytical`). |
| `eas.context.stale_items` | int | Items whose `as_of` exceeds the freshness SLA for this decision. |
| `eas.context.cached_tokens` | int | Input tokens served from the provider's prompt cache. Will be replaced by the GenAI convention's cache attribute once stable. |
| `eas.route.escalated` | boolean | The call is an escalation in a model cascade. |

### ToolCall (`execute_tool`)

| Attribute | Type | Notes |
|---|---|---|
| `eas.tool.effect_class` | enum | `none`, `reversible`, `reversible_delayed`, `irreversible`. |
| `eas.tool.egress` | boolean | |
| `eas.tool.output_trust` | `trusted` \| `untrusted` | |
| `eas.tool.output_tokens` | int | After enforcement. |
| `eas.tool.output_truncated` | boolean | |
| `eas.tool.call_index` | int | Per-Tool count within the Run. |
| `eas.tool.args_fingerprint` | string | Hash of canonicalised arguments, for loop detection. Never the raw arguments. |
| `eas.tool.data_access` | enum | `none`, `private`, `regulated`. |
| `eas.tool.scopes_used` | string[] | Credential scopes the call exercised. |
| `eas.tool.resources` | string[] | Tokenised identifiers of the resources touched. |
| `eas.tool.results_filtered` | boolean | Permissions excluded some results, and the Tool said so ([EAS-06.08](controls/identity.html#eas-06-08)). |
| `eas.honeytoken.touched` | boolean | The call referenced a honeytoken resource ([EAS-07.10](controls/untrusted-content.html#eas-07-10)). |

### PolicyDecision (`eas.policy`)

| Attribute | Type | Notes |
|---|---|---|
| `eas.policy.decision` | `allow` \| `deny` \| `escalate` | |
| `eas.policy.rule_id` | string | The rule that produced the decision. |
| `eas.policy.point` | enum | `gateway`, `output`, `data_layer`, `network`, `memory`. |

### ActionIntent (`eas.intent`, `eas.execute`)

| Attribute | Type | Notes |
|---|---|---|
| `eas.intent.id` | string | |
| `eas.intent.key_hash` | string | Hash of the idempotency key. |
| `eas.intent.action_type` | string | Logical action, e.g. `send_followup`, `issue_refund`. |
| `eas.intent.effect_class` | enum | Effect class of the action, so ordering and gating can be checked on executor spans. |
| `eas.intent.pacing_key` | string | Tokenised account or target the executor paces against ([EAS-03.09](controls/actions.html#eas-03-09)). |
| `eas.intent.state` | enum | Lifecycle state at the time of the span. |
| `eas.intent.approval` | `none` \| `policy` \| `human` | |
| `eas.intent.external_ref_present` | boolean | Executor recorded the target system's identifier. |
| `eas.credential.minted_for` | `run` \| `intent` | On `eas.execute`: whether the effect used the Run's credential or one minted for this intent ([EAS-06.13](controls/identity.html#eas-06-13)). |
| `eas.credential.age_s` | number | On `eas.execute`: age of the credential at the moment of execution. |
| `eas.credential.id_hash` | string | Hash of the credential identifier, so reuse of a Run's credential is detectable without exposing it. |

### Payload and redaction

| Attribute | Type | Notes |
|---|---|---|
| `eas.payload.captured` | boolean | Whether prompt/response/argument payloads were retained for this span. |
| `eas.payload.capture_reason` | enum | `error`, `policy_rejection`, `escalation`, `canary`, `user_flag`, `sample`. |
| `eas.redaction.applied` | boolean | Redaction ran in-process before export. |
| `eas.redaction.policy` | string | Identifier and version of the redaction policy. |

## Runtime assertions

Controls state runtime evidence as assertions over these attributes. For example, [EAS-07.03](controls/untrusted-content.html) is evidenced by:

> No `execute_tool` span with `eas.tool.egress = true` or `eas.tool.effect_class = irreversible` and `eas.run.tainted = true` exists without a preceding `eas.policy` span whose decision is `escalate`, or an `eas.intent` span with `eas.intent.approval = human`.

An assessor evaluates such assertions over a sample of traces (by default, the last 7 days or 10,000 Runs, whichever is smaller) and reports violations with span identifiers as evidence.
