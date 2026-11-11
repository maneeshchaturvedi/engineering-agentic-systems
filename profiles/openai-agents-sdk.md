---
layout: doc
title: OpenAI Agents SDK Profile
section: Profiles
framework: OpenAI Agents SDK
verified_version: "0.24.0"
verified_on: 2026-11-11
status: reviewed (3 open items)
---

# OpenAI Agents SDK Profile

This profile maps the EAS [reference model](../spec/reference-model.html), [hook contract](../spec/hooks.html) and [telemetry conventions](../spec/telemetry.html) onto the OpenAI Agents SDK. Every API name, default and behaviour below was checked against the SDK documentation and source for the version stated; anything that could not be confirmed is marked *(unverified)*.

## Scope

| Item | Value |
|---|---|
| Package | `openai-agents` (Python) **0.24.0** (PyPI, released 2026-10-15). Docs read at tag `v0.24.0`. |
| TypeScript | `@openai/agents` 0.21.0 (npm). Mentioned only where it differs: camelCase names (`maxTurns`, `timeoutMs`, `traceIncludeSensitiveData`, `toolExecution.preApprovalInputGuardrails`); the semantics checked here match Python. |
| Covered | `Agent`, `Runner` (`run`, `run_sync`, `run_streamed`), `RunConfig`, `RunHooks`/`AgentHooks`, input/output/tool guardrails, function tools, hosted tools (`WebSearchTool`, `FileSearchTool`, `CodeInterpreterTool`, `HostedMCPTool`, `ImageGenerationTool`, `ToolSearchTool`, `ProgrammaticToolCallingTool`), local execution tools (`ComputerTool`, `ShellTool`, `ApplyPatchTool`), local MCP servers (`MCPServerStdio`, `MCPServerSse`, `MCPServerStreamableHttp`), handoffs, `Agent.as_tool()`, human-in-the-loop (`needs_approval`, `RunState`), Sessions, usage, tracing, runner-managed retries. |
| Durable execution | The docs list integrations with **Temporal**, **Dapr** (Diagrid), **Restate** and **DBOS**. They are maintained outside the SDK. For **Temporal** and **DBOS**, model calls become durable steps automatically but tools do **not**: wrap them with `activity_as_tool()` (Temporal) or `@DBOS.step()` (DBOS) — see [EAS-09.01](../spec/controls/durable-state.html). Dapr and Restate were not inspected. Without an integration, the SDK's only durable artifact is a serialized `RunState`. |
| Not covered | Realtime/voice agents, the sandbox-agent harness (`SandboxAgent`) beyond its `Memory()` capability, the experimental Codex tool. |

## Concept mapping

| EAS entity | Native concept | Notes / gaps |
|---|---|---|
| Workflow | The starting `Agent` and the agents reachable from it, plus `RunConfig.workflow_name` (trace name) | The SDK has no versioned workflow identity. `workflow_name` is a trace label only. Workflow `id`/`version` must come from your own code and be put in `trace_metadata`. |
| Run | One `Runner.run*()` call, which produces a `RunResult` / `RunResultStreaming` | A chat conversation is several Runs. No `status` enum: the outcome is either a final output or an exception (`MaxTurnsExceeded`, `*GuardrailTripwireTriggered`, `ToolTimeoutError`, `ModelBehaviorError`, ...), or `result.interruptions` when the Run pauses. You map these to EAS statuses in `run.end` code. |
| Step | A **turn**. The `max_turns` docstring defines it as "one AI invocation (including any tool calls that might occur)". Traced as `turn_span()`. | This is close to EAS Step, but the SDK does not checkpoint at turn boundaries (see Checkpoint). |
| ModelCall | One LLM request, traced as `generation_span()`. Per-request usage is in `context.usage.request_usage_entries`. | There is no cost field. Cost must be computed from tokens and a price table. |
| Decision | `RunResult.raw_responses` / `new_items` (message, tool-call and handoff items) | Decisions stay in memory and in the session or trace. Nothing records them durably for replay unless you use a durable-execution integration. |
| Tool | `FunctionTool` (`@function_tool` / `@tool`), hosted tools, local execution tools, MCP tools, `Agent.as_tool()` | None of the EAS Tool attributes (`effect_class`, `egress`, `output_trust`, `data_access`, `idempotency`, `output_limit_tokens`, `required_scopes`) exists natively. Keep them in the manifest and in a registry keyed by tool name. |
| ToolRequest | A function-call item emitted by the model. Inside tool guardrails it is available as `ToolContext` (`tool_name`, `tool_call_id`, `tool_arguments`). | For hosted tools the request is executed on OpenAI servers inside the same model call, so application code never sees it as an interceptable object (except hosted MCP approvals). |
| PolicyDecision | `ToolGuardrailFunctionOutput` (`allow()`, `reject_content(msg)`, or a tripwire); approval decisions (`state.approve`/`reject`) | There is no rule identifier field. Put `rule_id` in the guardrail's `output_info` (every `ToolGuardrailFunctionOutput` constructor accepts it, and it is surfaced on `result.tool_input_guardrail_results[i].output.output_info`) or in a `custom_span`. |
| ActionIntent | None | **No native concept.** It can be approximated by `needs_approval` plus a pause, or by a tool input guardrail that commits an intent and returns `reject_content("queued as intent …")`. The ledger, executor and idempotency key are application code. |
| Principal / Credential | None. The application-defined `RunContextWrapper.context` is the only carrier. | **No native concept** of principal, tenant, scopes or actor chain. The context object is not sent to the LLM, which makes it the right place for identity. It *is* included in a serialized `RunState`. |
| Budget | `max_turns` (default **10**, `None` disables it); `ModelSettings.timeout` (per model-call attempt); `@function_tool(timeout=…)`; `ToolExecutionConfig.max_function_tool_concurrency`; `ModelRetrySettings.max_retries` | Only steps (turns) are bounded by default. Tokens, cost, Run wall time, per-tool call counts and tool output size have **no native limit**. |
| ContextItem | Input items, `instructions`, tool definitions, session history | No `kind`, `as_of`, `trust` or `truncated` metadata. Context can be shaped with `call_model_input_filter`, `session_input_callback`, `SessionSettings(limit=…)` and handoff `input_filter`. |
| Checkpoint | `RunState` (`result.to_state()`, `to_json()`/`to_string()`, `RunState.from_json()`) | It is captured only when your code calls `to_state()`, typically at an approval interruption or after `cancel(mode="after_turn")`. It is **not** written automatically at every Step and carries no Workflow version: the docs advise you to "store a version marker" alongside it. `from_json` does not authenticate the snapshot. |
| MemoryEntry | Sessions (`SQLiteSession`, `RedisSession`, `SQLAlchemySession`, `MongoDBSession`, `DaprSession`, `OpenAIConversationsSession`, `EncryptedSession`, custom `Session`) persist conversation history across Runs. The sandbox `Memory()` capability distils lessons into workspace files. | Neither stores provenance (writing Run, source, trust). `SQLiteSession` does not authenticate rows, and a session ID is not authorization. |
| Trace | Built-in tracing: `trace()` with spans `task_span`, `turn_span`, `agent_span`, `generation_span`, `function_span`, `guardrail_span`, `handoff_span`, `custom_span` | By default it is exported to the OpenAI Traces backend, with payloads included (see Evidence collection). The tracer is SDK-native, not OpenTelemetry. |

## Hook bindings

| Hook | Native mechanism | Status | Notes |
|---|---|---|---|
| [`run.start`](../spec/hooks.html) | Application code before `Runner.run()`; input guardrails with `run_in_parallel=False`; `RunHooks.on_agent_start` | adapter | Blocking input guardrails complete before the agent starts, but they receive only the user input (plus context) and run only for the **first** agent. The default `run_in_parallel=True` does **not** block: tokens may already be spent and tools may already have run before the tripwire fires. `on_agent_start` is documented as an observer. Credential minting and admission belong in a wrapper around `Runner.run()`. |
| [`model.before`](../spec/hooks.html) | `RunConfig.call_model_input_filter` (runs immediately before each model call and can rewrite instructions and input); `RunHooks.on_llm_start` / `AgentHooks.on_llm_start` | adapter | `call_model_input_filter` can transform the context but does **not** see usage: `CallModelData.context` is the application context object, not the `RunContextWrapper`. `on_llm_start` receives the `RunContextWrapper`, so `context.usage` (cumulative for the Run) is available there and it is the place for token and cost checks. An exception raised from either propagates unchanged out of `Runner.run` and the model call is not made (tested with a stub model). Hooks are documented as observers, but the SDK does not swallow their exceptions. |
| [`model.after`](../spec/hooks.html) | `on_llm_end(context, agent, response)` | native | Observe-only. `context.usage` is cumulative for the Run. |
| [`tool.before`](../spec/hooks.html) | **Tool input guardrails** (`@tool_input_guardrail`, `tool_input_guardrails=[…]`) on function tools and on local MCP servers; `needs_approval` (function tools, `Agent.as_tool`, `ShellTool`, `ApplyPatchTool`); MCP `require_approval`; `HostedMCPTool` `on_approval_request`; `ComputerTool.on_safety_check`; `on_tool_start` | **partial** | Tool input guardrails block: they can skip the call and return a message (`reject_content`) or raise a tripwire, and they receive `ToolContext` with `tool_arguments` and the app context. **Not covered:** `WebSearchTool`, `FileSearchTool`, `CodeInterpreterTool`, `ImageGenerationTool` (executed server-side inside the model call); `ComputerTool`, `ShellTool`, `ApplyPatchTool`, `LocalShellTool` (outside the guardrail pipeline); handoff calls; `Agent.as_tool()` (no tool-guardrail option); `HostedMCPTool` (only `require_approval` and `on_approval_request`). A local MCP `require_approval` callable does **not** receive call arguments. `on_tool_start` is an observer and fires only for local tools. |
| [`tool.after`](../spec/hooks.html) | **Tool output guardrails** (`@tool_output_guardrail`) on function tools and local MCP servers; `on_tool_end` | partial | Output guardrails can replace the output or raise a tripwire before the result returns to the model. They have the same coverage gaps as `tool.before`: hosted tool outputs (web and file search results, code interpreter output) and hosted MCP outputs enter the context with no client-side interception point. |
| [`delegate`](../spec/hooks.html) | `handoff(on_handoff=…, input_filter=…, is_enabled=…)`; `RunConfig.handoff_input_filter`; `Agent.as_tool(needs_approval=…, run_config=…, max_turns=…)` | adapter | The docs say to check authorization in `on_handoff` "before application side effects, and raise instead of returning when authorization fails". `input_filter` can narrow the history passed on. There is no credential or actor-chain object to narrow: scope narrowing must be implemented on your context object. Handoff input filters are **not supported** with server-managed conversations (`conversation_id`, `previous_response_id`). Tool guardrails do not apply to handoff calls. |
| [`state.checkpoint`](../spec/hooks.html) | `result.to_state()` + `state.to_json()`, called by application code | absent (native) / adapter (with Temporal, DBOS, Restate or Dapr) | No hook fires at Step boundaries, and the SDK persists nothing automatically except session items after the Run. A per-Step checkpoint requires one of the durable-execution integrations. With Temporal (`temporalio-openai-agents`) and DBOS (`dbos-openai-agents` 0.3.0), each model call is automatically an activity/step, but `@function_tool` tools are not: they run in workflow code unless wrapped with `activity_as_tool()` (Temporal) or decorated with `@DBOS.step()` (DBOS). *(Restate and Dapr per-Step semantics unverified: not inspected.)* |
| [`state.resume`](../spec/hooks.html) | `Runner.run(agent, RunState.from_json(...))` | adapter | There is no resume hook. Version checks and integrity verification must run before `from_json`: the SDK does not authenticate snapshots or record versions. |
| [`memory.write`](../spec/hooks.html) | Custom `Session` implementation (`add_items`); `session_input_callback` (read side) | adapter | Wrap or implement `Session.add_items` to attach provenance and drop or downgrade tainted items. Sandbox `Memory()` has no pre-write hook: `MemoryGenerateConfig` exposes only phase models and settings, `max_raw_memories_for_consolidation` and `extra_prompt` (a model instruction, not a deterministic filter). |
| [`run.end`](../spec/hooks.html) | Application code after `Runner.run()` returns or raises; `on_agent_end`; `error_handlers` (`max_turns`, `model_refusal`, `invalid_final_output`) | adapter | `on_agent_end` fires only on final output, not on exceptions. Use `try/except/finally` around `Runner.run()` to map exceptions to EAS statuses. |

**Blocking summary:** the only documented *blocking, deterministic, per-ToolRequest* interception points are tool input guardrails and approval rules (`needs_approval`, `require_approval`, `on_approval_request`, `on_safety_check`). `RunHooks` and `AgentHooks` are documented as observers ("observe the lifecycle"). Hosted tools other than hosted MCP have **no** client-side `tool.before` or `tool.after`. A Workflow that needs [EAS-02.01](../spec/controls/separation.html) or [EAS-04.02](../spec/controls/enforcement.html) coverage for them must leave them out of the agent, or accept and document that the model can trigger them freely.

## Evidence collection

### (a) Static signals for L1 controls

| Control | What to look for |
|---|---|
| [EAS-01.01](../spec/controls/pattern-selection.html) | Rung from code shape: one `Runner.run` with no tools means `single_call`. Python orchestration around several `Runner.run` calls means `fixed_workflow`. One agent with tools and `max_turns` > 1 means `agent`. `handoffs=[…]` or `Agent.as_tool()` means `multi_agent`. Compare with the manifest `rung`. |
| [EAS-01.02](../spec/controls/pattern-selection.html) | `rung_justification` is present when `handoffs` or `as_tool` are used. |
| [EAS-01.03](../spec/controls/pattern-selection.html) | Eligibility and routing rules live in Python (code before `Runner.run`, `is_enabled` callables, `tool_use_behavior=StopAtTools(...)`), not only in `instructions`. Routing by handoff alone is model judgement. |
| [EAS-02.01](../spec/controls/separation.html) | Every effectful `FunctionTool` has `tool_input_guardrails` or `needs_approval`. Every local MCP server sets `tool_input_guardrails`. `ShellTool`/`ApplyPatchTool` set `needs_approval` (default `False`). `ComputerTool` sets `on_safety_check`. Effectful hosted tools (hosted MCP) set `require_approval` to `"always"` or a per-tool map. Flag any hosted tool with egress or effects that has no gate. |
| [EAS-02.02](../spec/controls/separation.html) | Function tools have typed signatures or Pydantic fields (schemas are generated by `pydantic`). `strict_mode` is not set to `False`. Structured return annotations or `output_type` are present. `Agent.mcp_config` converts MCP schemas to strict. Scopes and output limit come from the manifest; the SDK has no field for them. |
| [EAS-03.01](../spec/controls/actions.html) | Manifest `effect_class` exists for every tool in `Agent.tools`, every MCP tool after `tool_filter`, and every hosted tool. |
| [EAS-04.01](../spec/controls/enforcement.html) | Each money, privacy, legal or safety rule in `instructions` or a platform `prompt` has a matching tool guardrail, approval rule, output guardrail or in-tool check. Input guardrails with the default `run_in_parallel=True` do not count as a backstop for tool effects. |
| [EAS-04.02](../spec/controls/enforcement.html) | A shared tool input guardrail (allow-list, argument bounds, taint, rate) is attached to every function tool and every local MCP server. `is_enabled` alone does not count: the docs say it "does not replace authorization". |
| [EAS-05.01](../spec/controls/bounds.html) | `max_turns` is passed explicitly and is not `None`. The default of 10 is finite. `MaxTurnsExceeded` (or `error_handlers["max_turns"]`) is mapped to `budget_exhausted` and not retried. Nested `Agent.as_tool(max_turns=…)` is also bounded. |
| [EAS-05.02](../spec/controls/bounds.html) | A check of `context.usage.total_tokens` against a limit in `on_llm_start` (`call_model_input_filter` cannot see usage). `ModelSettings.max_tokens` (per-request output tokens) alone does not count. No native Run token cap exists. |
| [EAS-05.03](../spec/controls/bounds.html) | `ModelSettings(timeout=…)` (per attempt; it "does not limit the full agent run"). `timeout=` on every async function tool. Sync (`def`) tools cannot take one: `@function_tool(timeout=…)` on a sync function raises `ValueError` ("only supported for async @function_tool handlers"), so tools that need a timeout must be `async def`. `client_session_timeout_seconds` on MCP servers (`None`/`0` disables it). A Run deadline around `Runner.run` (application code). |
| [EAS-05.05](../spec/controls/bounds.html) | A per-Run, per-tool counter in a shared tool input guardrail. Nothing native exists. |
| [EAS-05.06](../spec/controls/bounds.html) | A tool output guardrail, or in-tool truncation, for every function and MCP tool. `FileSearchTool(max_num_results=…)` (1–50; `None` or 0 means the provider default) and `WebSearchTool(search_context_size=…)` are the only hosted-tool size controls. |
| [EAS-05.08](../spec/controls/bounds.html) | Retry layers: (1) `ModelSettings(retry=ModelRetrySettings(...))`, runner-managed and opt-in; (2) the underlying `AsyncOpenAI` client, which retries certain errors **2 times by default** (openai-python) unless `max_retries=0` on a client installed with `set_default_openai_client`; (3) the SDK's automatic `conversation_locked` retry; (4) any decorator retries inside tools; (5) durable-engine activity retries. More than one active layer for the same dependency is a finding. |
| [EAS-06.01](../spec/controls/identity.html) | Tool signatures do not take `user_id`, `tenant_id` or similar parameters. Identity is read from `ctx.context` (`RunContextWrapper`/`ToolContext`), which is not sent to the LLM. |
| [EAS-06.02](../spec/controls/identity.html) | Tools that take model-supplied identifiers (order ID and the like) check ownership against `ctx.context` before acting. |
| [EAS-07.01](../spec/controls/untrusted-content.html) | Manifest `output_trust`, `data_access` and `egress` cover hosted tools: `WebSearchTool` and `HostedMCPTool` output is untrusted, `FileSearchTool` is likely private or untrusted, `CodeInterpreterTool` output depends on its inputs. Also covers MCP servers and session stores. |
| [EAS-07.02](../spec/controls/untrusted-content.html) | Agents that combine `WebSearchTool`, MCP tools or file reads (untrusted) with private-data tools and an egress tool (email, post, hosted MCP, `WebSearchTool` queries, rendered URLs) need a deterministic gate (tool input guardrail or approval) between them. Handoffs forward the full history by default. |
| [EAS-07.04](../spec/controls/untrusted-content.html) | Minimal `tools=[…]`. MCP `tool_filter` / `create_static_tool_filter(allowed_tool_names=…)`. `is_enabled` callables. Review `ToolSearchTool` with `defer_loading=True`, which lets the toolset grow at runtime. No `ShellTool`/`ComputerTool` on agents that do not need them. |
| [EAS-08.01](../spec/controls/context.html) | In-tool pagination or truncation with an explicit "partial" marker, or a tool output guardrail that truncates. `SessionSettings(limit=…)` or compaction for history. |
| [EAS-08.02](../spec/controls/context.html) | Structured facts come from typed function tools, not `FileSearchTool` similarity search. |
| [EAS-08.03](../spec/controls/context.html) | No tool takes free-form SQL or query strings. `CodeInterpreterTool`, `ShellTool` and the Codex tool are not given production-store credentials. |
| [EAS-09.01](../spec/controls/durable-state.html) | Approval-gated tools pause **before** invocation. Other tool calls in the same turn that do not need approval **do** execute before the Run pauses (tested with a stub model), so an approval gate does not hold back sibling effects. Effectful tools are approval-gated or idempotent. With Temporal or DBOS, tools are not activities/steps by default: wrap them with `activity_as_tool()` (Temporal) or `@DBOS.step()` (DBOS); only model calls are made durable automatically. |
| [EAS-10.01](../spec/controls/evidence-gated-change.html) | `instructions`, `model`, tool docstrings (they become descriptions) and `ModelSettings` are in version control. If `Agent(prompt={"id": …, "version": …})` uses platform prompt templates, `version` is pinned. Unpinned platform prompts are console-editable *(version-omitted behaviour unverified: the SDK passes `version` through unchanged and the OpenAI platform docs do not state the default; note `v1/prompts` is scheduled to shut down on 2026-11-30)*. |
| [EAS-10.02](../spec/controls/evidence-gated-change.html) | A runtime flag checked before `Runner.run` and in `is_enabled` callables (tools and handoffs re-evaluate `is_enabled` before invocation). For in-flight streamed Runs, `RunResultStreaming.cancel()`. Nothing native exists. |
| [EAS-12.01](../spec/controls/observability.html) | Tracing is enabled (not `tracing_disabled`, `OPENAI_AGENTS_DISABLE_TRACING`), `workflow_name` and `trace_metadata` are set, and a processor maps spans to the EAS tree (below). |
| [EAS-12.02](../spec/controls/observability.html) | `trace_include_sensitive_data=False`, or `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=0`, or `set_trace_processors([...])` with a redacting exporter. A redaction processor added with `add_trace_processor` does **not** satisfy the control (see below). |

### (b) Telemetry

**Built-in tracing.** Tracing is **on by default**. The default `TraceProvider` uses a `BatchTraceProcessor` that sends batches to a `BackendSpanExporter`, which exports to the **OpenAI Traces backend** (platform.openai.com/traces). Tracing is unavailable for organizations under Zero Data Retention.

**Payloads (EAS-12.02).** `trace_include_sensitive_data` **defaults to `True`**:

- `generation_span` stores LLM inputs and outputs.
- `function_span` stores tool inputs and outputs.
- Audio spans store base64 audio unless `trace_include_sensitive_audio_data` is disabled.
- When the flag is `False`, Responses spans omit request input and response output but keep `response_id` for official OpenAI endpoints.
- `trace_metadata`, `group_id` and custom span data are exported as given.

So by default, prompts, tool arguments and results leave the process for OpenAI's trace store.

**Redaction.**

- Processors are independent observers. A failing redaction processor does not stop other processors.
- `add_trace_processor()` keeps the default OpenAI exporter registered.
- The documented safe pattern is `set_trace_processors([BatchTraceProcessor(<own exporter>)])`. Your exporter copies the payloads, redacts them and drops the batch if redaction fails.
- Disabling tracing does not discard data that is already buffered.

**OpenTelemetry.** The SDK's tracer is not OpenTelemetry, and the docs list no first-party OTel exporter. OTel export goes through a custom `TracingProcessor` or a listed integration (for example Logfire, Arize Phoenix, Datadog, Langfuse, MLflow). Their attribute mapping is *(unverified: each integration is third-party, versioned outside the SDK and not inspected here)*.

**Span mapping to the EAS tree:**

| EAS span | SDK span | How to add `eas.*` |
|---|---|---|
| `eas.run` | `trace()` / `task_span` | `RunConfig(workflow_name=…, trace_metadata={"eas.workflow.id":…, "eas.workflow.version":…, "eas.run.id":…, "eas.tenant.id":…})`. Status and budget totals are written by the exporter from `run.end` data. |
| `eas.step` | `turn_span` (disable with `tracing={"include_task_and_turn_spans": False}`; keep it enabled) | Turn count is used for `eas.budget.steps.used`. |
| ModelCall | `generation_span` | The exporter computes `eas.cost.usd` from model and usage. |
| `execute_tool` | `function_span` (function and MCP tools only). MCP list-tools calls are also traced. | `eas.tool.*` from the manifest tool registry, keyed by tool name, added in the exporter. `eas.tool.args_fingerprint` is hashed in the guardrail. Hosted tool calls produce no `function_span`: they run server-side and appear only as output items on the `Response` attached to the model's `response_span` (`span_data.response`; the default OpenAI exporter serialises only `response_id` and `usage`). Map them to `execute_tool` in a custom processor. Local Computer, shell and apply-patch actions do get a `function_span`. |
| `eas.policy` | `guardrail_span` (agent input/output guardrails only; tool input/output guardrails emit no span) | Emit `custom_span("eas.policy", data={…decision, rule_id, point})` from the tool input guardrail. |
| `eas.intent` | none | `custom_span` from the intent-commit code. |
| delegate | `handoff_span`, `agent_span` | `eas.actor_chain` from your context object. |

## Framework pitfalls

| Pitfall | Controls |
|---|---|
| `max_turns=None` removes the only native bound. `error_handlers["max_turns"]` converts exhaustion into a normal final output, which hides `budget_exhausted`. | [EAS-05.01](../spec/controls/bounds.html) |
| Input guardrails default to `run_in_parallel=True`: the agent, including its tool calls, can run before the tripwire fires. | [EAS-04.01](../spec/controls/enforcement.html), [EAS-02.01](../spec/controls/separation.html) |
| Input guardrails run only for the **first** agent and output guardrails only for the **last**. Specialists reached by handoff are not covered. | [EAS-04.01](../spec/controls/enforcement.html), [EAS-04.02](../spec/controls/enforcement.html) |
| Tool guardrails skip hosted tools, `ComputerTool`/`ShellTool`/`ApplyPatchTool`, handoffs, `Agent.as_tool()` and `HostedMCPTool`. A policy attached "to all tools" is usually only attached to function tools. | [EAS-02.01](../spec/controls/separation.html), [EAS-04.02](../spec/controls/enforcement.html) |
| `ShellTool`/`ApplyPatchTool` default to `needs_approval=False`. `on_approval` alone does not enable approval. `ComputerTool` without `on_safety_check` proceeds and leaves flagged checks unacknowledged. | [EAS-02.01](../spec/controls/separation.html), [EAS-07.04](../spec/controls/untrusted-content.html) |
| `is_enabled` and MCP `tool_filter` control visibility, not authorization. A local MCP `require_approval` callable cannot see arguments. | [EAS-04.02](../spec/controls/enforcement.html), [EAS-06.02](../spec/controls/identity.html) |
| Calling a tool's `__wrapped__` bypasses schema validation, guardrails, timeouts and tracing. | [EAS-02.01](../spec/controls/separation.html) |
| Tracing is on by default, exports to OpenAI, and has `trace_include_sensitive_data=True`. A redaction processor added via `add_trace_processor` runs beside the default exporter, not in front of it. | [EAS-12.02](../spec/controls/observability.html) |
| ZDR organizations cannot use built-in tracing. Without a replacement processor there is no trace evidence. | [EAS-12.01](../spec/controls/observability.html) |
| Enabling `ModelSettings.retry` while the `AsyncOpenAI` client keeps its default retries means two retry layers. The SDK also always retries `conversation_locked`. | [EAS-05.08](../spec/controls/bounds.html) |
| Function-tool errors and timeouts default to model-visible messages (`failure_error_function` default, `timeout_behavior="error_as_result"`), which invites repeated calls. | [EAS-05.05](../spec/controls/bounds.html), [EAS-05.10](../spec/controls/bounds.html) |
| `ModelSettings.timeout` is per attempt. Function-tool `timeout` is documented for async tools. Nothing bounds the whole Run. | [EAS-05.03](../spec/controls/bounds.html) |
| Handoffs forward the full conversation by default. `nest_handoff_history` "does not redact". Server-managed conversations cannot use handoff input filters. | [EAS-07.02](../spec/controls/untrusted-content.html), [EAS-12.02](../spec/controls/observability.html) |
| `ToolSearchTool` with `defer_loading=True` lets the model enlarge its own toolset at runtime. | [EAS-07.04](../spec/controls/untrusted-content.html) |
| Platform prompt templates (`prompt={"id": …}`) can be edited in the OpenAI dashboard outside version control. | [EAS-10.01](../spec/controls/evidence-gated-change.html) |
| A serialized `RunState` includes the app context (secrets, PII) and tool arguments. `from_json` does not authenticate. No version is recorded. | [EAS-09.01](../spec/controls/durable-state.html), [EAS-06.01](../spec/controls/identity.html), [EAS-12.07](../spec/controls/observability.html) |
| A session ID is not authorization, and `SQLiteSession` has no integrity protection. Sessions shared across agents mix histories. | [EAS-06.07](../spec/controls/identity.html), [EAS-07.07](../spec/controls/untrusted-content.html) |
| `cache_tools_list=True` on MCP servers keeps serving a cached description after the server changes it. Without it, `list_tools()` is called every Run and a changed description is picked up silently. | [EAS-07.06](../spec/controls/untrusted-content.html) |

## Satisfying L1 in the OpenAI Agents SDK

**Shared gate.** A single tool input guardrail, attached to every function tool and every local MCP server, covers [EAS-02.01](../spec/controls/separation.html), [EAS-04.02](../spec/controls/enforcement.html), [EAS-05.05](../spec/controls/bounds.html) and the [EAS-07.02](../spec/controls/untrusted-content.html) gate:

```python
from agents import ToolGuardrailFunctionOutput
from agents.decorators import tool_input_guardrail

@tool_input_guardrail
def eas_gate(data):
    ctx = data.context                      # ToolContext: tool_name, tool_arguments, .context
    run = ctx.context                       # your RunCtx: principal, tenant, budgets, taint, counters
    spec = TOOL_REGISTRY[ctx.tool_name]     # manifest attributes
    run.tool_calls[ctx.tool_name] += 1
    if run.tool_calls[ctx.tool_name] > spec.max_calls:
        return ToolGuardrailFunctionOutput.reject_content("Tool call limit reached for this run.")
    decision = POLICY.evaluate(run, ctx.tool_name, ctx.tool_arguments)   # deterministic
    if decision.outcome != "allow":
        return ToolGuardrailFunctionOutput.reject_content(f"Denied by policy {decision.rule_id}.")
    return ToolGuardrailFunctionOutput.allow()
```

| Control | Guidance |
|---|---|
| [EAS-01.01](../spec/controls/pattern-selection.html) / [01.02](../spec/controls/pattern-selection.html) | Declare the rung in the manifest. Prefer Python orchestration around `Runner.run` (fixed_workflow) over handoffs where the route is known. Justify `handoffs` and `as_tool`. |
| [EAS-01.03](../spec/controls/pattern-selection.html) | Put routing and eligibility in Python before or around `Runner.run`. Use `is_enabled` and `StopAtTools` rather than instructions. |
| [EAS-02.01](../spec/controls/separation.html) | Attach `eas_gate` everywhere: `@tool(tool_input_guardrails=[eas_gate])` and `MCPServer*(tool_input_guardrails=[eas_gate])`. Set `needs_approval` (Shell/ApplyPatch) with an `on_approval` policy, `on_safety_check` (Computer), and `require_approval="always"` plus `on_approval_request` (hosted MCP). Do not attach effectful or egress-capable hosted tools you cannot gate. |
| [EAS-02.02](../spec/controls/separation.html) | Use typed parameters, Pydantic `Field` constraints and structured return types. Keep strict schemas. Record scopes and `output_limit_tokens` in the manifest registry that `eas_gate` reads. |
| [EAS-03.01](../spec/controls/actions.html) | Classify every entry in `tools`, every filtered MCP tool and every hosted tool in the manifest. CI fails if a tool name has no manifest entry. |
| [EAS-04.01](../spec/controls/enforcement.html) | For each prompt rule, add a deterministic check (`eas_gate` rule, output guardrail or in-tool check). Use `run_in_parallel=False` for any input guardrail that is meant to block. |
| [EAS-04.02](../spec/controls/enforcement.html) | Use `eas_gate` with the Run's credential scopes from `ctx.context`. Do not rely on `is_enabled` alone. |
| [EAS-05.01](../spec/controls/bounds.html) | Pass `Runner.run(..., max_turns=budget.steps)` and catch `MaxTurnsExceeded`, recording it as `budget_exhausted` with no retry. Bound `as_tool(max_turns=…)` as well. |
| [EAS-05.02](../spec/controls/bounds.html) | In `RunHooks.on_llm_start(context, agent, system_prompt, input_items)`, compare `context.usage.total_tokens` with the budget and raise a dedicated exception, which `run.end` maps to `budget_exhausted`. The exception propagates unchanged out of `Runner.run` before the model call. (`call_model_input_filter` cannot be used: `CallModelData.context` is the application context and has no `usage`.) |
| [EAS-05.03](../spec/controls/bounds.html) | `ModelSettings(timeout=…)`; `@tool(timeout=…, timeout_behavior="raise_exception")` where hanging is not recoverable; `client_session_timeout_seconds` on MCP; `asyncio.wait_for(Runner.run(...), budget.wall_time_s)` for the Run. |
| [EAS-05.05](../spec/controls/bounds.html) | Per-tool counter in `eas_gate` (above). |
| [EAS-05.06](../spec/controls/bounds.html) | A shared `@tool_output_guardrail` that measures tokens and returns truncated content with a "truncated" marker, attached to all function and MCP tools. Set `FileSearchTool(max_num_results=…)`. |
| [EAS-05.08](../spec/controls/bounds.html) | Choose one owner. Either keep the `AsyncOpenAI` defaults and leave `ModelSettings.retry` unset, or set `ModelSettings(retry=…)` and install `set_default_openai_client(AsyncOpenAI(max_retries=0))`. Document the choice. |
| [EAS-06.01](../spec/controls/identity.html) / [06.02](../spec/controls/identity.html) | Pass the Principal and tenant in `Runner.run(context=…)`. Tools read `ctx.context` and verify ownership of model-supplied IDs before acting. |
| [EAS-07.01](../spec/controls/untrusted-content.html) | Record `output_trust`, `data_access` and `egress` in the manifest for every tool, hosted tool, MCP server and session store. |
| [EAS-07.02](../spec/controls/untrusted-content.html) | Set `run.tainted = True` in a tool output guardrail on untrusted tools. `eas_gate` denies or escalates egress tools when tainted. Do not combine `WebSearchTool` with private-data and egress tools on one agent unless a gate sits between them. |
| [EAS-07.04](../spec/controls/untrusted-content.html) | Minimal `tools`, `create_static_tool_filter(allowed_tool_names=…)` on MCP servers, `is_enabled` per request. Avoid `defer_loading` on effectful tools. |
| [EAS-08.01](../spec/controls/context.html) | Paginate in tools (cursor argument) and mark partial results. Use the output guardrail above as a backstop. `SessionSettings(limit=…)` for history. |
| [EAS-08.02](../spec/controls/context.html) / [08.03](../spec/controls/context.html) | Use typed lookup tools with parameterised queries. No free-form query or code tools against production stores. |
| [EAS-09.01](../spec/controls/durable-state.html) | Make effectful tools `needs_approval` or idempotent. Do not put effects in the same turn before an approval pause. For durable Runs, use the Temporal or DBOS integration. |
| [EAS-10.01](../spec/controls/evidence-gated-change.html) | Keep instructions, tool docstrings, `model` and `ModelSettings` in the repo. Pin `prompt["version"]` or avoid platform prompts. |
| [EAS-10.02](../spec/controls/evidence-gated-change.html) | Check a flag service before `Runner.run` and inside `is_enabled` callables. For streamed Runs, call `cancel()`. |
| [EAS-12.01](../spec/controls/observability.html) | Set `workflow_name` and `trace_metadata`. Keep turn spans. Use a custom `TracingProcessor` or exporter that adds `eas.*` and ships to your OTel backend. Emit `custom_span` for policy and intent events. |
| [EAS-12.02](../spec/controls/observability.html) | `RunConfig(trace_include_sensitive_data=False)` (or the env var) **and** `set_trace_processors([BatchTraceProcessor(RedactingExporter(...))])`. Do not use `add_trace_processor` for redaction. |

```python
from agents import RunConfig, set_trace_processors
from agents.tracing.processors import BatchTraceProcessor

set_trace_processors([BatchTraceProcessor(EasRedactingOtelExporter())])  # replaces OpenAI default exporter
cfg = RunConfig(workflow_name="refunds", trace_include_sensitive_data=False,
                trace_metadata={"eas.workflow.version": "1.4.0", "eas.tenant.id": tenant_hash})
```

## Sources

- https://pypi.org/pypi/openai-agents/json (version 0.24.0)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/running_agents.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/agents.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/guardrails.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/tools.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/tracing.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/human_in_the_loop.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/mcp.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/handoffs.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/context.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/sessions/index.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/models/index.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/usage.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/results.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/streaming.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/docs/sandbox/memory.md
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/run_config.py (`DEFAULT_MAX_TURNS = 10`)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/run.py (`max_turns` docstring)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/lifecycle.py (`RunHooks`/`AgentHooks`)
- https://github.com/openai/openai-python/blob/main/README.md (client default retries)
- https://registry.npmjs.org/@openai/agents/latest (TypeScript 0.21.0)
- https://github.com/openai/openai-agents-js/tree/main/docs/src/content/docs/guides (running-agents, guardrails, tracing, tools, human-in-the-loop)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/run_internal/turn_preparation.py (`maybe_filter_model_input`: `CallModelData.context=context_wrapper.context`; exceptions re-raised)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/run_internal/run_loop.py (`on_llm_start` called with `RunContextWrapper` after the filter, before the model call)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/run_config.py (`CallModelData`)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/model_settings.py (`max_tokens`)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/tool.py (`_validate_function_tool_timeout_config`: sync tools reject `timeout_seconds`)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/tool_guardrails.py (`ToolGuardrailFunctionOutput.output_info`)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/run_internal/guardrails.py (`guardrail_span` only for agent input/output guardrails)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/run_internal/tool_execution.py (`function_span` for function and local action tools)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/models/openai_responses.py and https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/tracing/span_data.py (`response_span`, `ResponseSpanData.export`)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/sandbox/config.py and https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/sandbox/capabilities/memory.py (`Memory`, `MemoryGenerateConfig`)
- https://github.com/openai/openai-agents-python/blob/v0.24.0/src/agents/prompts.py (`Prompt.version` passed through)
- Stub-model behavioural tests against `openai-agents==0.24.0` (2026-11-11): raising from `call_model_input_filter` and `on_llm_start`; sibling tool execution before an approval pause; sync tool `timeout`; tool guardrail spans
- https://github.com/temporalio/ai-integrations/tree/main/python/openai_agents (Temporal: model calls are activities; `@function_tool` tools run in the workflow unless `activity_as_tool()`)
- https://github.com/temporalio/sdk-python/tree/main/temporalio/contrib/openai_agents (moved to `temporalio-openai-agents`)
- https://pypi.org/project/dbos-openai-agents/0.3.0/ and https://github.com/dbos-inc/dbos-openai-agents (`runner.py`: model calls are `@DBOS.step()`; tools only turnstile-ordered; README: decorate tools with `@DBOS.step()`)
- https://developers.openai.com/api/docs/guides/prompting/migrate-from-prompt-object (`v1/prompts` shutdown 2026-11-30; no version-omitted default stated)
