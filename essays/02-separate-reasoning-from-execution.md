---
layout: post
title: "Separate Reasoning from Execution"
redirect_from: /02-separate-reasoning-from-execution.html
order: 2
---

# Separate Reasoning from Execution

The most common architecture for an LLM agent is also the most dangerous one. A model is given a list of functions it may call. When it decides to call one, the framework invokes the function directly with whatever arguments the model produced, returns the result to the model, and loops. The model reasons, and the same loop executes. There is nothing between the model's decision and its consequence.

This design works well in a demo, because in a demo the model's decisions are good and the consequences are harmless. In production, it means every guarantee the system needs — that arguments are valid, that the caller is permitted, that the action happens once, that it is recorded, that it respects business rules — either lives inside the model's reasoning or does not exist. And the model's reasoning is exactly the part of the system we cannot guarantee.

The principle is simple to state: **the model never calls the outside world directly.** It emits a structured request. Something else — deterministic, testable code — validates that request, decides whether it may proceed, and carries it out.

## Five layers with distinct responsibilities

A useful way to see the structure is as five layers, each with a clear job and, just as importantly, a clear list of things it must not do.

The **reasoning layer** is the model itself. Its job is to interpret input, form a plan, choose which capability to use next and draft language. It must not be responsible for enforcing permissions, tracking budgets, holding durable state or guaranteeing anything, because it cannot.

The **orchestration layer** is the control flow: the graph or workflow that determines what happens in what order, where the loops are, when the run stops, and where a human must approve something. It decides *when* the model is consulted and *what* it is consulted about. It must not perform business side effects inline, mixed into its control logic, because that makes retries and replays dangerous — a point the article on durable state develops in detail.

The **state layer** is the durable record of progress: what has been decided, what intermediate results exist, where the run is. It must not be mutable directly from model output without validation. State that the model can overwrite arbitrarily is state an injection can corrupt.

The **tool layer** is the set of typed capabilities the agent can request: look up a record, search documents, compute something, propose an action. Each tool has a contract — input schema, output schema, permissions it requires, size limits on what it returns. Tools must not trust their arguments blindly, and must not return unbounded output.

The **execution layer** is where side effects actually happen: messages sent, records changed, money moved. It is idempotent, policy-checked and recorded. It must never be invoked directly by the model.

## Why the boundaries matter

Drawing these lines buys four things, and each matters more as the system grows.

The first is **testability**. A system where the model calls functions directly can only be tested end to end, with all the nondeterminism that implies. With layers separated, each can be tested on its own terms. Tools get ordinary unit tests. Orchestration can be tested by replaying recorded model outputs through it, which is fully deterministic. Execution can be tested for idempotency and policy enforcement with no model involved at all. The model's own behaviour is tested the way it should be — statistically, with evaluation suites. You have turned one untestable system into four testable ones and one measurable one.

The second is **safety**. When permissions, budgets, idempotency and policy live in deterministic layers, a mistake by the model — or a successful prompt injection — cannot bypass them. The model can request anything it likes. The question of whether that request is honoured is answered by code that does not read instructions from retrieved documents.

The third is **change management**. A clean boundary means you can swap the model, or route some requests to a cheaper one, without touching how actions are executed. You can add a tool without rewriting the orchestration. You can tighten a policy without retraining or re-prompting anything. Each layer evolves at its own pace.

The fourth is **ownership**. On a platform shared by many teams, these boundaries become organisational interfaces. Product teams own their tools and prompts. The platform owns orchestration, state and execution. The contract between them — tool schemas, side-effect classes, permission scopes — is explicit and versioned. Without the boundary, every team reinvents retries, approvals and auditing, and each reinvention has its own bugs.

## What it looks like in practice

Consider an agent that helps support staff resolve customer issues, and can issue refunds.

In the naive design, the model has a `refund(order_id, amount)` function. It reads the conversation, decides a refund is appropriate, picks an amount and calls the function. The function calls the payment API. If the model chose the wrong order — perhaps because the customer's message mentioned an order number that isn't theirs — or the wrong amount, or if the call times out and the framework retries, the consequences land directly in the payment system.

In the separated design, the model does not have a refund function. It has a `propose_refund(reason_code)` tool. When it calls that tool, the tool layer looks up the order from the authenticated customer's identity, not from anything the model extracted from text. The amount is computed from the order record by business rules, not chosen by the model. The proposal is written to a durable record of intended actions. A policy check runs: is the amount under the automatic threshold? Has this order already been refunded? Is there any sign that this conversation has been manipulated? If the checks pass, an executor performs the refund with an idempotency key derived from the order and reason, and records the payment system's confirmation. If they don't, the proposal waits for a person.

The model's contribution is exactly what it is good at: understanding that the customer is asking for a refund, and why, and drafting a clear explanation. Every guarantee lives in code.

## The objection: isn't this over-engineering?

For a prototype, yes. If you are exploring whether a model can do a task at all, collapse the layers and move fast. The separation earns its keep the moment an agent can touch customer data or take an action that matters, and that moment usually arrives sooner than teams expect.

The more important answer is that the cost of the separation falls dramatically when the platform provides it. If every team must build its own action ledger, policy engine and tool gateway, the separation is expensive and teams will skip it. If the platform offers these as standard components, building an agent the safe way is no harder than building it the dangerous way. That is the real job of an agent platform: making the right architecture the default, so that each team gets its guarantees for free and spends its effort on the part only it can do — understanding its users' problems well enough to design good tools and good prompts.

There is also a retrofitting argument. Adding these boundaries after an incident is far more expensive than designing them in, because by then the coupling between reasoning and execution has spread through the codebase, and the incident has usually done damage that no later refactoring can undo.

## The model as an advisor

A helpful way to explain this principle to people outside engineering is to describe the model as an advisor rather than an operator. An advisor can be brilliant: perceptive, fast, creative, able to see options nobody else would. We still don't give advisors direct access to the bank account. We have them recommend, and we have a process — with controls, records and accountability — that decides what happens to the recommendation.

That is all this principle asks. Let the model advise as freely as it likes. Keep execution in hands that are predictable, accountable and testable.
