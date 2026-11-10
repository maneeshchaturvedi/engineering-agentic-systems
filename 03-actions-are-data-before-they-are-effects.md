---
layout: post
title: "Actions Are Data Before They Are Effects"
order: 3
---

# Actions Are Data Before They Are Effects

Every engineer who has built a payment system has learned the same lesson, usually painfully: there is no such thing as exactly-once delivery across a network boundary. A request can time out after the remote system has already acted on it. Your process can crash after sending a message but before recording that it did. The only honest guarantee available is at-least-once delivery, and the only way to get exactly-once *effects* on top of it is to make repeated attempts harmless. We call that idempotency, and we have well-understood tools for it: idempotency keys, upserts, deduplication windows, the transactional outbox.

Agents need all of these tools, and they need one more idea that conventional services never did. This article is about that idea.

## The twist: a retry can produce a different action

In a conventional service, a retry sends the same request again. The idempotency key identifies the request, the remote system recognises it the second time, and nothing happens twice.

In an agent, a retry can go back through the model. Suppose an agent is partway through a step that drafts a follow-up email and sends it. The worker running it crashes, or a timeout fires, and the step is re-executed. The model runs again. Because the model is nondeterministic, it produces a slightly different email — a different opening line, perhaps a different subject. If the idempotency key was derived from the request content, which is the most natural way to build one, the second email has a different key. The system sees two distinct actions and sends both. The recipient gets two subtly different follow-ups a few minutes apart, and your customer looks careless.

It can be worse than duplicate wording. On a retry the model might choose a different recipient, a different amount or a different decision altogether. Content-based deduplication cannot help, because from the content's point of view these really are different actions.

The fix is to change where the idempotency comes from. Instead of identifying an action by *what it contains*, identify it by *what it is for*.

## Separate deciding from doing

The pattern has four steps.

First, the model **decides**. It does not perform an action; it produces a structured description of one. "Send follow-up number two in this sequence to this contact, using this draft." The description is data.

Second, the platform **commits the intent**. It writes the action description to a durable store — an action ledger — with an idempotency key derived from the logical intent: the tenant, the run, the type of action, the target, and its position in the sequence. Not the email body; not the wording. Crucially, this write happens in the same transaction as the checkpoint that records the agent's progress. The decision and the record that the decision was made are atomic.

Third, a separate executor **does** the action. It reads committed intents from the ledger, performs them against the outside world, records the external system's identifier for the result — the message ID, the record ID, the refund ID — and marks the intent complete.

Fourth, on any **retry**, one of two things happens. Either the agent resumes after the decision, because the decision was checkpointed and is not re-made, or, if something forces it to decide again, the ledger rejects the second intent because an intent with the same logical key already exists. The second draft is discarded. Nothing is sent twice.

This is the transactional outbox pattern, familiar from event-driven systems, with one adjustment for the agent world: the key is semantic, not syntactic.

## The things this makes possible

Once actions are data before they are effects, a surprising number of hard requirements become easy.

**Auditing** stops being a logging problem. The ledger is a complete record of every action the system intended and performed, with who it acted for, when, and what the external system returned. After an incident, "how many people received the wrong email?" becomes a query that returns an exact answer, not a forensic investigation that returns an estimate.

**Human approval** becomes a state transition. An action that needs approval is committed to the ledger in a "proposed" state. The executor ignores it until a person moves it to "approved." There is no special approval mechanism bolted on beside the agent; approval is just another step in the action's lifecycle. Batching approvals — a reviewer approving forty drafts on one screen — is a query over proposed actions.

**Dry runs** become trivial. Disable the executor, run the agent, and inspect the ledger. You see exactly what it would have done.

**Policy enforcement** has a natural home. Before an intent can move to executable, it passes through a policy check: is the recipient permitted, is the amount within limits, is this run trustworthy? The check runs on structured data, not on free text, which makes it far easier to write and test.

**Rate limiting and pacing** of real-world effects — not sending more than a certain number of messages per hour from one account, for instance — sit naturally in the executor, independent of how fast the agent reasons.

## Idempotency at the far end

The ledger guarantees you won't *intend* the same action twice. You still have to make sure the executor doesn't *perform* it twice, because the executor can crash too.

How you do this depends on what the target system offers. If it accepts idempotency keys, pass the ledger's key through, and the remote system handles deduplication. If it supports upserts keyed on an identifier you control, use that; repeated upserts converge on one record.

Many systems offer neither, and email-sending services are the classic example. Here the guarantee has to come from your side. The executor checks the ledger, takes a lease on the action so no other executor picks it up, sends the message, records the provider's message ID and marks the action done. There remains a narrow window: if the process crashes after the provider accepted the message but before the executor recorded it, a retry might send it again. You close that window by reconciliation. Before retrying an action whose state is uncertain, check the provider's delivery events for the message you tagged with your own identifier. It is worth saying plainly, in design reviews and in interviews, that this window exists and how you close it. Pretending it doesn't is how duplicates happen.

## Reversible and irreversible actions

Not every action is equally dangerous, and the architecture should reflect that.

Some actions are **reversible**: updating a field, adding an item to a list, creating a task. For these, the saga pattern works well. Each action is recorded with a compensating action — the previous value of the field, the removal of the list entry — and if a later step fails, the compensations run in reverse order. The compensations themselves go through the ledger, so a crash in the middle of a rollback resumes the rollback rather than leaving the system half undone.

Some actions are **reversible with delay**. A message can be placed in a send queue with a short cancellation window, the way many email clients offer "undo send." The effect becomes real only when the window closes. This is a useful middle ground for actions that are irreversible once they happen but where a brief delay is acceptable.

And some actions are simply **irreversible**: an email delivered, a public post published, money transferred to an external account. There is no compensation. The saga pattern is irrelevant here, and invoking it is a sign that someone hasn't thought the problem through.

For irreversible actions, the architecture has to put its caution *before* the action. That leads to an ordering principle worth stating explicitly: in a multi-step workflow, do all the reversible work first and the irreversible step last, behind a gate. If anything fails before the gate, everything can be undone. The gate itself — policy checks, and for high-stakes cases a human approval — is the last point at which a mistake can be caught.

## Does the ledger become a bottleneck?

This is the question an infrastructure-minded reviewer will ask, and the answer is reassuring. The ledger records one row per *side effect*, which is orders of magnitude fewer than model calls or state checkpoints. A system making hundreds of model calls per second might perform a few actions per second. It is an ordinary transactional workload, comfortably handled by a relational database partitioned by tenant. And because it doubles as the audit log, it replaces infrastructure you would have had to build anyway.

## The underlying idea

Underneath the mechanics is a shift in how we think about what an agent produces. A conventional program produces effects. An agent, done well, produces *decisions about effects*, which are data — durable, inspectable, checkable and approvable — and a separate, boring, reliable part of the system turns those decisions into effects exactly once.

That separation is what lets a nondeterministic component take real actions in the world without the system as a whole becoming nondeterministic about what it did.
