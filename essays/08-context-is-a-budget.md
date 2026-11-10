---
layout: post
title: "Context Is a Budget"
redirect_from: /08-context-is-a-budget.html
order: 8
---

# Context Is a Budget

Context windows have grown enormously, and with them a tempting idea: if the model can read a million tokens, why not give it everything that might be relevant and let it work out what matters? Retrieval becomes a matter of recall rather than precision, and the hard problem of deciding what an agent needs to know is handed to the model.

It doesn't work, for reasons that are partly economic and partly about how models behave. More context costs more on every call, adds latency, and — more subtly — tends to make reasoning worse. Relevant facts buried among irrelevant ones are more likely to be missed. Older material in a long context is attended to less reliably than recent material. Contradictory snippets from different times confuse rather than inform. The goal is not the largest context the model can accept. It is the smallest context sufficient for the task, assembled deliberately.

Treating context as a budget means three things: choosing what goes in, sizing it, and labelling it so the model and the people evaluating it know what it is.

## Not all context is the same

The first step is to recognise that the information an agent needs comes in kinds that differ in how often they change and how much they cost to produce, and that each kind has a natural source.

Some context is **static**: the system instructions, the policies the agent must follow, the definitions of its tools. This is the same for every run of a workflow and belongs in a fixed prefix at the start of the prompt, where it can be cached by the model provider and charged at a fraction of the usual price on repeated calls.

Some context changes **slowly**: profiles of the entities the agent works with, configuration, scores and classifications computed by batch pipelines. A risk score calculated overnight doesn't change between 10:00 and 10:05. This context should come from precomputed snapshots — compact documents per entity, refreshed when the underlying pipeline publishes new results — read cheaply at the moment the agent needs them.

Some context is **fresh**: what happened in the last few minutes, the current status of an order, a reply that just arrived. This needs a direct lookup on a path that reflects recent events, bounded to the specific items the agent asks about.

Some context is **unstructured knowledge**: documents, notes, manuals, past conversations. This is where retrieval belongs — search, ranking and selection of the passages most relevant to the task.

And some context requires **deep analysis**: large aggregations or joins across long histories. These are expensive and should be requested explicitly, run within strict limits, and often performed asynchronously, with the agent receiving a summary rather than the raw result.

The single most important observation in this list is about the second kind. **An agent should not recompute at query time what a pipeline has already computed.** If a tool call re-aggregates a month of activity to work out a score that a batch job produced last night, the design is wasteful at best and inconsistent at worst, because the agent's figure may disagree with the one the rest of the product shows. Agents should read the same precomputed results as everything else.

## The wrong primitive

A related mistake is to reach for vector search for everything. Retrieval-augmented generation has become so closely associated with LLM applications that teams sometimes embed structured facts — a customer's plan, an account's status, a score — and retrieve them by similarity. Similarity search is the right tool for finding passages of text that discuss something. It is the wrong tool for answering "what is this customer's current plan?", which has exactly one correct answer sitting in a database. Structured facts belong in structured lookups.

Equally risky is giving autonomous agents the ability to write and run arbitrary queries against production data stores. For an analyst's assistant, where a person reads the result, generated SQL can be enormously useful. For an agent acting on its own, it means unbounded cost, unpredictable query plans that can harm shared systems, and a path for injected instructions to reach the database. Parameterised query templates — a fixed set of questions the tool knows how to ask efficiently, with the model supplying only the parameters — give most of the flexibility with none of these risks.

## Every tool has a size limit

The second part of budgeting is sizing. Any tool that returns information to the model should have a contract about how much it returns.

That contract has a few parts. There is a maximum response size, measured in tokens rather than rows. Responses that would exceed it are summarised first, with details available on request, or paginated with a cursor the model can use to ask for more. And truncation is always explicit: the response says that it is partial, so the model doesn't mistake a subset for the whole.

Unbounded tool output is a bug in two ways. It is a context bug, because one oversized response can crowd out everything else the model needs and make every subsequent step more expensive. And it is a load bug, because a tool that can return a hundred thousand rows will, at volume, ask the systems behind it to produce a hundred thousand rows, many times a minute.

This matters especially for an infrastructure team. Agents are a different kind of client from people. A person browsing a dashboard sends a few queries a minute, follows predictable paths, and gives up if things are slow. An agent can make dozens of tool calls in a run, fan out across hundreds of entities, retry on errors, and run at any hour across every tenant at once. Agent traffic should be isolated in its own capacity pool or queue, rate-limited per tenant, and served from caches and snapshots wherever possible — always with the tenant as part of every cache key, since that is the most common route by which one customer's data appears in another's results.

## Freshness is part of the data

The third part of budgeting is labelling. Every fact an agent receives should carry the time it was true as of.

This sounds like a detail, and it pays off in three ways. It lets the model reason about staleness: if it can see that a status was computed this morning and a reply arrived ten minutes ago, it can account for the gap. It makes evaluation more precise, because a bad decision made on stale data is a different problem from bad reasoning, with a different fix — one belongs to the data pipeline, the other to the prompt or the model. And it makes staleness observable: when the age of a context section exceeds its agreed freshness, that is an alert on the pipeline, rather than an agent quietly making decisions on yesterday's information.

Freshness requirements differ by use. An agent deciding whether to send a follow-up message needs to know about replies within minutes, because following up after someone has already answered is a visible mistake. An agent producing a weekly priority list is fine with yesterday's scores. Rather than one global freshness target, define one per kind of context and per kind of decision, and let the platform refuse or flag an action whose required inputs are older than that action can tolerate.

## Context across long runs

Long-running agents face a version of the budget problem over time. Each step adds tool results and reasoning to the context, and a run of fifty steps can accumulate far more than the model can use well.

Three techniques help. **Compaction** periodically summarises older parts of the history, keeping decisions, open questions, identifiers and anything the agent has committed to, and discarding the detail that led there. **Sub-agent isolation** gives exploratory work — reading many documents, trying several searches — to a separate agent with its own context, which returns only a compact result to the parent. And **structured notes** let the agent write important findings to durable state and re-read them when needed, rather than relying on everything remaining in the window.

All three share a principle: the context window is working memory, not a log. What needs to persist should persist somewhere designed for it.

## Was the context enough?

Finally, budgeting implies measurement. If you are deciding what goes into an agent's context, you need to know when you got it wrong.

The most useful measurement separates retrieval from reasoning. For a set of test tasks, record which facts the correct answer depends on, and check whether those facts were present in the context the agent actually received. If they were missing, the problem is upstream of the model, and no prompt engineering will fix it. Track "answered without the needed information" as its own failure category, and you will find that a significant share of what looks like model error is really context error.

Context engineering is, in the end, ordinary information engineering: knowing where each kind of fact lives, how fresh it is, how much it costs to retrieve and how much of it the consumer can use. What's new is that the consumer is a model with a finite and expensive attention span, which makes getting it right worth considerably more than it used to be.
