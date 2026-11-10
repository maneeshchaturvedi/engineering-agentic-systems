---
layout: doc
title: Assessment Method
section: Assessment
order: 0
---

# Assessment Method

An EAS assessment answers a practical question about a Workflow: *which controls does it meet, which does it not, and what exactly must change?* The output is a [report](report.html) of findings, each with evidence and a remediation: a patch for local findings, a plan against the [reference architecture]({{ '/blueprint/' | relative_url }}) for structural ones.

The method is the same whether a person, a script or an LLM-based agent performs it. An automated assessor is a measuring instrument like any other, and is held to the same standard as the essays hold an LLM judge: see [Calibrating an automated assessor](#calibrating-an-automated-assessor).

## Phases

### 1. Scope

Identify the Workflows, their versions and their stack. Load the [manifest]({{ '/spec/manifest.html' | relative_url }}) if one exists; if not, the first deliverable of the assessment is a draft manifest inferred from the code, for the owning team to correct.

Load the stack's [profile]({{ '/profiles/' | relative_url }}). The profile says where each hook binds, which framework defaults are bounded, and which pitfalls to look for.

### 2. Inventory

Build the **Tool inventory**: every capability reachable by the model in a Run, including sub-agents, handoff targets, hosted or provider-side tools, and third-party (e.g. MCP) servers. Classify each Tool's `effect_class`, `egress`, `output_trust` and `data_access` *from its implementation*, not only from its description.

Compare with the declared inventory. Every difference is a finding: an undeclared Tool, a Tool declared `none` that performs a write, a Tool declared `trusted` that returns content authored outside.

Derive the **minimum risk tier** from the inventory and compare it with the declared tier ([Conformance]({{ '/spec/conformance.html#risk-tiers' | relative_url }})). The required level follows from the higher of the two.

This phase matters more than any other. Four control domains are rules over Tool attributes, so an error in the inventory spreads to every later phase.

### 3. Evidence collection

For each control in scope (by level and applicability), gather evidence of every kind the control defines:

| Kind | How |
|---|---|
| Declared | Read the manifest fields named in the control. |
| Static | Search code and configuration using the control's static evidence and the profile's signals. Record what was searched as well as what was found. |
| Runtime | Evaluate the control's runtime assertion over a trace sample using the [telemetry conventions]({{ '/spec/telemetry.html' | relative_url }}). Record the sample (time window, Run count) and any violating span IDs. |
| Attested | Put the control's question to the owning team (see the [questionnaire](questionnaire.html)) and record the answer, the respondent and the linked artefact. |

### 4. Evaluation

Assign each control a [verdict]({{ '/spec/conformance.html#verdicts' | relative_url }}) by the evidence rules: declared evidence alone never establishes L2 or above; stronger evidence governs; absence of evidence is `unknown`, not `not_met`.

Record **drift** wherever kinds of evidence disagree: declared against static, static against runtime. Drift findings are often the most valuable output, because they show where a team believes it is protected and is not.

### 5. Verification

Before a finding is reported, it must survive an attempt to refute it:

- Is there enforcement the search missed — in a platform component, a base class, a decorator, configuration loaded at runtime, an infrastructure policy?
- Does the applicability condition actually hold?
- Is the evidence cited specific (file and line, span ID, manifest path) and does it say what the finding claims?

A finding that cannot cite specific evidence is downgraded to `unknown` with a note on what would settle it.

### 6. Remediation and reporting

For each finding with verdict `not_met` or `partial`:

- **Local** remediation (the control's `remediation.scope`): produce a concrete patch against the code or configuration, following the control's guidance and the profile's idiom for the framework. Patches must be minimal and must not change behaviour beyond the control's requirement.
- **Structural** remediation: produce a plan that names the target [blueprint]({{ '/blueprint/' | relative_url }}) components, the files and modules affected, a migration sequence, and the evidence that will show the control is met afterwards. Do not generate large architectural patches; an action ledger or durable-execution migration is a design decision for the team.

Rank findings by severity: a control's level relative to the required level, then whether the gap is on a path with irreversible or external effects, then breadth (how many Tools or Runs it affects).

## Calibrating an automated assessor

Automating this method — static analysis, trace queries and LLM-based code reading — is the natural next step, and the specification is designed to make it possible: the [catalog]({{ '/spec/controls/catalog.json' | relative_url }}) is machine-readable, evidence is stated per control, and verdict rules are explicit.

But an automated assessor that uses a model to read code is itself an LLM judge, and [Principle 10]({{ '/essays/10-evidence-gated-change.html#judges-calibrated' | relative_url }}) applies to it. Before its findings are trusted:

1. Build a **seeded corpus**: small Workflows in each supported stack with known, labelled violations and known-clean counterparts, covering every L1 control.
2. Measure **precision and recall per control** against the labels, and publish them with the assessor's version. A control with poor recall should be reported as `unknown` rather than `met` when the assessor finds nothing.
3. **Prefer deterministic checks** wherever a control allows it — manifest validation, configuration parsing, trace assertions — and use model judgement only for what code cannot decide, such as matching prompt rules to their enforcement ([EAS-04.01]({{ '/spec/controls/enforcement.html#eas-04-01' | relative_url }})).
4. **Recalibrate** whenever the assessor's model, prompts or the catalog change.
