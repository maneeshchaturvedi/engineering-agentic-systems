---
layout: doc
title: Reference Model
section: Specification
order: 2
---

# Reference Model

The reference model is the vocabulary every other part of the specification is written in. Controls are stated as properties of these entities; the [manifest](manifest.html) declares them; the [telemetry conventions](telemetry.html) observe them; and each [stack profile]({{ '/profiles/' | relative_url }}) maps them onto a framework's native concepts.

The model is deliberately small. An entity is included only if at least one control depends on it.

## Layers

Following [Principle 2]({{ '/essays/02-separate-reasoning-from-execution.html' | relative_url }}), every agentic system is described as five layers, each with a responsibility and a list of things it must not do.

| Layer | Responsibility | Must not |
|---|---|---|
| **Reasoning** | Interpret input, plan, choose the next capability, draft language. | Enforce permissions, track budgets, hold durable state, guarantee anything. |
| **Orchestration** | Control flow: ordering, loops, stopping, approval points, bounds. | Perform business side effects inline in control logic. |
| **State** | Durable record of progress, decisions and intermediate results. | Accept model output without validation. |
| **Tool** | Typed capabilities the model may request, each with a contract. | Trust arguments blindly; return unbounded output. |
| **Execution** | Perform side effects: idempotent, policy-checked, recorded. | Be invoked directly by the model. |

## Entities

### Workflow

A named, versioned agentic application, the unit of conformance assessment.

| Attribute | Values / meaning |
|---|---|
| `id`, `version` | Identity. Every Run is pinned to one version. |
| `rung` | Pattern on the autonomy ladder: `code`, `single_call`, `fixed_workflow`, `agent`, `multi_agent`. |
| `rung_justification` | The requirement the next rung down cannot meet. Required for `agent` and `multi_agent`. |
| `risk_tier` | `T1`, `T2` or `T3` — see [Conformance](conformance.html#risk-tiers). |
| `owner` | Accountable team. |
| `success_definition` | What a successful outcome is, in business terms. |

### Run

One execution of a Workflow version on behalf of a Principal.

| Attribute | Values / meaning |
|---|---|
| `run_id`, `workflow_version` | Identity and pinned version. |
| `principal`, `actor_chain` | On whose behalf, through which agents. See Principal. |
| `budget` | Limits on every resource dimension. See Budget. |
| `tainted` | `true` once the Run has consumed output from an untrusted source. Never reset within a Run. |
| `status` | `queued`, `running`, `waiting`, `completed`, `failed`, `stuck`, `budget_exhausted`, `cancelled`. |

### Step

One reasoning-and-action cycle, and the unit of checkpointing. A Step boundary is the point at which progress is made durable.

### ModelCall

A single request to a model. Carries model identity, input and output token counts, cost and latency. A ModelCall's result is a **Decision**.

### Decision

Structured output of the reasoning layer: either a final answer or one or more ToolRequests. A Decision, once recorded, is a fact; recovery reads it rather than recomputing it.

### Tool

A typed capability the model may request.

| Attribute | Values / meaning |
|---|---|
| `effect_class` | `none` (pure read/compute), `reversible`, `reversible_delayed` (cancellable window), `irreversible`. |
| `egress` | `true` if the Tool can communicate outside the trust boundary — send, post, call an external service, write somewhere others read, or render a URL. |
| `output_trust` | `trusted` or `untrusted`. Untrusted means any content whose author you do not control, including data in your own systems that originated outside. |
| `data_access` | `none`, `private` (customer or internal data), `regulated` (personal, financial or health data under legal obligation). |
| `idempotency` | For effectful Tools: `native_key`, `upsert`, or `none` (requires reconciliation). |
| `output_limit_tokens` | Maximum output size returned to the model. |
| `required_scopes` | Permissions the Run's credential must carry. |
| `approval` | `none`, `policy` (automatic gate), `human`. |
| `source` | `first_party`, `third_party`, or `mcp` with server identity and a pinned description hash. |

Tool attributes are the foundation of assessment: lessons 3, 4, 6 and 7 are all expressed as rules over them.

### ToolRequest

A Decision's structured request to invoke a Tool. A ToolRequest is data; it has no effect until it passes the policy gate.

### PolicyDecision

The deterministic outcome of evaluating a ToolRequest or outbound content against policy: `allow`, `deny` or `escalate`, with the identifier of the rule that produced it.

### ActionIntent

The durable record of a side effect the system has decided to perform.

| Attribute | Values / meaning |
|---|---|
| `intent_id` | Identity. |
| `idempotency_key` | Derived from logical purpose — tenant, Run, action type, target, sequence position — never from generated content. |
| `state` | `proposed` → `approved` / `rejected` → `executing` → `executed` / `failed` → `reconciled`. |
| `compensation` | For reversible effects, the compensating action. |
| `external_ref` | The target system's identifier for the effect (message ID, refund ID). |

### Principal and Credential

The **Principal** is the user or named service principal on whose behalf a Run acts, within a **tenant**. The **Credential** is minted per Run: it carries the principal as subject, the agent as actor, the scopes the Workflow requires, and a short expiry. Delegation to a sub-agent appends to the **actor chain** and may only narrow scope.

### Budget

Limits on each resource dimension of a Run: `steps`, `tokens`, `wall_time_s`, `cost_usd`, `tool_calls` (per Tool), `tool_output_tokens` (per Tool), `concurrency`, and `retries`.

### ContextItem

A unit of information placed in the model's context.

| Attribute | Values / meaning |
|---|---|
| `kind` | `static` (instructions, policies, tool definitions), `slow` (precomputed snapshots), `fresh` (direct lookups), `unstructured` (retrieved passages), `analytical` (bounded, often asynchronous aggregations). |
| `as_of` | When the fact was true. |
| `trust` | `trusted` or `untrusted`. |
| `tokens`, `truncated` | Size, and whether the item is explicitly partial. |

### Checkpoint

Durable state of a Run at a Step boundary, tagged with the Workflow version that produced it.

### MemoryEntry

Information persisted across Runs, with provenance: the writing Run, the source, and the source's trust.

### Trace

Telemetry for a Run, structured as a tree: Run → Step → ModelCall / ToolCall, using the [telemetry conventions](telemetry.html). A Trace is a copy of customer data and is governed as such.

### EvalSuite

A versioned dataset and set of metrics used to gate change, with a stated **minimum detectable effect** and calibrated judges.

### OutcomeEvent

A business outcome (reply received, ticket reopened, meeting booked) emitted by the system where it happens and joined to Runs by entity within an attribution window.

### Change

Any modification that can alter agent behaviour: prompt, model, tool description, retrieval configuration, workflow code, policy, or eval dataset. Every Change is subject to [evidence gates](controls/evidence-gated-change.html).

## Planes

Beyond the five layers, several concerns cut across every Workflow. The [reference architecture]({{ '/blueprint/' | relative_url }}) realises each as one or more components.

| Plane | Concern |
|---|---|
| **Policy** | Deterministic evaluation of ToolRequests and outputs. |
| **Identity** | Delegated credentials, scope narrowing, data-layer enforcement. |
| **Capacity** | Budgets, quotas, admission, retries, degradation. |
| **Observability** | Traces, metrics, redaction, retention, deletion. |
| **Evidence** | Evaluation, release gates, outcome measurement. |
