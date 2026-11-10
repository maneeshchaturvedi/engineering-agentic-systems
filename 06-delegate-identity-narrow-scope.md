---
layout: post
title: "Delegate Identity, Narrow Scope"
order: 6
---

# Delegate Identity, Narrow Scope

Ask a team that has shipped an agent who the agent *is* when it reads a customer's data, and you will often get a puzzled answer. It runs as the service, of course. The service has a database credential, an API key for the CRM, perhaps a cloud role with read access to a storage bucket. When the agent calls a tool, the tool uses those credentials. The question of whose behalf it is acting on is answered, if at all, by a filter somewhere in the tool code.

This arrangement has a name in security literature: the confused deputy. A program with broad authority performs actions on behalf of someone with narrower authority, and can be tricked — or can simply err — into using its own authority where it should have used theirs. Agents are the most persuadable deputies we have ever built. The principle in this article is that an agent must never act as itself. It acts on behalf of a principal, with credentials that carry that principal's identity and no more than the authority the task requires.

## Three ways data leaks

It helps to separate three different paths by which an agent can expose data, because each needs a different defence.

The first is the confused deputy itself. The agent's effective identity is broader than its user's, so any tool call — whether made correctly, made in error, or induced by a prompt injection — can reach data the user could not. This is the most important path, because it turns every other mistake into a breach.

The second is cross-tenant bleed through shared infrastructure. Caches, search indexes, vector stores, memory stores, prompt caches and traces are often shared across tenants for efficiency, with separation enforced by a filter at query time. When a filter is forgotten, or a cache key omits the tenant, one customer's data appears in another's results.

The third is exfiltration through output. The agent sees data it is legitimately allowed to see, and then sends it somewhere it shouldn't go — an external email address, a third-party tool, a URL.

Identity and scope are the primary defence against the first, contribute to the second, and are one layer of defence against the third.

## The agent acts on behalf of someone

When a user starts an agent run, the platform should mint a credential for that run. It identifies the user, the tenant they belong to, the specific capabilities the workflow needs — reading accounts, writing drafts, but not sending — and a short expiry. The tools the agent calls present this credential to the systems they reach, and those systems make their decisions based on it.

The standard shape for this is token exchange: the user's authenticated session is exchanged for a new, narrower token whose subject is still the user but which also records the agent as the *actor*. If the agent delegates part of the task to a sub-agent, the token is exchanged again, recording both actors in a chain. Every action can then be attributed precisely: this sub-agent, acting for that agent, acting for this user. Accountability is preserved through every hop.

The rule that makes this safe is that **each hop can only narrow scope, never widen it.** A sub-agent receives a subset of its parent's permissions. A research sub-agent that only needs to read documents gets a token that can only read documents, even if the parent could also send messages. Delegation becomes a way of reducing authority, which is the opposite of how service accounts tend to drift over time.

Not every run has a human behind it. Scheduled jobs and event-triggered workflows act on behalf of the system, but "the system" should never mean "the platform with all its permissions." Such runs should use a named service principal with an explicit, reviewable set of grants, specific to that workflow. When someone later asks why this workflow could read that data, the answer should be in a reviewed policy, not in the history of a shared credential.

## Narrowing at the infrastructure layer

The same principle applies to the cloud credentials the agent runtime uses. The runtime itself should get its identity from the platform — workload identity in the orchestrator, rather than static keys baked into configuration — so there is no long-lived secret to leak. On top of that, each run can receive short-lived cloud credentials narrowed for that run. Major cloud providers let you assume a role with an additional session policy that can only *reduce* the role's permissions, and attach tags such as tenant and run identifier that access policies and audit logs can use.

The effect is that a run acting for tenant A holds credentials that, at the cloud provider's own enforcement layer, can only reach tenant A's resources. If the run is compromised, the damage is bounded by something the agent cannot negotiate with.

## Enforcement belongs in the data layer

Carrying the right identity is half the work. The other half is making sure the systems that hold data use it.

Many teams stop at application-level enforcement: the tool receives the user's identity and adds the appropriate filter to its query. This is a reasonable first step and a dangerous last one. It depends on every tool, written by every team, applying the filter correctly every time, and on no injection ever persuading the agent to request something the filter doesn't anticipate.

The stronger design pushes enforcement down. Databases and query engines that support row-level and column-level security can apply policy based on the identity of the user a query is made for. Search and vector stores can be physically partitioned by tenant — a separate index or namespace per tenant — rather than sharing an index and relying on a metadata filter. Caches include the tenant, and where relevant the user, in every key. When enforcement lives in the data layer, an application bug produces a denied query and an alert instead of a breach.

There is a real cost here, and it is worth naming. For a data store to enforce a user's permissions, it has to know who the user is. Either the store authenticates end users directly, or a trusted service connects on their behalf using impersonation, with rules about which identities that service may assume. Impersonation is usually the practical choice. It also concentrates trust in the impersonating service, so its rules must be narrow, reviewed and audited. A sensible migration starts with application-level enforcement plus physical tenant separation, then moves enforcement into the data layer for agent workloads first, and then extends it to other consumers as part of a broader zero-trust effort.

## The model never chooses who it is

One detail deserves particular emphasis because it is so often gotten wrong. Tools should never accept identity or tenancy as arguments from the model.

If a tool takes a `tenant_id` parameter, the model fills it in, which means a prompt injection can fill it in. If a tool takes an `account_id` and looks it up without checking that the account belongs to the run's tenant, the model can be talked into requesting someone else's account. The tenant, the user and the permissions must come from the authenticated credential the run carries. The model may choose *which* of the user's accounts to look at; it must never choose *whose* accounts are in scope.

A particularly common version of this mistake appears in customer-facing agents. A customer writes, "Can you check on order 48213?" The agent extracts the order number and looks it up. Unless the lookup verifies that the order belongs to the authenticated customer, any customer can read any order by typing its number. The fix is the same: identity comes from authentication, never from text.

## Seeing too little

There is a second, quieter failure that permission-aware systems introduce, and raising it yourself in a design discussion shows you've built these systems rather than read about them.

When permissions filter results, the agent sees a subset of the data. Often that's exactly right. But the model usually doesn't know that a subset is what it's seeing. It answers confidently as though its view were complete. A sales assistant whose user can see three of an account's seven open deals will summarise "the account's pipeline" from three deals, and present that summary with the same confidence as a complete one.

The remedy is to make partial visibility explicit. When permissions remove results, the tool says so: "results limited to records you have access to; some records were excluded." The model can then qualify its answer, and the user knows to ask someone with broader access. Silent subsets are a correctness problem disguised as a security feature.

## Failing closed, and what it costs

Finally, decide what happens when the permission system itself is unavailable. For reads of customer data, the safe answer is to fail closed: if the platform cannot confirm a permission, it denies the request. That costs availability, and it is the right trade.

The cost can be softened with a short-lived cache of permission decisions, so that a brief outage of the permission service doesn't stop every agent. The cache introduces a window during which a revoked permission may still be honoured. Make that window an explicit number, measured in minutes, documented and agreed with your security team, rather than an accident of configuration.

## Audit at the same grain

Every tool call should be recorded with the run, the full actor chain, the tool, the permissions it used, the resources it touched and the policy decision. When an enterprise customer's security team asks for a record of everything your AI accessed on their behalf last quarter, the answer should be a query. That request will come, and the systems that can answer it easily are the ones designed with delegated identity from the start.
