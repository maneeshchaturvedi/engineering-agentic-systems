---
layout: doc
title: Hook Contract
section: Specification
order: 6
---

# Hook Contract

The hook contract defines the interception points a stack must expose for controls to be enforced *outside the model*. It is abstract: each [stack profile]({{ '/profiles/' | relative_url }}) binds these hooks to the framework's native mechanisms (callbacks, middleware, guardrails, graph nodes) or records that a hook is not expressible, which is itself a finding.

A hook is **blocking** if it can prevent the operation from proceeding. A hook that can only observe does not satisfy a control that requires enforcement.

| Hook | When | Blocking | Must receive | Typical controls |
|---|---|---|---|---|
| `run.start` | Before the first Step. | Yes | Workflow, version, Principal | Credential minting, budget initialisation, admission ([EAS-06](controls/identity.html), [EAS-05](controls/bounds.html)) |
| `model.before` | Before each ModelCall. | Yes | Run, accumulated usage, assembled context | Token, cost and step limits; context budget ([EAS-05](controls/bounds.html), [EAS-08](controls/context.html)) |
| `model.after` | After each ModelCall. | No | Run, Decision, usage | Usage accounting; loop detection |
| `tool.before` | After a ToolRequest is produced, before any effect. | Yes, and able to substitute | Run (incl. taint, credential), ToolRequest | Policy gate, per-tool limits, taint rules, intent capture ([EAS-02](controls/separation.html), [EAS-04](controls/enforcement.html), [EAS-07](controls/untrusted-content.html)) |
| `tool.after` | After a Tool returns, before output enters context. | Yes (may transform) | Run, Tool, raw output | Output limits, explicit truncation, taint marking, freshness labels ([EAS-05.06](controls/bounds.html), [EAS-08](controls/context.html)) |
| `delegate` | Before control passes to a sub-agent or handoff target. | Yes | Parent Run, child spec, Credential | Scope narrowing, actor chain, budget inheritance ([EAS-06.04](controls/identity.html)) |
| `state.checkpoint` | When a Step boundary is persisted. | Yes | Run, state, version | Validation of model-derived state, atomic intent commit ([EAS-03](controls/actions.html), [EAS-09](controls/durable-state.html)) |
| `state.resume` | When a paused or failed Run resumes. | Yes | Checkpoint, recorded version, current version | Version pinning, migrations, replay sandboxing ([EAS-09](controls/durable-state.html)) |
| `memory.write` | Before persisting a MemoryEntry. | Yes | Run (incl. taint), entry | Provenance, trust downgrade ([EAS-07](controls/untrusted-content.html)) |
| `run.end` | After the Run reaches a terminal status. | No | Run, status, totals | Spend accounting, outcome correlation keys ([EAS-11](controls/baseline.html)) |

## Semantics

1. **`tool.before` is the most important hook.** It is the boundary between reasoning and execution. It MUST be able to deny a ToolRequest and return a structured refusal to the model, and SHOULD be able to *substitute* — converting a direct effect into a committed ActionIntent for later execution (see [EAS-03](controls/actions.html)).
2. **Hooks run in deterministic code.** A hook MUST NOT delegate its decision to a model. A hook MAY consult a classifier as a signal, but the outcome of a probabilistic signal can only be `allow` or `escalate`, never a silent pass for a request that deterministic rules would deny.
3. **Hooks fail closed.** If a blocking hook errors or times out, the operation MUST NOT proceed.
4. **Hooks see identity from the Run, never from arguments.** The Principal, tenant and scopes available to a hook come from the Run's Credential.
5. **Coverage is total.** A hook bound only to some Tools, or only to the parent agent and not its sub-agents, is a partial binding. Profiles record coverage explicitly.

## Conformance of a binding

A stack's binding of the hook contract is assessed per hook:

| Status | Meaning |
|---|---|
| `native` | The framework exposes a blocking interception point with the required inputs. |
| `adapter` | Achievable by wrapping framework components (e.g. wrapping every tool function); coverage must be verified. |
| `partial` | Achievable for some paths only (e.g. not for built-in or hosted tools). |
| `absent` | Not expressible without modifying the framework. Controls that depend on this hook require an architectural change. |
