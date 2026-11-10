---
layout: post
title: "Observability Data Is Sensitive Data"
order: 12
---

# Observability Data Is Sensitive Data

Observability for conventional services is mostly about metadata. A trace records that a request arrived, which services it touched, how long each took and whether it failed. Logs record events and errors. Payloads, where they appear at all, are usually small and often deliberately excluded. The data needed to debug a service is, for the most part, data about the service rather than data about its users.

Agents invert this. To debug an agent, you need to see what it saw and what it said: the full prompt, including retrieved documents and tool results; the model's complete response; the arguments it passed to each tool and what came back. That is, by definition, a copy of everything the agent touched — customer records, messages, documents, personal details — taken at every step of every run. An agent's traces are among the most sensitive data a company holds, and they are usually stored with far less care than the systems they were copied from.

The principle in this article is that agent observability must be designed twice over: once to be genuinely useful for debugging, evaluation, cost and audit, and once to be governed like the sensitive data it is.

## What to capture

Start with usefulness, because a privacy-safe trace that can't diagnose anything protects nobody.

A good agent trace is structured as a tree: the run at the root, each step beneath it, and each model call and tool call beneath the step that made it. Every span carries a consistent set of attributes — the run identifier, tenant, workflow and version; for model calls, the model, input and output token counts, latency and cost; for tool calls, the tool, its arguments, the size of its result and any error; and throughout, the policy decisions made at each boundary. Using a standard such as OpenTelemetry lets these traces flow into the tracing and monitoring tools an infrastructure team already operates.

The consistency of that schema matters more than any individual attribute. If each team traces its agents in its own way, every question that crosses workflows — which tenant's runs are most expensive, which tools fail most often, how latency changed after a model upgrade — requires bespoke work. A common schema is one of the most valuable things an agent platform can provide, and one of the least glamorous.

From traces, derive the metrics that a platform team watches. Reliability metrics: the share of runs that succeed, fail unrecoverably or get stuck; latency to the first useful output and to completion; time spent waiting in queues. Quality signals visible in production: policy rejections, escalations to people, users correcting or retrying the agent's work, failures of grounding checks. And cost: tokens and currency per run and per successful outcome, broken down by workflow, tenant and version, with alerts on anomalies. Breaking every metric down by version is what makes regressions attributable; without it, a bad release shows up as a vague deterioration nobody can pin on a cause.

## Estimate the volume before choosing the tools

Agent traces are large, and it pays to calculate how large before committing to a design.

A platform making 400 model calls a second, each carrying around 3,000 tokens — roughly twelve kilobytes of text — produces close to five megabytes of prompt and response text every second, or around 400 gigabytes a day before counting tool inputs and outputs. In compressed columnar storage on object stores, that is a manageable amount of data. Sent in full to a hosted tracing product priced by volume, it can be very expensive indeed.

The usual answer is tiering. Keep metadata — timings, token counts, models, tools called, outcomes, costs — for every run, because it is small and supports nearly all aggregate analysis. Keep full payloads selectively: for every error, every policy rejection, every escalation, every run on a new version during its canary period, every run a user flagged, and a random sample of everything else so that analysis isn't biased towards failures. Hold recent traces in a fast, interactive tool for debugging, with short retention, and archive the rest in governed storage you control, partitioned by tenant and date, for audit, evaluation and cost analysis. That archive is also where traces can be joined with business outcomes and billing data, which is how cost per successful outcome gets measured.

## Redact before anything leaves the process

Now the second design. Because traces contain whatever the agent saw, they must be treated with the same care as the data they copy, and the most effective control is to reduce what they contain in the first place.

Redaction should happen inside the agent's own process, before trace data is exported anywhere. Personal data — names, email addresses, phone numbers, account identifiers, free-text fields likely to contain them — is detected and replaced with tokens that refer to entries in a secure vault. The tracing system receives the tokens. The real values exist only in the vault, behind access controls and audit logging. An engineer debugging a run sees the structure of what happened and the tokens; if they genuinely need a real value, they request it through a controlled process that records who looked and why.

This design has a valuable side effect for deletion, which the next section covers. When a person asks for their data to be deleted, removing their entries from the vault makes every token referring to them meaningless, in every trace, wherever it has been copied.

## Access to traces is access to customer data

Once traces are recognised as copies of customer data, the access rules follow. Engineers on the team that owns a workflow can see that workflow's traces. Access across tenants is restricted and logged. Support staff who need to investigate a specific customer's issue get time-limited access, granted for that purpose and revoked afterwards. None of this is unusual for a production database; it is unusual for an observability stack, which is exactly why it needs stating.

## Deletion has to reach traces too

Data protection laws give people the right to have their personal data deleted, and that right doesn't exempt logs. Agent systems make honouring it harder because they copy data into so many places. Traces are one. Others include the agent's saved state, its long-term memory, search and vector indexes built from its inputs, evaluation datasets assembled from production traces, caches of prompts and responses, the model provider's own retention, and — most often forgotten — the notebooks, tickets and local files where engineers pasted traces while debugging.

The defences work together. Minimise: redact and tokenise before storing, and store references instead of copies wherever possible. Tag: label every record with its tenant and the people it concerns when it is written, so deletion is a lookup rather than a search. Encrypt sensitive fields with keys held per tenant, so that removing a tenant can mean destroying a key. And run deletion as a tracked process: a request creates a job that fans out to every store holding agent data, confirms the data is gone by checking for it, and records evidence that it did. Where a store deletes data eventually rather than immediately — as some table formats do, where removed rows remain in older files until a compaction runs — the delay should be known, documented and within legal limits.

Evaluation datasets deserve particular attention, because they are deliberately permanent and built from production traces. Where possible, build them from redacted or synthetic versions of real cases, with personal details replaced by consistent placeholders, so they remain useful without containing anyone's data. Where real data is genuinely needed, tag it so it can be removed, and record the change to the baseline when it is.

## Closing the loop

Well-governed observability is not just a defensive measure. It is the raw material for nearly every other practice in this series. Traces become evaluation cases. Metrics by version make evidence-gated change possible. Cost attribution makes cost per outcome measurable. The action ledger and traces together let an incident be scoped exactly and diagnosed quickly. And when a single run goes wrong, its trace — combined with the ability to replay it from a checkpoint with side effects disabled — lets an engineer see precisely what happened, try a fix against the same inputs, and add the case to the evaluation suite so it can't silently happen again.

The point of treating observability data as sensitive is not to see less. It is to be able to see everything you need, for as long as you need it, without creating a second, less protected copy of your customers' data in the process.
