---
layout: doc
title: Conformance
section: Specification
order: 1
---

# Conformance

This page defines what it means for a Workflow to conform to the EAS specification: the levels, how risk determines the level required, what counts as evidence, and how a conformance claim is made.

## Levels

Every control is assigned the lowest level at which it is required. A Workflow conforms at a level when every applicable control at that level and below is `met`.

| Level | Name | Intended for | Character |
|---|---|---|---|
| **L1** | Baseline | Any agent in production. | Achievable mostly through configuration and small code changes within the existing design: bounds, tool contracts, identity not taken from model arguments, prompt rules backed by code, a kill switch. |
| **L2** | Governed | Workflows that take consequential actions or handle private data. | Requires the deterministic machinery around the model: action ledger, policy gate, taint, delegated credentials, durable state, evaluation gates, redaction. |
| **L3** | Assured | High-stakes Workflows and shared platforms. | Enforcement at the lowest layer, statistical rigour in evaluation, verified deletion, fault-injection testing, measured lift. |

## Risk tiers

The level a Workflow *must* reach is set by its risk tier. The tier is declared in the [manifest](manifest.html) and checked against a minimum derived from the Tool inventory; an assessor reports a declared tier below the derived minimum as a finding.

| Tier | Derived when | Required level |
|---|---|---|
| **T1** Assistive | Every Tool has `effect_class: none` and `egress: false`, and outputs are reviewed by a person before use. | L1 |
| **T2** Consequential | Any Tool has `effect_class` other than `none`, or `egress: true`; or the Workflow combines `data_access: private` with any `output_trust: untrusted` source. | L2 |
| **T3** High-stakes | Any Tool is `irreversible` and either `egress: true` or moves money; or any Tool has `data_access: regulated`; or the system is a shared platform serving multiple Workflows or tenants. | L3 |

This follows the essays' guidance that controls should be applied by risk tier: a read-only research agent can plan adaptively, while an agent that sends messages, changes records or moves money gets the constrained patterns.

## Applicability

Each control states the condition under which it applies. A control whose condition does not hold is `not_applicable`, and the assessor records why. For example, a Workflow at rung `fixed_workflow` makes loop-detection controls not applicable, and a Workflow with no effectful Tools makes the action-ledger controls not applicable.

## Evidence

Four kinds of evidence can establish a control, in increasing order of strength:

| Kind | Source | Establishes |
|---|---|---|
| **Attested** | A named owner's answer to the control's question, with a link to an artefact (runbook, CI configuration, dashboard). | That a process exists. |
| **Declared** | The [agent manifest](manifest.html). | What the team intends. |
| **Static** | Code and configuration, read by a person or tool. | What the system is built to do. |
| **Runtime** | Traces using the [telemetry conventions](telemetry.html). | What the system actually did. |

Rules:

1. **Declared evidence alone never establishes a control at L2 or above.** A manifest is a claim; it must be corroborated by static or runtime evidence.
2. **At L3, where a control defines runtime evidence, runtime evidence is required.**
3. **When evidence disagrees, the stronger evidence governs, and the disagreement is itself a finding.** A manifest that declares a Tool approval-gated, while traces show it executing without approval, yields a `not_met` verdict plus a drift finding. These disagreements are often the most valuable output of an assessment.
4. **Absence of evidence is `unknown`, not `not_met`.** "No step limit found in the scanned code" is reported as `unknown` with the search performed, unless the scan is known to be complete (for example, the profile confirms the framework default is unbounded and no override exists).

## Verdicts

| Verdict | Meaning |
|---|---|
| `met` | Sufficient evidence for the control's level; no contrary evidence. |
| `partial` | Satisfied on some paths only (e.g. some Tools, the parent agent but not sub-agents). |
| `not_met` | Evidence shows the requirement is not satisfied. |
| `not_applicable` | The control's applicability condition does not hold. |
| `unknown` | Evidence was insufficient to decide. |
| `excepted` | Not met, with a recorded risk acceptance: owner, reason, compensating control, expiry date. |

## Inheritance

Many controls are best satisfied once by a platform rather than by every Workflow — a model gateway owns retries and quotas, an identity broker mints credentials, a telemetry pipeline redacts. A Workflow MAY **inherit** a control from a platform component if:

- the platform component has itself been assessed against that control, and
- the Workflow demonstrably routes through it (static evidence) and the component's telemetry shows the Workflow's traffic (runtime evidence, where defined).

The [reference architecture]({{ '/blueprint/' | relative_url }}) lists which components can satisfy which controls. Vendors implementing those components can publish the controls they satisfy, so that adopters inherit them.

## Conformance claims

A claim names the specification version, the Workflow and version, the level, and the date, and lists any exceptions:

> *Workflow `support-refunds` v14 conforms to EAS 0.1 at **L2** (risk tier T2), assessed 2026-11-10. Exceptions: EAS-09.04 (expires 2027-01-31).*

A claim is valid for the assessed Workflow version only. Any [Change](reference-model.html#change) produces a new version and requires the assessment to be re-run, which in practice means running it in CI (see [EAS-10.07](controls/evidence-gated-change.html#eas-10-07)).
