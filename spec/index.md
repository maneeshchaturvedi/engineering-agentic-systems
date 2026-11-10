---
layout: doc
title: EAS Specification
section: Specification
order: 0
---

# The EAS Specification

The **Engineering Agentic Systems (EAS) specification** turns the principles of the [essay series]({{ '/essays/' | relative_url }}) into testable controls that any agentic stack can adopt, implement and be assessed against. It is framework-neutral: it defines what must be true of a well-engineered agentic system and how to collect evidence of it, and leaves *how* to each stack.

The design stance is the one the essays argue for: **the model proposes; a deterministic system disposes.** Every control is some version of putting a guarantee in ordinary, testable code around the model, rather than in the model's reasoning.

<p class="status">Version {{ site.spec_version }} · Draft for comment. Control identifiers are stable within a minor version.</p>

## How the specification is organised

| Part | Status | What it defines |
|---|---|---|
| [Conformance](conformance.html) | Normative | Levels (L1–L3), risk tiers, evidence rules, verdicts, conformance claims. |
| [Reference model](reference-model.html) | Normative | The vocabulary: layers, entities and their attributes. |
| [Controls](controls/) | Normative | Testable requirements, one domain per principle. |
| [Agent manifest](manifest.html) | Normative | A declarative description of a Workflow. This is the *declared* evidence. |
| [Telemetry conventions](telemetry.html) | Normative | OpenTelemetry attributes that make *runtime* evidence possible. |
| [Hook contract](hooks.html) | Normative | Interception points a stack must expose for controls to be enforced outside the model. |
| [Stack profiles]({{ '/profiles/' | relative_url }}) | Informative | How the reference model and hooks map onto specific frameworks. |
| [Reference architecture]({{ '/blueprint/' | relative_url }}) | Informative | A blueprint of components that satisfy the controls, for vendors and platform teams to implement. |
| [Assessment method]({{ '/assessment/' | relative_url }}) | Informative | How to assess a Workflow and report findings with concrete remediation. |

## How a stack integrates

The specification is designed to be adopted incrementally into an existing stack. Nothing in it requires replacing an agent framework.

1. **Declare.** Write an [agent manifest](manifest.html) for each Workflow: its rung, risk tier, Tools and their effect and trust classes, budgets and policies. This alone surfaces most L1 gaps, because it forces implicit decisions to be made explicit.
2. **Bind.** Use your stack's [profile]({{ '/profiles/' | relative_url }}) to bind the [hook contract](hooks.html) to the framework's native interception points. The `tool.before` hook is the most important one.
3. **Instrument.** Add the [telemetry attributes](telemetry.html) to existing OpenTelemetry instrumentation.
4. **Assess.** Run an [assessment]({{ '/assessment/' | relative_url }}) to compare what is declared, what is built and what the traces show, and to get findings with remediation.
5. **Gate.** Re-run the assessment in CI on every Change, and block releases that fall below the required level.

## Normative language

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY and OPTIONAL are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) and [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174) when, and only when, they appear in capitals.

## Versioning

The specification uses semantic versioning. Within a minor version, control identifiers are stable and requirements are only clarified. A new minor version may add controls or raise a control's level. A major version may remove or renumber controls. Essays and the specification are versioned together in the same repository: when an essay's argument changes, the controls derived from it are revised in the same release.
