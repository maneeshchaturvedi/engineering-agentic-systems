---
layout: post
title: "Bound Everything"
redirect_from: /05-bound-everything.html
order: 5
---

# Bound Everything

A conventional service mostly bounds itself. A request handler does a fixed amount of work, calls a known set of dependencies and returns. When we need limits — timeouts, connection pools, request quotas — we add them at the edges, and they rarely trigger in normal operation.

An agent does not bound itself. How many steps it takes, how many tokens it consumes, how long it runs, how many times it calls a tool and how much data it pulls into its context are all decisions the model makes as it goes. Usually those decisions are reasonable. At sufficient volume, some of them won't be, and nothing in the model guarantees an upper limit. The principle that follows is blunt: every dimension along which an agent can consume resources needs an explicit, enforced limit, and that limit must live outside the model.

## The dimensions that need limits

It is worth listing the dimensions, because teams usually remember one or two and forget the rest.

**Steps.** A cap on the number of reasoning-and-action cycles in a run. Without it, an agent that gets confused can loop indefinitely.

**Tokens.** A cap on total input and output tokens per run, since a run with few steps but enormous context can be as expensive as one with many steps.

**Wall time.** A cap on elapsed time, so that runs which are slow for any reason — a stuck tool, a provider slowdown — release resources and report rather than hang.

**Cost.** A cap in currency, combining tokens across models of different prices with tool and infrastructure costs. This is the limit finance cares about, and the one that catches surprises the token cap misses, such as an unexpected escalation to an expensive model.

**Calls per tool.** A cap on how many times one tool can be called in a run. This catches a common failure in which the model calls the same search or lookup repeatedly with minor variations, hoping for a different result.

**Tool output size.** A cap on how much any single tool can return. An unbounded tool can flood the context window in one call, degrading the model's reasoning and multiplying the cost of every subsequent step.

**Concurrency.** A cap on how many parallel operations one run, one tenant or one product can have in flight, so that fan-out can't overwhelm the systems behind the tools.

**Retries.** A budget on how much retrying the system will do in aggregate, which we will come back to, because it is the limit that most directly separates a bad hour from an outage.

## Loops are a normal failure, not an exotic one

The failure these limits most often catch is the loop. A model calls a tool, gets a result it doesn't find satisfactory, and calls it again with slightly different arguments. Or it alternates between two steps, each undoing the effect of the other. Or a sub-agent delegates back to its parent, which delegates again.

In ordinary software, an infinite loop is a bug: you find it, fix it, and it is gone. In an agent, a loop is a probabilistic outcome. A prompt can make loops rarer, and a better model can make them rarer still, but at a hundred thousand runs a day, "rare" is a number you can plot. The engineering response is to detect and stop them deterministically.

Hard caps on steps and calls stop every loop eventually. Better still is to detect them early. If the same tool is called with the same normalised arguments several times in a run, or the sequence of steps repeats a cycle, the orchestration layer can end the run with a "stuck" status and escalate it, rather than letting it burn its full budget first. A stuck run that ends quickly and tells a person is a much better outcome than one that silently consumes its limit and fails.

## Model capacity is a shared, scarce resource

Some of the most important bounds are not per run but across the whole system, because the resource that agents depend on most is usually the scarcest one in the building.

A simple calculation makes the point. Suppose a platform starts 50 agent runs per second at peak, each lasting about a minute and making eight model calls of around 3,000 tokens each. By Little's law, about 3,000 runs are in flight at any moment. They make 400 model calls a second — 24,000 a minute — which at 3,000 tokens each is 72 million tokens per minute. That figure is far beyond the default throughput a model provider will grant a single account, and it is shared across every product and every tenant.

Compute, by comparison, is easy. Worker processes can be added in minutes. What cannot be added on demand is model throughput, and the same is often true of shared databases behind the agents' tools. The binding constraint on an agent platform is rarely CPU. It is a pool of tokens per minute that every team draws from at once.

A shared, scarce resource needs a scheduler, and the right model comes from cluster computing. Put a gateway in front of all model calls and give it hierarchical quotas: the organisation's total capacity is divided among products, each product's share among tenants, and each tenant's share among runs. Each level gets a guaranteed floor and can borrow capacity others aren't using. The limits are measured in tokens, not requests, because one request might be five hundred tokens and another a hundred thousand. Priority classes let interactive work — a person waiting for an answer — take precedence over background work that can wait.

Execution should be queue-based rather than request-driven. When a run starts, it enters a durable queue, and workers pull from the queue according to available capacity, not according to how fast work is arriving. When capacity is exhausted, work waits; it does not fail. At admission, low-priority work can be refused with a clear status when queues grow beyond a threshold, which is far better than accepting work that will time out. Work that doesn't need an immediate answer can go to providers' batch interfaces, which typically offer lower prices and separate capacity.

## How overload becomes an outage

The most dangerous unbounded quantity in an agent platform is retries.

When a model provider starts returning rate-limit errors, every layer of a typical stack tries to help. The provider client library retries. The agent framework retries the step. The tool wrapper retries the call. The workflow retries the run. If each layer retries three times, one logical call becomes twenty-seven attempts, arriving precisely when the provider is already overloaded. This is retry amplification, and it is how a brief capacity squeeze turns into a prolonged outage.

The defences are well known in site reliability engineering, and agents make them mandatory. Retry in exactly one layer, typically the gateway, and nowhere else. Use exponential backoff with jitter, and honour any retry-after signal the provider gives. Give each client a retry budget — retries limited to a fraction of its normal traffic, perhaps a tenth — and fail fast once the budget is spent. Put circuit breakers on each dependency so that a failing provider or region is avoided for a while rather than hammered.

## Spend as an alarm

The last bound is the one that protects the business from its own changes. A single prompt edit can double the average number of steps a workflow takes. A routing change can send most traffic to an expensive model. A new tool can return ten times more text than the one it replaced. None of these is an error in the usual sense, so nothing fails, and the first anyone hears of it is a monthly invoice.

The defence is to treat spend as a monitored signal with an automatic response. Track cost per workflow and per tenant per hour against a baseline. If spend exceeds a multiple of its baseline, page someone and pause new runs for that workflow until a person looks. That sounds drastic, but a paused background workflow costs very little, and an unnoticed tenfold cost increase over a weekend costs a great deal.

## Degrading on purpose

Bounds also define how the system behaves when it can't do everything. A well-designed platform has a deliberate degradation order, decided in advance rather than improvised during an incident.

A reasonable order is to shed background work first, then reduce lower-priority tenants to their guaranteed floor, then shrink context sizes, then route to smaller models that have been evaluated as acceptable for the workflow, and finally queue interactive work with honest status shown to users. One rule holds throughout: never shed a run partway through its side effects. A run that has sent the first of three messages, or debited one account in a transfer, must be able to finish or compensate. Capacity for in-flight work is reserved before new work is admitted.

## Why bounds belong outside the model

Every one of these limits could, in principle, be stated in a prompt: "Try to finish in under ten steps." "Don't call the search tool more than three times." Doing so is mildly helpful and entirely insufficient, for the same reasons that apply to every rule in a prompt. Limits must be enforced by the orchestration layer, the gateway and the scheduler, which count deterministically and stop when the count is reached.

Bounds are what turn an agent from a component that might do anything into one whose worst case you can state in advance. That statement — "no run can cost more than this, take longer than this, or call that service more than this many times" — is what lets an infrastructure team say yes to running agents on shared systems.
