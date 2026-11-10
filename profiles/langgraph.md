---
layout: doc
title: LangGraph Profile
section: Profiles
framework: LangGraph
verified_version: "langgraph 1.2.20 (Python); langchain 1.4.9; langgraph-checkpoint 4.3.1; langsmith 0.14.17"
verified_on: 2026-11-10
status: draft
---

# LangGraph Profile

This profile maps the EAS [reference model](../spec/reference-model.html) and [hook contract](../spec/hooks.html) onto LangGraph. Every API name, default and behaviour below was checked against the official documentation on the date above; anything that could not be checked is marked **(unverified)**.

## Scope

| Item | Coverage |
|---|---|
| Version | `langgraph` 1.2.20 (PyPI, released 2026-11-05). Features marked "≥1.2" (node timeouts, error handlers, `set_node_defaults`, `RunControl` drain, `DeltaChannel`) are absent from earlier 1.x releases. |
| Agent layer | LangChain `create_agent` (`langchain` 1.4.9) and its **middleware**, which "run inside the compiled LangGraph that `create_agent` returns". `langgraph.prebuilt.create_react_agent` is **deprecated** in LangGraph v1; profiles and assessments treat it as legacy. |
| APIs | Graph API (`StateGraph`), Functional API (`@entrypoint` / `@task`), checkpointers (`langgraph-checkpoint-*`), stores. |
| Languages | Python is primary. LangGraph JS (`@langchain/langgraph` 1.7.3) is noted only where it differs materially (recursion-limit default, `RemainingSteps`). |
| Platform | LangSmith Deployment / Agent Server (custom auth, assistants, TTL, revisions) and LangSmith tracing are covered where they supply evidence; they are **optional**. A conformant system can be built on OSS LangGraph alone. |
| Out of scope | Deep Agents, LangGraph Studio, LangSmith evaluation features (EAS-10 L2+), provider-specific middleware. |

## Concept mapping

| Reference-model entity | Native LangGraph concept | Notes / gaps |
|---|---|---|
| Workflow | A compiled graph (`StateGraph(...).compile()` or `create_agent(...)`); on LangSmith, a graph in `langgraph.json` plus an **Assistant** (versioned configuration). | No native `workflow.version`, `rung` or `risk_tier`. Assistants are versioned ("Editing an assistant creates a new version") but those versions live in the platform, not in source control. |
| Run | One `invoke`/`stream` call on a `thread_id`. `runtime.execution_info.run_id` is "`None` when not provided in config". | A **thread** spans many invocations; an EAS Run should map to one invocation (one user turn) unless the Workflow defines otherwise. No native Run status enum; `budget_exhausted`, `stuck` must be mapped by the application. |
| Step | **Super-step** ("Nodes that run in parallel share one super-step"); in `create_agent`, one model→tools cycle spans more than one super-step (unverified). | Checkpoints are written at super-step boundaries, so the EAS Step boundary = super-step boundary. `recursion_limit` counts super-steps, not agent turns. |
| ModelCall | A chat-model invocation inside a node; in `create_agent`, the model node wrapped by `wrap_model_call`. | Token usage arrives on `AIMessage` usage metadata "when available" from the provider. |
| Decision | `AIMessage` (content and `tool_calls`) appended to state. | Recorded in the next checkpoint, but a model call placed before an `interrupt()` or in a retried node **is re-executed** (see pitfalls). |
| Tool | `@tool` / `BaseTool` with `args_schema`; MCP tools via `MCPAdapter` (beta). | No native `effect_class`, `egress`, `output_trust`, `data_access`, `required_scopes`, `output_limit_tokens`. Must be held in a side registry keyed by tool name. |
| ToolRequest | An entry in `AIMessage.tool_calls`; in middleware, `ToolCallRequest` (`request.tool_call['name']`, `['args']`). | Native data; becomes an effect only when `ToolNode` executes it. |
| PolicyDecision | None. `HumanInTheLoopMiddleware` decisions (`approve`/`edit`/`reject`/`respond`) are the closest native analogue. | Absent: `allow/deny/escalate` with `rule_id` must be produced by custom middleware. |
| ActionIntent | None. | Absent. The docs recommend idempotency keys derived from durable state and warn "Treat missing local state as unknown"; a ledger must be built outside LangGraph. |
| Principal / Credential | `context` (`runtime.context`, `ToolRuntime[Ctx]`) passed per invoke; on Agent Server, `config["configurable"]["langgraph_auth_user"]` populated by `@auth.authenticate`. | No credential minting, actor chain or scope narrowing. Docs: "Storing secrets in graph state is not recommended." |
| Budget | `recursion_limit` (super-steps); `ModelCallLimitMiddleware`, `ToolCallLimitMiddleware` (`run_limit`, `thread_limit`); node `timeout`; `RetryPolicy`. | No token, cost or Run wall-time budget. |
| ContextItem | Messages in `state["messages"]`; context editing / summarization middleware. | No `kind`, `as_of` or `trust` attributes. |
| Checkpoint | `Checkpoint` via `BaseCheckpointSaver` (`put`, `put_writes`, `get_tuple`, `list`), keyed by `thread_id` / `checkpoint_id`. | **Not tagged with graph version**: "LangGraph applies the latest graph immediately to every thread." |
| MemoryEntry | Store item (`store.put(namespace, key, value)`), namespaced by tuple. | No provenance or trust fields; add them to the value. |
| Trace | LangSmith trace (runs tree) or OpenTelemetry spans via `LANGSMITH_OTEL_ENABLED=true`. | No `eas.*` attributes; captures inputs/outputs by default. |

## Hook bindings

| Hook | Native mechanism | Status | Notes / coverage caveats |
|---|---|---|---|
| [`run.start`](../spec/hooks.html) | `create_agent`: `before_agent` middleware with `can_jump_to=["end"]`. Raw `StateGraph`: a first node, or a wrapper around `invoke`. Agent Server: `@auth.authenticate` / `@auth.on`. | `native` (create_agent) / `adapter` (StateGraph) | `before_agent` runs "once per invocation", so it fires again on every resume invocation. |
| [`model.before`](../spec/hooks.html) | `before_model` (can jump to `end`) or `wrap_model_call` (may short-circuit: "handler is called zero times"). | `native` (create_agent) / `adapter` (StateGraph) | In custom graphs, model calls are ordinary code inside nodes; wrap the model client or route every call through one node. |
| [`model.after`](../spec/hooks.html) | `after_model`, `wrap_model_call` (can return `ExtendedModelResponse` with a `Command` to update state). | `native` / `adapter` | Usage only "when available" from provider; streaming usage may need opt-in (OpenAI). |
| [`tool.before`](../spec/hooks.html) | `wrap_tool_call` (deny by not calling `handler` and returning a `ToolMessage`; substitute by returning a `Command`); `HumanInTheLoopMiddleware` (`interrupt_on`). | `native` for `create_agent`; `adapter` for custom `StateGraph` | Covers tools executed by the agent's `ToolNode`. Not covered: tools inside a sub-agent compiled with its own middleware list; provider-hosted / server-side tools (unverified); `Send`-dispatched nodes that perform effects directly. A tool raising `interrupt()` inside its body re-runs from the top on resume. |
| [`tool.after`](../spec/hooks.html) | `wrap_tool_call` (inspect/transform the result of `handler`); `PIIMiddleware(apply_to_tool_results=True)`. | `native` / `adapter` | Same coverage caveats as `tool.before`. `ToolErrorMiddleware` (langchain ≥1.3.14) converts exceptions to `ToolMessage`s. |
| [`delegate`](../spec/hooks.html) | Sub-agents are invoked as tools ("calling them as tools"), so the parent's `wrap_tool_call` sees the delegation call; subgraphs via `add_node(subgraph)`. | `partial` | Parent middleware does not propagate into the child agent (unverified; no documented inheritance); `context` and credential must be passed explicitly. `set_node_defaults` "is not inherited by subgraphs". No native actor chain. |
| [`state.checkpoint`](../spec/hooks.html) | Subclass/wrap `BaseCheckpointSaver.put` / `put_writes`; custom `serde` (`EncryptedSerializer`). | `adapter` | Wrapping `put` can block persistence but runs after the node already executed; it cannot validate before effects inside that node. State validation is better done in reducers / node code. |
| [`state.resume`](../spec/hooks.html) | No resume callback. Resume is `invoke(Command(resume=...), config)` or `invoke(None, config)`. | `adapter` | Wrap the resume entry point: read `graph.get_state(config)`, compare a stored version field with the deployed version, then refuse or migrate. |
| [`memory.write`](../spec/hooks.html) | Wrap/subclass the store (`BaseStore.put`); tools write via `runtime.store`. | `adapter` | Every write path (tools, nodes, background jobs) must use the wrapped store. |
| [`run.end`](../spec/hooks.html) | `after_agent` middleware; for raw graphs, code after `invoke` returns or catches `GraphRecursionError` / `GraphDrained`. | `native` / `adapter` | `after_agent` does not run if the graph raises (unverified); use a `try/finally` around `invoke` for totals. |

## Evidence collection

### (a) Static signals for L1 controls

| Control | What to look for in LangGraph code / config | Default bounded? |
|---|---|---|
| [EAS-01.01](../spec/controls/pattern-selection.html) | `create_agent` / a cyclic `StateGraph` with conditional edges back to the model ⇒ `agent`; acyclic `StateGraph` with fixed edges ⇒ `fixed_workflow`; multiple agents wired as tools / subgraphs ⇒ `multi_agent`. Compare with declared `rung`. | n/a |
| [EAS-01.02](../spec/controls/pattern-selection.html) | Manifest text only; no LangGraph signal. | n/a |
| [EAS-01.03](../spec/controls/pattern-selection.html) | Routing via conditional-edge functions / `Command(goto=...)` in code rather than an LLM router for rules that must be exact. | n/a |
| [EAS-02.01](../spec/controls/separation.html) | Every effectful tool is reached only through a `ToolNode` wrapped by blocking `wrap_tool_call` middleware (or an equivalent gate node). Finding: effects in a node that is not behind the gate, or in a node that calls the model and the effect in the same function. | No gate by default. |
| [EAS-02.02](../spec/controls/separation.html) | `@tool(args_schema=...)` (Pydantic / JSON schema); structured return types; a registry with `required_scopes`, `output_limit_tokens`. | Input schema inferred from signature; output schema and scopes absent. |
| [EAS-03.01](../spec/controls/actions.html) | A tool registry mapping each tool `.name` to `effect_class`; HITL `interrupt_on` keyed by the same names. | Absent. |
| [EAS-04.01](../spec/controls/enforcement.html) | For each rule in `system_prompt`, a matching check in `wrap_tool_call`, `before_model`/`after_model`, `PIIMiddleware(strategy="block")` or tool code. | n/a |
| [EAS-04.02](../spec/controls/enforcement.html) | `wrap_tool_call` middleware that checks allow-list, scopes from `runtime.context`, argument bounds, taint flag in state, and per-tool counters, returning a refusal `ToolMessage`. Placed first in `middleware=[...]` ("place critical middleware first"). | Absent. |
| [EAS-05.01](../spec/controls/bounds.html) | `recursion_limit` passed as a **top-level** config key (not under `configurable`), or `LANGGRAPH_DEFAULT_RECURSION_LIMIT`; `GraphRecursionError` caught and mapped to `budget_exhausted`; or `RemainingSteps` routing; `ModelCallLimitMiddleware(run_limit=...)`. | Python default is **10,007 super-steps** (≥1.1.4; 10,000 in 1.0.6–1.1.3): finite but not a meaningful bound; **does not count** as satisfying the control. JS default is 25. `ModelCallLimitMiddleware` limits default to "no limit". |
| [EAS-05.02](../spec/controls/bounds.html) | Custom `before_model`/`wrap_model_call` accumulating `AIMessage` usage metadata against a per-Run limit. `max_tokens` on the model only bounds one response. | **No native per-Run token budget.** |
| [EAS-05.03](../spec/controls/bounds.html) | Model `timeout=` on chat model; `add_node(..., timeout=...)` / `TimeoutPolicy(run_timeout=..., idle_timeout=...)` / `set_node_defaults(timeout=...)`; timeouts on HTTP/DB clients in tools; Run deadline around `invoke` (e.g. `asyncio.wait_for`, unverified as a documented pattern). | Model `timeout` has no documented default. Node timeouts are opt-in and **async-only** ("Sync nodes with a `timeout` are rejected at compile time"). No Run-level deadline. |
| [EAS-05.05](../spec/controls/bounds.html) | `ToolCallLimitMiddleware(tool_name=..., run_limit=...)` per tool (or a global instance) with `exit_behavior`. | Limits are `None` by default; at least one must be set. |
| [EAS-05.06](../spec/controls/bounds.html) | `wrap_tool_call` truncating the returned `ToolMessage` to the tool's `output_limit_tokens`; `ContextEditingMiddleware` is not a substitute (it clears old tool uses once context exceeds `trigger`, default 100000 tokens). | Absent. |
| [EAS-05.08](../spec/controls/bounds.html) | Inventory: chat model `max_retries` (**default 6**); `ModelRetryMiddleware` / `ToolRetryMiddleware` (`max_retries` default 2); node `RetryPolicy` (`max_attempts` default 3) or `set_node_defaults(retry_policy=...)`; retry decorators inside tools. More than one active layer per dependency is a finding. | SDK default (6) is an active layer unless `max_retries=0`. Node retries are opt-in in Python (diagram: "exhausted or absent") and JS ("Retries are opt-in"). |
| [EAS-06.01](../spec/controls/identity.html) | Tool signatures: no `user_id` / `tenant_id` model-visible args; identity read from `runtime.context` or `langgraph_auth_user` (the `runtime` parameter "is hidden from the model"). Note the stores doc example `get_user_info(user_id: str, runtime)` exposes `user_id` to the model: a finding if copied. | n/a |
| [EAS-06.02](../spec/controls/identity.html) | Tools that receive record IDs from the model check ownership against `runtime.context` principal before use. | n/a |
| [EAS-07.01](../spec/controls/untrusted-content.html) | Registry attributes `output_trust`, `data_access`, `egress` per tool (including MCP tools from `MCPAdapter`) and per retriever. | Absent. |
| [EAS-07.02](../spec/controls/untrusted-content.html) | For any agent whose tool set includes private-data, untrusted-input and egress tools: a deterministic gate (`wrap_tool_call` taint rule or `HumanInTheLoopMiddleware` on egress tools). | Absent. |
| [EAS-07.04](../spec/controls/untrusted-content.html) | `tools=[...]` per `create_agent` / `ToolNode`; per sub-agent tool lists. `ShellToolMiddleware` default `HostExecutionPolicy` ("Full host access") is a finding unless justified. | n/a |
| [EAS-08.01](../spec/controls/context.html) | Tools return cursors / `truncated` flags; `wrap_tool_call` truncation adds an explicit marker. | Absent. |
| [EAS-08.02](../spec/controls/context.html) | Structured facts fetched by typed tools / store `get` by key, not `store.search(query=...)` semantic search. | n/a |
| [EAS-08.03](../spec/controls/context.html) | No tool that accepts free-form SQL/query text from the model against production (e.g. SQL-agent tutorial patterns); parameterised query tools instead. | n/a |
| [EAS-09.01](../spec/controls/durable-state.html) | In any node (or tool) that calls `interrupt()`: no effectful call before the `interrupt()` line. Effects in their own node or in a `@task`. | n/a |
| [EAS-10.01](../spec/controls/evidence-gated-change.html) | Prompts, model ids, tool descriptions, graph code in VCS; on LangSmith, Assistant configs managed via API/IaC rather than UI edits. | n/a |
| [EAS-10.02](../spec/controls/evidence-gated-change.html) | A flag checked in `before_agent` / first node (or at the API gateway) that ends the Run without deploy. | **No native kill switch** in OSS. `RunControl.request_drain()` stops one in-flight run cooperatively. |
| [EAS-12.01](../spec/controls/observability.html) | LangSmith or OTel tracing enabled (`LANGSMITH_TRACING=true` / `LANGSMITH_OTEL_ENABLED=true`); `eas.*` attributes added (see below). | Tracing off unless configured. |
| [EAS-12.02](../spec/controls/observability.html) | `LANGSMITH_HIDE_INPUTS` / `LANGSMITH_HIDE_OUTPUTS` / `LANGSMITH_HIDE_METADATA`, `create_anonymizer([...])` on the `Client`, or redaction in an OTel processor; `PIIMiddleware` for model I/O. | **Inputs and outputs are captured** unless hidden. `PIIMiddleware` `apply_to_output` and `apply_to_tool_results` default `False`. |

### (b) Telemetry

| Today | Detail |
|---|---|
| LangSmith tracing | `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`; per-call `config={"tags": [...], "metadata": {...}}` or `ls.tracing_context(...)`. |
| OpenTelemetry | `pip install "langsmith[otel]"`, `LANGSMITH_OTEL_ENABLED=true`; `LANGSMITH_OTEL_ONLY="true"` to send only to OTLP; standard `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_RESOURCE_ATTRIBUTES`. Fan-out to other backends via an OTel Collector. |
| GenAI attributes | LangSmith maps `gen_ai.system`, `gen_ai.operation.name`, `gen_ai.prompt.{n}.*`, `gen_ai.completion.{n}.*`, `gen_ai.tool.name` and usage attributes; custom metadata as `langsmith.metadata.{key}`. Which exact `gen_ai.*` attributes the LangChain exporter emits for LangGraph spans (vs. ingests) is (unverified). |
| Span tree | Graph → node → model/tool runs. There is no `eas.step` span per super-step (unverified whether node spans carry `langgraph_step`; the step number is readable in config metadata per the recursion-counter docs). |

Adding `eas.*` attributes:

- **Run-level** (`eas.run.id`, `eas.workflow.id/version`, `eas.tenant.id`, `eas.principal.type`): pass in `config["metadata"]` on every invoke; with OTel they surface as `langsmith.metadata.eas.*` (mapping direction unverified for export) or set process-wide via `OTEL_RESOURCE_ATTRIBUTES` for `eas.workflow.version`.
- **Model / tool / policy spans**: in `wrap_model_call` / `wrap_tool_call`, open a child span with the OpenTelemetry API and set `eas.cost.usd`, `eas.tool.effect_class`, `eas.tool.output_tokens`, `eas.tool.args_fingerprint`, `eas.policy.decision`, `eas.policy.rule_id`.
- **Budgets and status**: compute `eas.budget.*.used` in middleware state; set `eas.run.status` in the `run.end` wrapper (map `GraphRecursionError` → `budget_exhausted`, `GraphDrained` → `waiting`).

## Framework pitfalls

| Pitfall | Behaviour (documented) | Controls |
|---|---|---|
| Node re-execution on resume | "The node restarts from the beginning of the node where the interrupt was called when resumed, so any code before the interrupt runs again." Also applies to parent nodes of an interrupted subgraph. | [EAS-09.01](../spec/controls/durable-state.html), [EAS-03.02](../spec/controls/actions.html) |
| Node re-execution on retry | "A retry re-runs the entire node function from the start … at-least-once"; writes from the failed attempt are discarded but external effects are not. | [EAS-09.01](../spec/controls/durable-state.html), [EAS-03.03](../spec/controls/actions.html), [EAS-05.08](../spec/controls/bounds.html) |
| Idempotency key generated in the effectful node | Key generated in-node is lost if the node never returns; "Derive the key from state that is already durable". | [EAS-03.03](../spec/controls/actions.html) |
| Default durability is `async` | `invoke` "defaults to `async`"; "small risk that LangGraph does not write checkpoints if the process crashes". `exit` saves nothing until the run ends. | [EAS-09.04](../spec/controls/durable-state.html), [EAS-09.03](../spec/controls/durable-state.html) |
| Crash before first durable checkpoint | Thread is "indistinguishable from a thread that was never invoked"; record admission outside the checkpointer. | [EAS-09.04](../spec/controls/durable-state.html), [EAS-05.12](../spec/controls/bounds.html) |
| Model call recomputed | A model call in the same node as `interrupt()`, or in a retried node, is re-issued, so the Decision is recomputed. Functional API replays "at the beginning of the **entrypoint**", restoring only `@task` results. | [EAS-09.05](../spec/controls/durable-state.html) |
| Latest code applied to paused threads | "Unlike workflow engines that pin a run to the version of code it started with, LangGraph applies the latest graph immediately to every thread." Renaming/removing a node an interrupted thread is about to enter fails the run; renaming a state key "drops the saved value". | [EAS-09.08](../spec/controls/durable-state.html), [EAS-09.09](../spec/controls/durable-state.html) |
| Time-travel replay hits real systems | "Replay re-executes nodes … LLM calls, API requests, and interrupts fire again." | [EAS-09.06](../spec/controls/durable-state.html) |
| Recursion limit default is effectively unbounded | Python default 10,007 super-steps; one agent turn consumes more than one super-step, so the limit is not a step count in EAS terms. | [EAS-05.01](../spec/controls/bounds.html) |
| Stacked retries | Chat model `max_retries` default 6 plus `ModelRetryMiddleware` (default 2) plus node `RetryPolicy` (default 3 attempts) ⇒ up to 6×3×3 attempts per logical call (arithmetic from documented defaults). `NodeTimeoutError` is retryable by default. | [EAS-05.08](../spec/controls/bounds.html), [EAS-05.09](../spec/controls/bounds.html) |
| `default_retry_on` retries broadly | Retries on any exception except a listed set (e.g. `ValueError`, `OSError`); for `requests`/`httpx` only 5xx. Retrying a node that performed an effect duplicates the effect. | [EAS-05.08](../spec/controls/bounds.html), [EAS-03.06](../spec/controls/actions.html) |
| Tool limit "continue" mode | `ToolCallLimitMiddleware` default `exit_behavior="continue"`: the model is told the call was blocked and "decides when to end". Not a terminal `budget_exhausted`. | [EAS-05.05](../spec/controls/bounds.html), [EAS-05.10](../spec/controls/bounds.html) |
| Sync nodes cannot time out | Node `timeout` is async-only; sync nodes are rejected at compile time if given one. `request_drain()` "does not cancel running asyncio tasks or kill threads". | [EAS-05.03](../spec/controls/bounds.html) |
| Middleware coverage gaps | Middleware is passed to one `create_agent`; sub-agents built with their own `create_agent` need their own list (inheritance unverified); `set_node_defaults` "is not inherited by subgraphs". | [EAS-02.01](../spec/controls/separation.html), [EAS-04.02](../spec/controls/enforcement.html), [EAS-06.04](../spec/controls/identity.html) |
| Bare `try/except` around `interrupt()` | The interrupt exception is caught; `interrupt()` also bypasses retry policies and error handlers. | [EAS-09.02](../spec/controls/durable-state.html) |
| `InMemorySaver` / `InMemoryStore` in production | Documented as for experimentation; state lost on restart. | [EAS-09.02](../spec/controls/durable-state.html), [EAS-09.03](../spec/controls/durable-state.html) |
| Traces capture payloads | LangSmith captures inputs/outputs unless `LANGSMITH_HIDE_*` or an anonymizer is configured. | [EAS-12.02](../spec/controls/observability.html), [EAS-12.04](../spec/controls/observability.html) |
| Checkpoints hold everything | Full channel values at every super-step; no OSS TTL (LangSmith `checkpointer.ttl`, "If omitted, threads do not expire by default"). Encryption is opt-in (`EncryptedSerializer`). | [EAS-12.07](../spec/controls/observability.html), [EAS-09.10](../spec/controls/durable-state.html) |
| Identity as tool argument | Doc examples such as `get_user_info(user_id: str, runtime: ToolRuntime)` let the model choose the user. | [EAS-06.01](../spec/controls/identity.html) |
| Shell tool default | `ShellToolMiddleware` default `HostExecutionPolicy` gives "Full host access". | [EAS-07.04](../spec/controls/untrusted-content.html), [EAS-07.05](../spec/controls/untrusted-content.html) |

## Satisfying L1 in LangGraph

| Control | Guidance |
|---|---|
| [EAS-01.01](../spec/controls/pattern-selection.html), [EAS-01.02](../spec/controls/pattern-selection.html) | Prefer a fixed `StateGraph` over `create_agent` when the path is known; declare `rung` and justification in the manifest. |
| [EAS-01.03](../spec/controls/pattern-selection.html) | Put exact rules in conditional-edge functions or `before_agent` with `jump_to`, not in the prompt. |
| [EAS-02.01](../spec/controls/separation.html), [EAS-04.02](../spec/controls/enforcement.html) | One policy middleware first in `middleware=[...]` on **every** agent including sub-agents (snippet below). For custom graphs, route all tool calls through one gate node before `ToolNode`. |
| [EAS-02.02](../spec/controls/separation.html), [EAS-03.01](../spec/controls/actions.html), [EAS-07.01](../spec/controls/untrusted-content.html) | `@tool(args_schema=Model)` plus a `TOOLS` registry dict keyed by tool name holding manifest attributes; fail compilation if any tool lacks an entry. |
| [EAS-04.01](../spec/controls/enforcement.html) | For each prompt rule, add a middleware or tool-level check and a test; use `PIIMiddleware(..., strategy="block")` for data rules. |
| [EAS-05.01](../spec/controls/bounds.html) | `graph.invoke(x, {"recursion_limit": N, "configurable": {...}})`, catch `GraphRecursionError` → `budget_exhausted`; for agents also `ModelCallLimitMiddleware(run_limit=steps)`. |
| [EAS-05.02](../spec/controls/bounds.html) | `wrap_model_call` that sums usage into state and short-circuits once the limit is reached. |
| [EAS-05.03](../spec/controls/bounds.html) | `init_chat_model(..., timeout=30)`; async nodes with `set_node_defaults(timeout=TimeoutPolicy(run_timeout=...))`; client timeouts inside tools; Run deadline wrapper around `ainvoke`. |
| [EAS-05.05](../spec/controls/bounds.html) | `ToolCallLimitMiddleware(tool_name=t, run_limit=n, exit_behavior="error")` per tool (or `"end"` for single-tool limits), mapped to a terminal status. |
| [EAS-05.06](../spec/controls/bounds.html), [EAS-08.01](../spec/controls/context.html) | Truncate in `wrap_tool_call` to `output_limit_tokens` and append an explicit "truncated; use cursor X" marker. |
| [EAS-05.08](../spec/controls/bounds.html) | Pick one layer, e.g. `init_chat_model(..., max_retries=0)` + `ModelRetryMiddleware`, or keep SDK retries and use no node `RetryPolicy` on model nodes; comment the choice. |
| [EAS-06.01](../spec/controls/identity.html), [EAS-06.02](../spec/controls/identity.html) | Identity only from `runtime.context` / `langgraph_auth_user`; tools taking model-supplied record IDs verify ownership against it. |
| [EAS-07.02](../spec/controls/untrusted-content.html), [EAS-07.04](../spec/controls/untrusted-content.html) | Minimal `tools=[...]` per agent; set `state["tainted"]` in `wrap_tool_call` after untrusted tools and deny or `interrupt_on` egress tools when tainted. |
| [EAS-08.02](../spec/controls/context.html), [EAS-08.03](../spec/controls/context.html) | Typed lookup tools and parameterised query tools; no free-form SQL tool for autonomous agents. |
| [EAS-09.01](../spec/controls/durable-state.html) | Effects after `interrupt()` or in a separate node; in Functional API, inside `@task`. Use `durability="sync"` for effectful Workflows (L2, but cheap). |
| [EAS-10.01](../spec/controls/evidence-gated-change.html) | All prompts/models/tool descriptions in VCS; manage Assistants through the API from CI, not the UI. |
| [EAS-10.02](../spec/controls/evidence-gated-change.html) | `before_agent` (or first node) reads a remote flag keyed by workflow/version/tenant and jumps to `end` with status `cancelled`. |
| [EAS-12.01](../spec/controls/observability.html), [EAS-12.02](../spec/controls/observability.html) | Enable OTel export, add `eas.*` attributes in middleware, and set `LANGSMITH_HIDE_INPUTS/OUTPUTS=true` or an anonymizer before any export. |

```python
from langchain.agents import create_agent
from langchain.agents.middleware import (
    wrap_tool_call, ToolCallLimitMiddleware, ModelCallLimitMiddleware)
from langchain.messages import ToolMessage
from langchain.chat_models import init_chat_model

@wrap_tool_call
def policy_gate(request, handler):            # tool.before + tool.after
    call = request.tool_call
    decision, rule = evaluate(call["name"], call["args"], request.runtime.context)  # deterministic
    if decision != "allow":
        return ToolMessage(content=f"denied by {rule}", tool_call_id=call["id"])
    result = handler(request)
    return truncate(result, TOOLS[call["name"]].output_limit_tokens)

agent = create_agent(
    model=init_chat_model("<model>", timeout=30, max_retries=0),
    tools=[...],
    middleware=[policy_gate,
                ModelCallLimitMiddleware(run_limit=20, exit_behavior="end"),
                ToolCallLimitMiddleware(tool_name="search", run_limit=5, exit_behavior="error")],
)
agent.invoke(inp, {"recursion_limit": 60, "configurable": {"thread_id": tid}},
             context=Ctx(principal=..., tenant=...), durability="sync")
```

`request.runtime` on `ToolCallRequest` is (unverified); if it is absent, read identity from a `ToolRuntime` inside the tool instead.

## Sources

- https://pypi.org/pypi/langgraph/json (version 1.2.20, 2026-11-05); https://pypi.org/pypi/langchain/json; https://pypi.org/pypi/langgraph-checkpoint/json; https://pypi.org/pypi/langsmith/json; https://registry.npmjs.org/@langchain/langgraph/latest
- https://docs.langchain.com/oss/python/langgraph/interrupts
- https://docs.langchain.com/oss/python/langgraph/checkpointers
- https://docs.langchain.com/oss/python/langgraph/persistence (target of the former durable-execution URL)
- https://docs.langchain.com/oss/python/langgraph/fault-tolerance
- https://docs.langchain.com/oss/python/langgraph/graph-api
- https://docs.langchain.com/oss/python/langgraph/graph-api-control-flow
- https://docs.langchain.com/oss/python/langgraph/functional-api
- https://docs.langchain.com/oss/python/langgraph/use-time-travel
- https://docs.langchain.com/oss/python/langgraph/use-subgraphs
- https://docs.langchain.com/oss/python/langgraph/backward-compatibility
- https://docs.langchain.com/oss/python/langgraph/stores
- https://docs.langchain.com/oss/python/langgraph/observability
- https://docs.langchain.com/oss/python/migrate/langgraph-v1 ; https://docs.langchain.com/oss/python/releases/langgraph-v1
- https://docs.langchain.com/oss/python/langchain/middleware/overview ; …/middleware/built-in ; …/middleware/custom
- https://docs.langchain.com/oss/python/langchain/tools ; …/langchain/models ; …/langchain/guardrails ; …/langchain/human-in-the-loop ; …/langchain/multi-agent/subagents ; …/langchain/mcp/tools
- https://reference.langchain.com/python/langgraph/pregel/main/Pregel/invoke (durability default)
- https://docs.langchain.com/oss/javascript/langgraph/fault-tolerance ; https://docs.langchain.com/oss/javascript/langgraph/graph-api
- https://docs.langchain.com/langsmith/trace-with-opentelemetry ; https://docs.langchain.com/langsmith/mask-inputs-outputs
- https://docs.langchain.com/langsmith/custom-auth ; https://docs.langchain.com/langsmith/assistants ; https://docs.langchain.com/langsmith/configure-ttl
