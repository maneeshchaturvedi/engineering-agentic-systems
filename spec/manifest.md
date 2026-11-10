---
layout: doc
title: Agent Manifest
section: Specification
order: 4
---

# Agent Manifest

The agent manifest is a declarative, framework-neutral description of one or more Workflows. It is the *declared* evidence in an assessment, and writing it is useful even before any assessment: it forces decisions that are usually implicit to be made explicit. Which Tools have effects? Which return untrusted content? Who does the agent act for? What are its limits? Which rules are enforced where?

- **Schema:** [`eas-manifest.schema.json`]({{ '/schemas/eas-manifest.schema.json' | relative_url }}) (JSON Schema 2020-12; manifests may be written in YAML or JSON).
- **Conventional location:** `eas.yaml` at the repository root, or `<workflow>.eas.yaml` beside each Workflow's entry point.
- **Example:** [`support-refunds.eas.yaml`]({{ '/schemas/examples/support-refunds.eas.yaml' | relative_url }}), the refund-capable support agent from [Principle 2]({{ '/essays/02-separate-reasoning-from-execution.html' | relative_url }}#what-it-looks-like-in-practice).

## Structure

| Section | Declares | Primary controls |
|---|---|---|
| `rung`, `rung_justification`, `agents[]` | Where the Workflow sits on the autonomy ladder, and why. | [EAS-01](controls/pattern-selection.html) |
| `risk_tier`, `target_level` | The tier, and therefore the [required level](conformance.html#risk-tiers). | [Conformance](conformance.html) |
| `principal` | On whose behalf Runs act, with which scopes and credential lifetime. | [EAS-06](controls/identity.html) |
| `budgets` | Limits on every resource dimension; the owner of retries. | [EAS-05](controls/bounds.html) |
| `tools[]` | Every Tool's effect class, egress, output trust, data access, idempotency, output limit, scopes, approval and source. | [EAS-02](controls/separation.html), [EAS-03](controls/actions.html), [EAS-07](controls/untrusted-content.html) |
| `policies[]` | Every business rule, its category, and *where it is enforced*. | [EAS-04](controls/enforcement.html) |
| `context.sources[]` | Each context source's kind, trust and freshness SLA. | [EAS-08](controls/context.html) |
| `state` | Checkpointer, durability mode, version strategy. | [EAS-09](controls/durable-state.html) |
| `memory` | Whether long-term memory exists and how untrusted content is handled. | [EAS-07.07](controls/untrusted-content.html#eas-07-07) |
| `observability` | Exporter, redaction, payload capture, retention. | [EAS-12](controls/observability.html) |
| `evaluation` | Suite, dataset version, minimum detectable effect, gates, kill switch. | [EAS-10](controls/evidence-gated-change.html) |
| `success_definition`, `baseline` | What success is and what the Workflow is compared against. | [EAS-11](controls/baseline.html) |
| `exceptions[]` | Accepted risks, with owner and expiry. | [Conformance](conformance.html#verdicts) |
| `platform.components[]` | Platform components the Workflows inherit controls from. | [Inheritance](conformance.html#inheritance) |

## The Tool inventory is the foundation

Most of the assessment depends on the `tools[]` section being correct. Four attributes carry most of the weight:

```yaml
- name: reply_to_customer
  effect_class: irreversible   # none | reversible | reversible_delayed | irreversible
  egress: true                 # can communicate outside the trust boundary
  output_trust: trusted        # does its output contain content whose author you don't control?
  data_access: private         # none | private | regulated
```

From these, an assessor derives the minimum risk tier, finds every Run that combines private data, untrusted content and external communication ([EAS-07.02](controls/untrusted-content.html#eas-07-02)), identifies which Tools need an action ledger ([EAS-03](controls/actions.html)), and checks least privilege ([EAS-07.04](controls/untrusted-content.html#eas-07-04)). An assessor also checks the inventory against the code: a Tool present in code but missing from the manifest, or one whose implementation contradicts its declared classes (for example a `none`-effect Tool that issues an HTTP POST), is a finding.

## Policies declare where they are enforced

```yaml
- id: refund-auto-threshold
  description: Refunds above 100 USD require human approval.
  category: money
  enforced_at: [prompt, gateway]
  code_ref: policies/refunds.rego
  tests_ref: policies/refunds_test.rego
```

A policy in the `privacy`, `money`, `legal` or `safety` category whose `enforced_at` contains only `prompt` is a direct violation of [EAS-04.01](controls/enforcement.html#eas-04-01). Declaring this is often the moment a team discovers it.
