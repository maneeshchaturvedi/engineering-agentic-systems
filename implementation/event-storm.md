---
layout: doc
title: Event Storm
section: Implementation
order: 3
---

# Event Storm

The reference architecture was first drawn top-down, from the essays. To check its boundaries bottom-up, we ran a big-picture event storm: the domain events in a Run's life, in time order, with the commands and actors that cause them and the policies ("whenever *this* happens, *that* must follow") that connect them. Where the timeline raised a design question the architecture had not answered, we marked a hotspot.

## A Run's life

| # | Actor / trigger | Command | Domain event | Policy |
|---|---|---|---|---|
| 1 | Principal | StartRun | **RunRequested** | → mint a delegated credential |
| 2 | Identity broker | MintCredential | **CredentialMinted** | → admit |
| 3 | Scheduler | Admit | **RunAdmitted** / **RunRefused** | → pin to the current Workflow version |
| 4 | Release control | — | **RunPinnedToVersion** | |
| 5 | Orchestrator | AssembleContext | **ContextAssembled** | stale input → flag or refuse |
| 6 | Orchestrator | CallModel | **ModelCallCompleted** / **QuotaExceeded** / **BudgetExhausted** | budget hit → end the Run |
| 7 | — | — | **DecisionRecorded** | must be durable before anything acts on it — H1 |
| 8 | Model, via Decision | RequestTool | **ToolRequested** | → evaluate policy |
| 9 | Policy engine | Evaluate | **ToolAllowed** / **ToolDenied** / **ToolEscalated** | denied → structured refusal to the model |
| 10 | Tool gateway | ExecuteReadTool | **ToolExecuted**, **OutputTruncated** | untrusted output → **RunTainted** — H3 |
| 11 | Tool gateway | ProposeAction | **IntentCommitted** / **DuplicateIntentRejected** | atomic with the checkpoint — H2 |
| 12 | Policy engine | — | **ApprovalRequested** | tainted or over threshold → a person |
| 13 | — | — | **RunWaiting** | no worker held |
| 14 | Reviewer | Approve / Reject | **IntentApproved** / **IntentRejected** | → resume, hand to executor — H5 |
| 15 | Executor | Execute | **EffectPerformed** / **EffectUncertain** | uncertain → reconcile — H8 |
| 16 | Executor | Compensate | **CompensationExecuted** | a later step failed on a reversible chain |
| 17 | Orchestrator | — | **LoopDetected** → **RunStuck** | → escalate |
| 18 | — | — | **RunCompleted** / **RunFailed** | → record cost components and entities |
| 19 | Telemetry | Export | **SpansExported** | redaction before any exporter — H7 |
| 20 | External system | — | **OutcomeObserved** (days later) | → attribute within the window |

**Change:** ChangeProposed → **EvalCompleted** → **GatePassed** / **GateBlocked** → **ShadowStarted** → **CanaryStarted** → **RolledBack** / **Promoted** → **OldVersionDrained**; at any point, **KillSwitchFlipped**.

**Trust and data:** **ToolDescriptionChanged** → **ServerQuarantined** → **Rereviewed**; **DeletionRequested** → **DeletionFannedOut** → **StorePurged** (per store) → **DeletionVerified**.

## Bounded contexts

The events cluster into contexts that match the blueprint's components, which is the check we wanted: Run execution; model access; tool mediation and policy; effects; identity and trust; context; observability and privacy; change and evidence; outcomes and governance. Each is a section of the [technology choices](choices.html).

## Hotspots

| | Hotspot | Resolution in this guide |
|---|---|---|
| **H1** | Two candidate owners of durable truth — the framework's checkpointer and a durable-execution engine. | Choose one per Workflow ([durable execution](choices.html#durable-execution)). |
| **H2** | Where the ledger lives: deduplication, approval and audit pull in different directions. | A relational table as the record, executed through recorded steps ([effects](choices.html#effects)). |
| **H3** | Taint and Run context crossing sub-agents and handoffs. | Part of the thin layer: no framework propagates them natively. |
| **H4** | Provider-hosted tools run inside the model call and bypass the tool gateway. | Treat as ungated; do not use them for Workflows at tier T2 or above unless an equivalent gated tool exists. |
| **H5** | A short-lived credential minted at the start of a Run expires long before a reviewer approves an intent days later. | The executor obtains its own narrow credential at execution time — now control [EAS-06.13]({{ '/spec/controls/identity.html#eas-06-13' | relative_url }}). |
| **H6** | Frameworks that apply the latest code to paused Runs. | Record the version on the Run; route resumption to matching workers. |
| **H7** | Framework default trace exporters that send payloads before your redaction runs. | Replace the default exporters, redact in-process. |
| **H8** | Reconciling uncertain effects needs each target system's delivery or status API. | Per-integration work in the executor. |
