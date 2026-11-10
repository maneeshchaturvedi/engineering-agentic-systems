---
layout: doc
title: CrewAI Profile
section: Profiles
framework: CrewAI
verified_version: "1.15.39"
verified_on: 2026-11-10
status: draft
---

# CrewAI Profile

This profile maps the EAS [reference model](../spec/reference-model.html), [hook contract](../spec/hooks.html) and [telemetry conventions](../spec/telemetry.html) onto CrewAI. Every API name, default and behaviour below was checked against the official CrewAI documentation (docs.crewai.com) on the date above. Anything that could not be confirmed is marked *(unverified)*.

## Scope

| Item | Value |
|---|---|
| Package | `crewai` (Python) **1.15.39**, the latest entry in the official changelog (released 2026-11-08). The docs were read at their current (unversioned) URLs. |
| Covered | **Crews** (`Agent`, `Task`, `Crew`, `Process.sequential` / `Process.hierarchical`, `kickoff*`), **Flows** (`Flow`, `@start`, `@listen`, `@router`, `or_`/`and_`, structured state, `@persist`, `@human_feedback`), direct `Agent.kickoff()` / `kickoff_async()` and direct `LLM.call(...)`, custom tools (`BaseTool`, `@tool`), `max_usage_count`, MCP via `mcps=` / `MCPServerAdapter`, unified `Memory`, Knowledge, task guardrails, execution hooks (`crewai.hooks`: `on`, `InterceptionPoint`, `HookAborted`, legacy `@before_tool_call` / `@after_tool_call` / `@before_llm_call` / `@after_llm_call`), step/task callbacks, the event bus (`BaseEventListener`), checkpointing (`CheckpointConfig`), anonymous telemetry, built-in tracing, and the third-party OpenTelemetry integrations listed in the docs. |
| OSS vs platform | This profile covers the open-source library. **CrewAI AMP** (the hosted platform) adds trace storage (the Traces tab), webhook-based human input with a `/resume` endpoint, and deployments. Where AMP is the only route to a capability, the profile says so. AMP access controls, retention and tenancy were not assessed. |
| Not covered | Training and testing commands (`crewai train`, `crewai test`), A2A server mode, deprecated code execution (`allow_code_execution`), and integrations' own SDK options. |

## Concept mapping

| EAS entity | Native concept | Notes / gaps |
|---|---|---|
| Workflow | A **Flow** subclass, or a **Crew** (often a `@CrewBase` class) | CrewAI has no workflow `id`/`version` field. Carry both in Flow state or kickoff inputs, and emit them yourself. **Rung mapping:** a Flow whose methods are plain code plus `LLM.call` → `fixed_workflow` (or `single_call` for a single call). A Flow method that calls `Agent.kickoff()` with tools → `agent` for that step. A Crew → `agent` (one agent) or `multi_agent` (several agents, any agent with `allow_delegation=True`, or `Process.hierarchical`). A sequential Crew of tool-less, non-delegating agents behaves like a fixed chain of model calls. Each agent still runs inside the agent executor with `max_iter`, so the assessor decides which rung applies and records the reasoning. |
| Run | One `Crew.kickoff*()` or `Flow.kickoff*()` | Flow state has an auto-generated UUID `state.id`, kept across persisted resumes (`kickoff(inputs={"id": ...})`). Crews have IDs (telemetry reports "Crew metadata: IDs"), but no per-kickoff run id is documented *(unverified)*. There is no Run `status` enum. Map the outcomes yourself: output object, exception, `HumanFeedbackPending` (Flow pause). |
| Step | Agent executor iteration (bounded by `max_iter`). In hooks, `PRE_STEP`/`POST_STEP` fire per **task** or **flow method** (`ctx.kind` ∈ `"task"`, `"flow_method"`) | Two granularities. Use the hook "step" (task or flow method) as the EAS checkpoint unit, and agent iterations (`ctx.iterations` in model hooks) as the step-budget unit. |
| ModelCall | `LLM` call made by the agent executor, or a direct `LLM.call(...)` | Observable through `PRE_MODEL_CALL`/`POST_MODEL_CALL` and `LLMCallStarted/Completed/FailedEvent`. Per-call token usage in hook or event payloads is not documented *(unverified)*. Aggregate usage is in `crew.usage_metrics` and `flow.usage_metrics` after the run. |
| Decision | Model response (`ctx.response` in `POST_MODEL_CALL`), task output (`TaskOutput.raw` / `.pydantic`), router label | Structured output comes from `output_pydantic` / `output_json` / `response_format`. If conversion fails, those fields are `None` and only `raw` is set. |
| Tool | `BaseTool` subclass (`name`, `description`, `args_schema`, `_run`) or `@tool` function; MCP tools via `mcps=` | No native fields for `effect_class`, `egress`, `output_trust`, `data_access`, `idempotency`, `required_scopes` or `approval`. Declare them in the manifest, or as extra fields on a `BaseTool` subclass. Native limits: `max_usage_count` (default unlimited) and `cache_function`. |
| ToolRequest | `ToolCallHookContext` (`tool_name`, `tool_input`, `tool`, `agent`, `task`, `crew`) in `PRE_TOOL_CALL` | Inputs may be mutated **in place only**. |
| PolicyDecision | `HookAborted(reason, source)` raised from a hook. CrewAI emits a `HookDispatchedEvent` with outcome `proceeded` / `modified` / `aborted`, the reason and the source | Close to the EAS shape. Use `reason` for `eas.policy.rule_id`. There is no native `escalate` outcome. Model it as abort plus a human-input request, or as an ActionIntent. |
| ActionIntent | — | **No native concept.** Implement as an application ledger. `PRE_TOOL_CALL` can commit an intent and then abort with a reason that tells the model the action is queued (see `tool.before` below). |
| Principal / Credential | — | **No native concept.** Hook contexts, tools and events carry no principal, tenant, scope or actor chain. Put them in Flow state or a `contextvars` context set by your entry point, never in model-visible arguments. |
| Budget | `Agent.max_iter` (20), `max_execution_time`, `max_rpm`, `max_retry_limit` (2), `Crew.max_rpm`, `Tool.max_usage_count`, `Task.guardrail_max_retries` (3), `LLM.max_tokens` | All of these are **per agent, per task or per call, not per Run**. CrewAI documents no Run-level token, cost, step or wall-time budget. Build them in `PRE_MODEL_CALL` / `PRE_TOOL_CALL`. |
| ContextItem | Task `description`/`context`, agent `role`/`goal`/`backstory`, recalled memories, knowledge chunks, tool results | No `kind`, `as_of` or `trust` labels. When `respect_context_window=True` (the default), CrewAI summarises history on overflow. That compaction is implicit, and nothing marks the content as partial. |
| Checkpoint | Crews: `CheckpointConfig` (default `location="./.checkpoints"`, `on_events=["task_completed"]`, `provider=JsonProvider()`, `max_checkpoints=None`). Flows: `@persist` (`SQLiteFlowPersistence` by default; custom `FlowPersistence`) | The checkpoint stores "the full state of the crew, flow, or agent" (memory, knowledge sources, task progress, intermediate outputs, inputs, event history). It does not record the workflow version *(per docs; not mentioned)*. |
| MemoryEntry | Unified `Memory` record (`remember()`; scope path, categories, importance, optional `source`, `private`) | `source` is the only provenance field, and it is optional. There is no trust field. For Crews, memory is extracted automatically by an LLM after each task. The default store is LanceDB under `./.crewai/memory`. |
| Trace | Built-in tracing (OpenTelemetry spans exported to CrewAI AMP), or third-party instrumentors (OpenInference `CrewAIInstrumentor`, OpenLIT, …) | None of them emits `eas.*` attributes. See [Evidence collection](#evidence-collection). |

## Hook bindings

Facts that apply to every hook below:

- Import path: `from crewai.hooks import on, InterceptionPoint, HookAborted`. Legacy decorators (`@before_tool_call`, `@after_tool_call`, `@before_llm_call`, `@after_llm_call`) share the same chain.
- **Blocking:** a hook blocks only by raising `HookAborted` (or, in a legacy before-hook, by returning `False`). **Any other exception "is swallowed (fail-open)".** This conflicts with [hook semantics](../spec/hooks.html) §3. A conformant binding must wrap every hook body so that any internal error is re-raised as `HookAborted` (see [Satisfying L1](#satisfying-l1-in-crewai)).
- **Scope:** global hooks first, then crew-scoped hooks (`@on` on a `@CrewBase` method, active only while that crew runs), each in registration order. The `agents=` and `tools=` filters match on **role and tool name strings**, so renaming a role or tool silently removes coverage.
- Hook contexts carry no run id, principal or credential. Every hook needs a `contextvars` adapter to meet §4.

| EAS hook | Native mechanism | Status | Notes (block vs observe) |
|---|---|---|---|
| [`run.start`](../spec/hooks.html) | `@on(InterceptionPoint.EXECUTION_START)` ("A crew or flow is about to begin"; `ctx.payload` = inputs dict). Also `INPUT` (resolved inputs). | adapter | **Can block** (`HookAborted`) and mutate inputs. Not documented to fire for a standalone `Agent.kickoff()` *(unverified)*. The Workflow, version and Principal must be supplied by your entry point because CrewAI has none of them. `@before_kickoff` exists but its behaviour is not documented *(unverified)*. |
| [`model.before`](../spec/hooks.html) | `@on(InterceptionPoint.PRE_MODEL_CALL)` / `@before_llm_call`; `LLMCallHookContext` (`messages`, `agent`, `task`, `crew`, `llm`, `iterations`, `executor`) | native | **Can block.** The executor raises `ValueError("LLM call blocked by before_llm_call hook")`. Documented to cover direct LLM calls too (agent/task/crew are `None`). Accumulated Run usage is **not** in the context, so the Run token counter is your own (adapter). It is not documented whether a blocked call triggers the agent's `max_retry_limit` retries *(unverified)*. |
| [`model.after`](../spec/hooks.html) | `@on(InterceptionPoint.POST_MODEL_CALL)` / `@after_llm_call` (`ctx.response`); `LLMCallCompletedEvent` | native | Returning a string replaces the response, which goes beyond observing. Per-call token usage is not documented in the context or the event *(unverified)*. |
| [`tool.before`](../spec/hooks.html) | `@on(InterceptionPoint.PRE_TOOL_CALL)` / `@before_tool_call`; `ToolCallHookContext` | native (substitution: adapter) | **Can block.** The agent receives "Tool execution blocked by hook. Tool: <name>" and the run continues, which gives the model a structured refusal. Can mutate `tool_input` in place. Can request human input in-process via `ctx.request_human_input(prompt, default_message)`. To substitute, commit an ActionIntent in the hook and then abort with a reason. Documented to fire on "every tool execution". Coverage of MCP tools and of the auto-added delegation tools is not stated *(unverified)*, so assessors must test it. |
| [`tool.after`](../spec/hooks.html) | `@on(InterceptionPoint.POST_TOOL_CALL)` / `@after_tool_call` (`tool_result`, `raw_tool_result`) | native | **Can transform:** returning a string replaces the agent-facing result, and `None` keeps it. This is the place for output limits, truncation markers and taint marking. Separately, the `LLM`'s `context_window_size` controls "when large tool results are saved to a file". That path is framework behaviour and must be accounted for in output limits. |
| [`delegate`](../spec/hooks.html) | No delegation interception point. Delegation happens through the auto-added tools "Delegate work to coworker(task, context, coworker)" and "Ask question to coworker(question, context, coworker)", the hierarchical manager, and A2A (`A2ADelegationStarted/CompletedEvent`, observe only). | adapter (coverage unverified) | If `PRE_TOOL_CALL` fires for the delegation tools *(unverified)*, filtering by their tool names gives a blocking point. CrewAI has no credential to narrow, and delegated agents run with their own configured tools. Scope narrowing and actor-chain recording are entirely application code. If the tool hooks do not fire for these tools, the status is **absent**. |
| [`state.checkpoint`](../spec/hooks.html) | Crew `CheckpointConfig(on_events=..., provider=...)`. Flow `@persist` with a custom `FlowPersistence`. `@on(InterceptionPoint.POST_STEP)` (task / flow method). | adapter | CrewAI has no hook *before* a checkpoint write. You can block or validate in two ways: a custom `FlowPersistence` that validates state before saving, or a `POST_STEP` hook that validates or aborts. Whether `POST_STEP` runs before the checkpoint write is not documented *(unverified)*. The checkpoint `provider` interface for Crews is limited to `JsonProvider`/`SqliteProvider` in the docs. A custom provider is *(unverified)*. |
| [`state.resume`](../spec/hooks.html) | Flow: `kickoff(inputs={"id": ...})`, `kickoff(restore_from_state_id=...)` (fork), `Flow.from_pending(id)` + `resume(feedback)`. Crew: `kickoff(from_checkpoint=...)`, `Crew.from_checkpoint(...)`, `Crew.fork(...)`, `crewai replay -t <task_id>`. | adapter | CrewAI exposes no resume hook. Wrap every resume entry point in your own code to compare the recorded version against the current one before calling CrewAI. **A Flow resume with an unknown id "falls back silently"**, so the wrapper must check that the snapshot exists. Whether `EXECUTION_START` fires on resume is *(unverified)*. |
| [`memory.write`](../spec/hooks.html) | No interception point. Crews write memory automatically ("After each task, the crew automatically extracts discrete facts … and stores them"). `MemorySave*` events are observe-only. A custom `StorageBackend` protocol and `memory.slice(..., read_only=True)` (raises `PermissionError` on write) are available. | adapter | You can block with a custom `StorageBackend` that refuses or downgrades entries without provenance or with tainted provenance, or with `read_only=True` slices. Whether the automatic post-task extraction path honours a read-only slice passed as the crew's memory is *(unverified)*. |
| [`run.end`](../spec/hooks.html) | `@on(InterceptionPoint.EXECUTION_END)` / `OUTPUT`; `CrewKickoffCompleted/FailedEvent`, `FlowFinished/FailedEvent`; `crew.usage_metrics` / `flow.usage_metrics` | native | Observation is sufficient here. Whether `EXECUTION_END` fires on failure is *(unverified)*, so use the `*FailedEvent` events as well. Note that `respect_context_window=False` ends execution with a `SystemExit` that `except Exception` does not catch. |

Non-hook mechanisms and what they can do:

| Mechanism | Can block? | Use |
|---|---|---|
| Task `guardrail` / `guardrails` (function returning `(bool, Any)`) | Rejects the **task output**. The error goes back to the agent, which retries up to `guardrail_max_retries` (default 3). | Deterministic output checks ([EAS-04.03](../spec/controls/enforcement.html)). This acts after the agent's tool calls, so it is **not** a tool gate. |
| String guardrails (`LLMGuardrail`, which uses the agent's LLM) | Model judgement | A signal only. Does not satisfy [EAS-04.01](../spec/controls/enforcement.html) or [EAS-01.03](../spec/controls/pattern-selection.html). |
| `step_callback` (agent or crew), `task_callback`, `Task.callback` | Observe only (documented as "called after") | Audit and metrics. |
| Event bus (`BaseEventListener`, `crewai_event_bus.on(...)`) | Not documented as able to block | Telemetry enrichment, `run.end` accounting. |
| Flow `@router` | Yes, as control flow (code) | Deterministic routing for [EAS-01.03](../spec/controls/pattern-selection.html). |
| `Task.human_input=True`, Flow `@human_feedback` | Review of the **final answer**, not of individual tool calls | Approval gates. The default `ConsoleProvider` blocks in-process. A custom `HumanFeedbackProvider` that raises `HumanFeedbackPending` persists the Flow state, and `kickoff()` returns. |

## Evidence collection

### (a) Static signals for L1 controls

| Control | What to look for in CrewAI code and config |
|---|---|
| [EAS-01.01](../spec/controls/pattern-selection.html) | The declared `rung` matches what the code builds. A Flow with `LLM.call`/code methods is `fixed_workflow`. Any `Agent` with `tools` or `allow_delegation=True` makes that step `agent`. Several agents, `Process.hierarchical`, `manager_llm`/`manager_agent` or `allow_delegation=True` → `multi_agent`. Also check `planning=True` (adds an `AgentPlanner` call "before each iteration") and `reasoning=True`. |
| [EAS-01.02](../spec/controls/pattern-selection.html) | For each Crew, a justification that names context isolation, permission separation, parallelism or ownership. Agent `role`/`goal`/`backstory` text that only describes personas ("researcher", "writer") is not a justification. |
| [EAS-01.03](../spec/controls/pattern-selection.html) | Eligibility, routing and legally required actions live in Flow `@router` / `@listen` code or plain functions, not in task `description`s, agent backstories or string guardrails. |
| [EAS-02.01](../spec/controls/separation.html) | A global `PRE_TOOL_CALL` hook (not filtered by `tools=`/`agents=`) that fails closed. Check that **no** tool performs effects without going through it. Check the coverage of MCP tools (`mcps=`), delegation tools and `CodeInterpreterTool` by test *(coverage unverified in docs)*. `code_execution_mode="unsafe"` is a finding. |
| [EAS-02.02](../spec/controls/separation.html) | Every `BaseTool` has an `args_schema` (Pydantic), a Pydantic output model, declared scopes, and an output limit. A bare `@tool` function with untyped args is a finding. |
| [EAS-03.01](../spec/controls/actions.html) | Every tool has an `effect_class` in the manifest (or as a field on a `BaseTool` subclass). Built-in `crewai_tools` and MCP tools must be classified too. |
| [EAS-04.01](../spec/controls/enforcement.html) | Each rule in agent `goal`/`backstory`/`system_template` or task `description` has a matching check in a `PRE_TOOL_CALL` hook, a function guardrail, Flow code or the data layer. |
| [EAS-04.02](../spec/controls/enforcement.html) | The `PRE_TOOL_CALL` hook checks the tool allow-list per workflow, scopes from the Run context, argument bounds and taint, and raises `HookAborted(reason=<rule_id>)`. |
| [EAS-05.01](../spec/controls/bounds.html) | `max_iter` is set explicitly. The default **20** is finite but applies **per agent per task**, and reaching it makes the agent "provide its best answer", which is not a distinct terminal status. Add a Run-level step counter in `PRE_MODEL_CALL` (`ctx.iterations` is per executor). Flows with `@router` cycles have no documented iteration cap *(unverified)*. `reasoning=True` with `max_reasoning_attempts=None` "will try until ready", so it is unbounded unless set. |
| [EAS-05.02](../spec/controls/bounds.html) | A Run-level token check in `PRE_MODEL_CALL`. `LLM(max_tokens=...)` bounds one call only. CrewAI documents no per-run token budget. |
| [EAS-05.03](../spec/controls/bounds.html) | `max_execution_time` set on every agent. Its default is not stated, and the examples use `None` *(treat as unbounded; unverified)*. It is per task, not per Run. `LLM(timeout=...)` set explicitly (no documented default; *unverified*). Explicit timeouts on tool I/O. MCP `connect_timeout` defaults to 30 s. A Run deadline lives in the caller or in `PRE_MODEL_CALL`. |
| [EAS-05.05](../spec/controls/bounds.html) | `max_usage_count` on each tool (default: "unlimited"; scope per task or per Run is *unverified*), or a per-Run per-tool counter in `PRE_TOOL_CALL`. |
| [EAS-05.06](../spec/controls/bounds.html) | A `POST_TOOL_CALL` hook enforcing the token limit, and awareness of `context_window_size` file-spill behaviour. |
| [EAS-05.08](../spec/controls/bounds.html) | Inventory: `Agent.max_retry_limit` (default **2**, "retries when an error occurs"), `LLM(max_retries=...)` (no documented default; *unverified*), provider SDK / LiteLLM retries *(unverified)*, empty-response resend ("resent once"), `guardrail_max_retries` (default **3**, which re-runs the model on validation failure and counts against model budgets), and tool-internal retries. More than one active layer per dependency is a finding. |
| [EAS-06.01](../spec/controls/identity.html) | No `args_schema` field named `user_id`, `tenant_id`, `account_id` or similar. Tools read identity from a `contextvars`/closure set at kickoff. |
| [EAS-06.02](../spec/controls/identity.html) | Tools that take model-supplied record ids look up ownership against the Run principal before acting. |
| [EAS-07.01](../spec/controls/untrusted-content.html) | `output_trust`, `data_access` and `egress` are declared for every tool, MCP server, knowledge source and memory scope. Web/scrape/search tools (`SerperDevTool`, `ScrapeWebsiteTool`, …), `*SearchTool` RAG tools and MCP tools default to `untrusted`. |
| [EAS-07.02](../spec/controls/untrusted-content.html) | For each Crew, take the union of tools across **all** agents, because delegation lets agent A's untrusted content reach agent B's egress tool. If private + untrusted + egress are all present, there must be a deterministic gate (`PRE_TOOL_CALL` taint rule). |
| [EAS-07.04](../spec/controls/untrusted-content.html) | Per-agent and per-task `tools=` lists are minimal. MCP servers use `create_static_tool_filter(allowed_tool_names=[...])`. `allow_delegation` stays `False` (default) unless justified. |
| [EAS-08.01](../spec/controls/context.html) | Tools paginate or truncate with an explicit marker (in the tool or in `POST_TOOL_CALL`). Reliance on `respect_context_window=True` summarisation is not explicit truncation. |
| [EAS-08.02](../spec/controls/context.html) | Structured facts (balances, statuses, entitlements) come from typed tools, not from `knowledge_sources` / RAG `*SearchTool` (similarity search; `results_limit` 3, `score_threshold` 0.35 by default) or from `Memory.recall`. |
| [EAS-08.03](../spec/controls/context.html) | No NL2SQL / free-form query tools against production stores. Tools take parameters for fixed query templates. |
| [EAS-09.01](../spec/controls/durable-state.html) | In Flow methods that call `@human_feedback` or raise `HumanFeedbackPending`, and in tasks with `human_input=True`, no effect is performed earlier in the same method or task. Re-execution semantics on resume are not documented *(unverified)*. |
| [EAS-10.01](../spec/controls/evidence-gated-change.html) | Prompts (`agents.yaml`/`tasks.yaml`, `system_template`, `prompt_file`), model names, tool descriptions, knowledge config and guardrails are all in version control. AMP-console-only edits are a finding. |
| [EAS-10.02](../spec/controls/evidence-gated-change.html) | An `EXECUTION_START` hook (or the entry point) reads a runtime flag per workflow/version/tenant and raises `HookAborted`. |
| [EAS-12.01](../spec/controls/observability.html) | An OTel instrumentor is registered with your tracer provider, and an adapter adds `eas.*` attributes (see below). |
| [EAS-12.02](../spec/controls/observability.html) | `share_crew` is not `True`. `CREWAI_TRACING_ENABLED=false` (or `tracing=False`) unless traces go through redaction. Anonymous telemetry is reviewed or disabled (`CREWAI_DISABLE_TELEMETRY=true`). Third-party instrumentor content capture is configured. `output_log_file` and `verbose=True` logs are treated as personal-data stores. |

### (b) Telemetry

**Built-in anonymous telemetry (on by default).** The docs say "NO personal data is collected". Collected by default: CrewAI/Python versions; crew metadata (IDs, process type, memory used, whether inputs were passed but not their keys or values, task/agent counts); agent role name, boolean settings, limits, LLM info and tool names; task execution settings; tool usage counts; task lifecycle timestamps and success/failure (exception class name only); flow lifecycle; CLI events; and a coarse environment description including `project_id`. With **`share_crew=True`** CrewAI also sends "detailed crew and task execution data", including goal, backstory, context and **output**, which "may include personal information". That breaches [EAS-12.02](../spec/controls/observability.html) unless outputs are known to be free of personal data. Opt out with `CREWAI_DISABLE_TELEMETRY` (`true`/`1`/`yes`/`on`), or with `OTEL_SDK_DISABLED` (which "also disables CrewAI's exporter"). `OTEL_SDK_DISABLED` is the standard OTel SDK switch and may also disable your own OTel pipeline in the same process *(unverified)*, so prefer `CREWAI_DISABLE_TELEMETRY`. `CREWAI_DISABLE_TRACKING` applies only to the experimental standalone-agent conversation signals.

**Built-in tracing (CrewAI AMP).** CrewAI "exports OpenTelemetry spans directly to Wharf", and these traces "may contain prompts, inputs, and outputs". The docs describe **no redaction option**. Nothing is sent before consent: on first run, spans are buffered and the user is asked "Share this execution trace with CrewAI? [y/N]". Declining, a timeout or a non-interactive run discards them. Enable with `tracing=True`, `CREWAI_TRACING_ENABLED=true` or `crewai traces enable`. Disable with `CREWAI_TRACING_ENABLED=false`, `crewai traces disable` or `tracing=False` on the Crew/Flow. For [EAS-12.02](../spec/controls/observability.html), a production deployment must pin it off explicitly, or treat AMP as a processor of personal data covered by the data inventory ([EAS-12.07](../spec/controls/observability.html)).

**OpenTelemetry for your own pipeline.** The docs list integrations rather than a native OTLP exporter for user traces. The two verified OTel paths are OpenInference (`pip install openinference-instrumentation-crewai`; `CrewAIInstrumentor().instrument(tracer_provider=...)`) and OpenLIT (`openlit.init(otlp_endpoint=...)`, described as "OpenTelemetry-native"). The docs also list Langfuse, MLflow, Langtrace, Opik, Weave, Portkey and LangDB without stating their mechanism. Neither verified path documents a content-capture switch on the CrewAI pages. OpenInference's `OPENINFERENCE_HIDE_INPUTS`/`HIDE_OUTPUTS` settings *(unverified here)* or an in-process redacting `SpanProcessor` are needed for [EAS-12.02](../spec/controls/observability.html). Span names and attributes emitted by these instrumentors were not documented on the CrewAI pages *(unverified)*.

**Adding `eas.*` attributes:**

| EAS attribute(s) | Where to set them in CrewAI |
|---|---|
| `eas.run.id`, `eas.workflow.*`, `eas.tenant.id`, `eas.principal.type`, `eas.budget.*.limit` | Open your own `eas.run` span around `kickoff()` in the entry point, and put the values in a `contextvars` context. Instrumentor spans nest under it if they use the active OTel context *(unverified per instrumentor)*. |
| `eas.budget.*.used`, `eas.cost.usd` | In the `POST_MODEL_CALL` hook (your own counters). Cross-check against `crew.usage_metrics` / `flow.usage_metrics` at `run.end`. |
| `eas.policy.*` | Emit an `eas.policy` span inside the `PRE_TOOL_CALL` hook for every decision. `HookDispatchedEvent` (outcome, reason, source) can be bridged from the event bus. It is emitted only when at least one hook is registered for the point. |
| `eas.tool.*` (`effect_class`, `egress`, `output_trust`, `output_tokens`, `output_truncated`, `call_index`, `args_fingerprint`) | `PRE_TOOL_CALL` / `POST_TOOL_CALL`, read from the tool's declared attributes. Set them on the current span (the instrumentor's tool span, if it is active in context *(unverified)*) or on your own `execute_tool` span. |
| `eas.run.tainted`, `eas.actor_chain` | In the `contextvars` Run context, updated in `POST_TOOL_CALL` (taint) and in the delegation-tool `PRE_TOOL_CALL` (actor chain). |
| `eas.redaction.*`, `eas.payload.*` | Your redacting `SpanProcessor`. |

## Framework pitfalls

| Pitfall | Why it violates | Controls |
|---|---|---|
| Hook bodies that raise ordinary exceptions are swallowed ("fail-open"), so a buggy policy check allows the call | Hooks must fail closed | [EAS-02.01](../spec/controls/separation.html), [EAS-04.02](../spec/controls/enforcement.html) |
| Hook `agents=`/`tools=` filters match role and tool name strings. Renamed roles or new tools fall outside a filtered gate | Gate coverage is no longer total | [EAS-02.01](../spec/controls/separation.html), [EAS-04.02](../spec/controls/enforcement.html) |
| Reassigning `ctx.tool_input` or `ctx.messages` instead of mutating in place. The tool never sees the change, and replacing `messages` "breaks the executor" | The argument sanitisation that was meant to run never takes effect | [EAS-04.02](../spec/controls/enforcement.html), [EAS-06.01](../spec/controls/identity.html) |
| Role-play crews (`role`/`goal`/`backstory` personas: "Researcher", "Writer", "Manager") chosen by default. CrewAI's primary abstraction invites this. Flows (`@start`/`@listen`/`@router` with `LLM.call` or a single `Agent.kickoff`) provide the lower rungs and should be the default | The split is a persona, not a context, permission, parallelism or ownership boundary | [EAS-01.01](../spec/controls/pattern-selection.html), [EAS-01.02](../spec/controls/pattern-selection.html), [EAS-01.04](../spec/controls/pattern-selection.html) |
| `allow_delegation=True` / `Process.hierarchical`: free-text delegation ("Delegate work to coworker(task, context, coworker)") to any coworker. The docs show no allowed-target restriction and no delegation depth limit (only advice against "delegate back and forth indefinitely") | Delegation that does not narrow scope, an actor chain that is never recorded, step counts multiplied across agents | [EAS-06.04](../spec/controls/identity.html), [EAS-01.04](../spec/controls/pattern-selection.html), [EAS-05.01](../spec/controls/bounds.html) |
| Crew agents with disjoint tool sets are assumed to be isolated. Delegation and task `context` pass untrusted text from the reading agent to the acting agent within the same Run | A lethal combination at Crew level | [EAS-07.02](../spec/controls/untrusted-content.html), [EAS-07.03](../spec/controls/untrusted-content.html) |
| Automatic LLM extraction into memory after every task. `source` is optional and there is no trust field, so content derived from a web page becomes a future "fact" | Memory without provenance, and memory poisoning | [EAS-07.07](../spec/controls/untrusted-content.html) |
| Memory (LanceDB `./.crewai/memory`) and knowledge (ChromaDB, collections named by agent role or `"crew"`) have no tenant concept. Tool result `cache=True` is on by default on agents and crews | Cross-tenant leakage through shared stores and caches | [EAS-06.07](../spec/controls/identity.html) |
| `cache=True` (default) on effectful tools may return a cached result instead of re-executing *(cache key semantics unverified)* | A hidden source of non-execution or duplication | [EAS-03.01](../spec/controls/actions.html), [EAS-03.06](../spec/controls/actions.html) |
| `max_iter` reached → "best answer", not a terminal budget status. All limits are per agent or per task, so a Run's worst case is the sum over tasks, delegations and guardrail retries | No Run-level bound and no `budget_exhausted` | [EAS-05.01](../spec/controls/bounds.html), [EAS-05.02](../spec/controls/bounds.html) |
| `reasoning=True` with `max_reasoning_attempts=None` ("will try until ready"). `planning=True` adds a planner call before each iteration | Unbounded or unbudgeted model calls | [EAS-05.01](../spec/controls/bounds.html), [EAS-05.02](../spec/controls/bounds.html) |
| Stacked retries: `max_retry_limit` (2) × `LLM max_retries` × provider SDK × `guardrail_max_retries` (3) | Retries in more than one layer | [EAS-05.08](../spec/controls/bounds.html) |
| `respect_context_window=True` silently summarises history on overflow, and large tool results spill to files based on `context_window_size` | Implicit, unmarked truncation | [EAS-08.01](../spec/controls/context.html), [EAS-08.07](../spec/controls/context.html) |
| Knowledge and RAG search tools used for exact facts (similarity search, top 3, threshold 0.35) | Structured facts fetched by similarity | [EAS-08.02](../spec/controls/context.html) |
| String guardrails (`guardrail="must not include PII"`) are an LLM checking an LLM | Not a code backstop | [EAS-04.01](../spec/controls/enforcement.html), [EAS-04.03](../spec/controls/enforcement.html) |
| `Task.human_input` reviews the *final answer* after tools have already run | An approval that arrives after the effect | [EAS-03.08](../spec/controls/actions.html), [EAS-09.01](../spec/controls/durable-state.html) |
| Console HITL (`ConsoleProvider`, `human_input`) blocks the process while it waits | No durable waiting | [EAS-09.02](../spec/controls/durable-state.html) |
| A Flow resume with an unknown `id` "falls back silently". Checkpoints record no workflow version. Checkpoint `max_checkpoints=None` keeps everything, unencrypted, in `./.checkpoints` | Silent fresh starts, no version pinning, unbounded copies of customer data | [EAS-09.08](../spec/controls/durable-state.html), [EAS-12.07](../spec/controls/observability.html), [EAS-09.10](../spec/controls/durable-state.html) |
| Restoring checkpoints with `CREWAI_DESERIALIZE_CALLBACKS=1` imports code paths named in the file | Untrusted checkpoint → code execution | [EAS-07.06](../spec/controls/untrusted-content.html) (supply chain) |
| `share_crew=True`, AMP tracing enabled (prompts, inputs, outputs, no redaction), `output_log_file`, `verbose=True` | Unredacted personal data leaves the process or lands in logs | [EAS-12.02](../spec/controls/observability.html), [EAS-12.07](../spec/controls/observability.html) |
| MCP servers attached via `mcps=` without `allowed_tool_names`. Docs say only "ensure that you trust an MCP Server", with no description pinning | Unreviewed, unpinned third-party tools | [EAS-07.04](../spec/controls/untrusted-content.html), [EAS-07.06](../spec/controls/untrusted-content.html) |
| `code_execution_mode="unsafe"` (direct execution, deprecated feature) | The model's output directly causes effects | [EAS-02.01](../spec/controls/separation.html) |

## Satisfying L1 in CrewAI

**Fail-closed run context and gate (the base for most L1 controls).** Give each Run a `contextvars` context, and register global hooks whose errors become aborts:

```python
import contextvars, functools
from crewai.hooks import on, InterceptionPoint, HookAborted

RUN = contextvars.ContextVar("eas_run")  # set by your entry point before kickoff()

def fail_closed(fn):
    @functools.wraps(fn)
    def wrapper(ctx):
        try:
            return fn(ctx)
        except HookAborted:
            raise
        except Exception as e:             # CrewAI would swallow this (fail-open)
            raise HookAborted(f"hook_error:{type(e).__name__}", fn.__name__)
    return wrapper

@on(InterceptionPoint.PRE_TOOL_CALL)       # global: no tools=/agents= filter
@fail_closed
def gate(ctx):
    run = RUN.get()                         # LookupError -> abort (no Run context)
    decision = run.policy.evaluate(ctx.tool_name, ctx.tool_input, run)  # deterministic
    run.emit_policy_span(decision)
    if decision.outcome != "allow":
        raise HookAborted(decision.rule_id, "eas.policy")
    run.count_tool(ctx.tool_name)           # EAS-05.05 per-Run per-tool limit
```

The order in which `@on` and `@fail_closed` compose depends on whether `@on` returns the function it registers *(unverified)*. If it does not, apply `fail_closed` inside a plain `def` and register that function. Check that `contextvars` reach hooks for `kickoff_async` and `async_execution=True` tasks *(unverified)*.

| Control | Concrete guidance |
|---|---|
| [EAS-01.01](../spec/controls/pattern-selection.html) / [EAS-01.02](../spec/controls/pattern-selection.html) | Start with a Flow. Use `LLM.call` with a Pydantic `response_format` per step, and `@router` for branching. Add an `Agent.kickoff()` step only where the path depends on discovery, and a Crew only with a written justification. Declare `rung` per workflow according to the mapping above. |
| [EAS-01.03](../spec/controls/pattern-selection.html) | Classify with one model call. Route and act in `@router`/`@listen` code (for example, unsubscribe is a code branch, not a task description). |
| [EAS-02.01](../spec/controls/separation.html) | The global, fail-closed `PRE_TOOL_CALL` gate above. Add a test that every registered tool (including MCP and delegation tools) triggers the gate. |
| [EAS-02.02](../spec/controls/separation.html) | Use `BaseTool` subclasses with `args_schema`, a Pydantic output model, and class fields for `required_scopes` and `output_limit_tokens`. Avoid untyped `@tool` functions. |
| [EAS-03.01](../spec/controls/actions.html) | Add `effect_class` (and `egress`, `output_trust`, `data_access`) to each tool class and to the manifest. The gate reads them. |
| [EAS-04.01](../spec/controls/enforcement.html) / [EAS-04.02](../spec/controls/enforcement.html) | For every rule in `backstory`/`description`, add a rule in the gate's policy (tool allow-list per workflow, scopes from `RUN`, argument bounds, taint) and/or a **function** task guardrail. Use the rule id as the `HookAborted` reason. |
| [EAS-05.01](../spec/controls/bounds.html) | Set `max_iter` explicitly on every agent. Add a Run-level step counter in a fail-closed `PRE_MODEL_CALL` hook that records `budget_exhausted` in `RUN` before raising `HookAborted`. Set `max_reasoning_attempts` if `reasoning=True`. Bound `@router` loops with a counter in Flow state. |
| [EAS-05.02](../spec/controls/bounds.html) | In `POST_MODEL_CALL`, accumulate usage per Run. Per-call usage is not exposed in the hook *(unverified)*, so count `ctx.messages`/`ctx.response` tokens with your tokenizer, or use `ctx.llm.get_token_usage_summary()` *(location unverified)*. Refuse in `PRE_MODEL_CALL` once the limit is reached. |
| [EAS-05.03](../spec/controls/bounds.html) | `LLM(timeout=...)`, `Agent(max_execution_time=...)`, explicit timeouts in every tool's HTTP/DB client, and a Run deadline checked in `PRE_MODEL_CALL`/`PRE_TOOL_CALL`. |
| [EAS-05.05](../spec/controls/bounds.html) | A per-Run, per-tool counter in the gate. `max_usage_count` on the tool can serve as a secondary cap. |
| [EAS-05.06](../spec/controls/bounds.html) | One `POST_TOOL_CALL` hook that measures tokens, truncates to `output_limit_tokens`, appends an explicit "[truncated: N of M; use cursor=…]" marker, and returns the string. |
| [EAS-05.08](../spec/controls/bounds.html) | Choose one layer, typically `LLM(max_retries=...)` or a gateway. Set `Agent(max_retry_limit=0)` and the other layers to zero, and document the choice. Count `guardrail_max_retries` in the step and token budgets. |
| [EAS-06.01](../spec/controls/identity.html) / [EAS-06.02](../spec/controls/identity.html) | Tools read `RUN.get().principal`/tenant. `args_schema` never contains identity fields. Model-supplied ids are checked for ownership against the principal before use. |
| [EAS-07.01](../spec/controls/untrusted-content.html) | Classify every tool, MCP server, knowledge source and memory scope in the manifest. Web, search, scrape, RAG and MCP default to `untrusted`. |
| [EAS-07.02](../spec/controls/untrusted-content.html) | Taint the Run in `POST_TOOL_CALL` when an `untrusted` tool returns. The gate denies or escalates `egress=true` tools on a tainted Run. Evaluate this at Crew level, across all agents. |
| [EAS-07.04](../spec/controls/untrusted-content.html) | Give each agent and task the minimal `tools=`. Use `create_static_tool_filter(allowed_tool_names=[...])` for MCP, leave `allow_delegation=False`, and give draft-only agents no send tool. |
| [EAS-08.01](../spec/controls/context.html) | Paginate in tools (cursor argument) and truncate explicitly in `POST_TOOL_CALL`. Size `context_window_size` so that implicit summarisation or file spill is not relied upon. |
| [EAS-08.02](../spec/controls/context.html) / [EAS-08.03](../spec/controls/context.html) | Use typed lookup tools with parameterised queries for facts. Keep `knowledge_sources` and RAG tools for unstructured passages, and add no free-form SQL tool. |
| [EAS-09.01](../spec/controls/durable-state.html) | Put `@human_feedback` and pending pauses in their own Flow method, with effects in a downstream `@listen` method. |
| [EAS-10.01](../spec/controls/evidence-gated-change.html) | Keep `config/agents.yaml`, `config/tasks.yaml`, tool classes, `LLM` model ids, knowledge config and policies in git. Stamp `eas.workflow.version` from the build. |
| [EAS-10.02](../spec/controls/evidence-gated-change.html) | A fail-closed `EXECUTION_START` hook reads a flag store (workflow, version, tenant) and raises `HookAborted("kill_switch", ...)`. Standalone `Agent.kickoff()` entry points check the flag in code. |
| [EAS-12.01](../spec/controls/observability.html) | Register `CrewAIInstrumentor` (or OpenLIT) with your tracer provider, open an `eas.run` root span around `kickoff()`, and add `eas.*` attributes from hooks as tabled above. |
| [EAS-12.02](../spec/controls/observability.html) | Set `CREWAI_TRACING_ENABLED=false`, `share_crew=False` and `CREWAI_DISABLE_TELEMETRY=true` (or keep telemetry after a documented review), add an in-process redacting `SpanProcessor` before any exporter, and avoid `output_log_file`/`verbose=True` in production. |

## Sources

- https://docs.crewai.com/en/changelog
- https://docs.crewai.com/en/concepts/agents
- https://docs.crewai.com/en/concepts/tasks
- https://docs.crewai.com/en/concepts/crews
- https://docs.crewai.com/en/concepts/flows
- https://docs.crewai.com/en/concepts/collaboration
- https://docs.crewai.com/en/concepts/tools
- https://docs.crewai.com/en/tools/overview
- https://docs.crewai.com/en/concepts/memory
- https://docs.crewai.com/en/concepts/knowledge
- https://docs.crewai.com/en/concepts/llms
- https://docs.crewai.com/en/concepts/checkpointing
- https://docs.crewai.com/en/concepts/event-listener
- https://docs.crewai.com/en/learn/execution-hooks
- https://docs.crewai.com/en/learn/tool-hooks
- https://docs.crewai.com/en/learn/llm-hooks
- https://docs.crewai.com/en/learn/human-in-the-loop
- https://docs.crewai.com/en/learn/human-feedback-in-flows
- https://docs.crewai.com/en/mcp/overview
- https://docs.crewai.com/en/telemetry
- https://docs.crewai.com/en/observability/tracing
- https://docs.crewai.com/en/observability/overview
- https://docs.crewai.com/en/observability/openlit
- https://docs.crewai.com/en/observability/arize-phoenix
