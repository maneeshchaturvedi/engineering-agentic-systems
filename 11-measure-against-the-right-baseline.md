---
layout: post
title: "Measure Against the Right Baseline"
order: 11
---

# Measure Against the Right Baseline

Every agent project eventually has to answer the same question: is it worth what it costs? The answers teams give are usually some version of "we saved X hours" or "it costs Y cents per task," and both are, on their own, almost meaningless. Hours saved compared to what? Cents per task that achieved what, compared to what else could have achieved it?

The principle in this article is that the cost of an agent should be measured per successful outcome, including every cost it actually incurs, and judged against the cheapest credible alternative — not against the most flattering one. That sounds like accounting. In practice it changes which agents get built, how they are designed and which optimisations are worth making.

## Cost per call is the wrong unit

The most visible cost of an agent is model tokens, and so teams track tokens per call or cost per run. These numbers are useful for engineering, and misleading as a measure of value.

They are misleading first because they leave out costs. A complete account of what one agent run costs includes the model tokens across every model it used; the infrastructure behind its tools — database queries, search, storage of its state and traces; the time people spend reviewing, approving and correcting its work; and the cost of runs that failed and had to be retried or redone by hand. The human time is very often the largest of these, and the one that nobody counts. An agent that is cheap in tokens but sends a third of its work to a person for approval may cost more in total than the process it replaced.

They are misleading second because they measure activity rather than results. A run that costs ten cents and produces a wrong answer is not cheaper than a run that costs thirty cents and produces a right one. The meaningful denominator is successful outcomes, which means each workflow needs a written definition of what success is. For a support agent, perhaps a ticket resolved without escalation and without the customer reopening it. For a research agent, perhaps a report a user acted on. For an outreach agent, perhaps a reply that led to a meeting.

Cost per successful outcome is the metric that connects engineering decisions to business value. It also explains why some apparently attractive optimisations aren't: switching to a model that costs half as much but succeeds on fewer tasks can increase cost per successful outcome even as the token bill falls.

## Outcomes that arrive late

The difficulty is that real outcomes often arrive long after the agent acted. Whether a message led to a meeting may not be known for weeks. Whether a resolved ticket stays resolved takes time to tell.

Handling this is a data engineering problem, and a familiar one. Each agent run records an identifier, the tenant, the entities it acted on, the workflow and version, and its cost components. Outcomes are captured as events from the systems where they happen — a reply received, a meeting booked, a ticket reopened — keyed by the same entities. A scheduled job joins the two within an attribution window: a meeting within three weeks of the message, say. Because outcomes keep arriving, the job recomputes recent windows as late data comes in, and a given day's figures are treated as provisional until its window has closed. Anyone who has built event-time joins in a streaming system will recognise the pattern.

The result is a table that tells you, for each workflow and version, how many runs happened, what they cost, how many succeeded, and what each success cost, with uncertainty attached.

## Lift, not totals

Even a correct cost per outcome can mislead, because it says nothing about outcomes that would have happened anyway.

Suppose an outreach agent is credited with a hundred meetings this month. Some of those prospects would have booked meetings regardless — through a template email, through a salesperson's own outreach, or on their own initiative. Crediting the agent with all hundred overstates its value, possibly by a lot.

The honest measure is **incremental** outcomes: the difference between what happened with the agent and what would have happened without it. The cleanest way to estimate that is a holdout — a random share of eligible cases that receive the alternative treatment instead of the agent. The lift is the difference between the two groups' success rates, and the cost per incremental outcome is the extra cost of the agent divided by the extra outcomes it produced.

Customers and product teams often resist holdouts, because everyone wants every case handled by the best available method. There are reasonable compromises: a small holdout, perhaps five or ten percent, presented as part of the product's measurement; staggered rollouts across comparable groups; or alternating periods of treatment. Where none of these is possible, it is worth saying plainly that the numbers show correlation rather than cause, and claiming value conservatively.

## Choosing the baseline

The most consequential choice in all of this is what to compare against, and it is where measurements most often go wrong.

There is a natural temptation to compare an agent to the most expensive way of doing the same work — usually a person. An agent that drafts outreach emails is compared with the salary of the person who would otherwise write them, and looks extraordinarily cost-effective. But that person was probably never going to write individual emails to every prospect. The realistic alternative was a templated sequence, which costs almost nothing in tokens and sends instantly. Against that baseline, the question becomes much sharper: does the agent's personalised email produce enough more replies to justify its cost? Sometimes it does. Sometimes the honest answer is that the agent's real value lies somewhere else — in reading and correctly routing replies, say, which a template genuinely cannot do.

The right baseline is **the cheapest credible alternative**: the simplest process that a sensible team would actually use if the agent didn't exist. A rule, a template, a classifier, an existing workflow. Choosing it deliberately, and saying so out loud, is one of the clearest signals of engineering maturity, because it shows you are trying to find out whether the agent is worth it rather than trying to prove that it is.

This connects back to the first principle in this series. Measured against the right baseline, a surprising number of agentic designs turn out to be beaten by simpler ones. The measurement isn't hostile to agents; it directs them to the places where they genuinely outperform the alternatives.

## Proxies for speed, outcomes for truth

Release decisions can't wait three weeks for outcome data. So teams gate changes on fast proxies — task success on an evaluation suite, policy compliance, user corrections — and use outcome data to check that the proxies are trustworthy.

That check should be explicit and periodic. Do versions that score better on the proxies also produce better outcomes? If a proxy stops tracking the outcome — because the product changed, or behaviour changed, or the proxy was being optimised in ways that don't help users — it has stopped being useful and should be replaced. A proxy is a hypothesis about what predicts value, and hypotheses need testing.

## Where the savings actually come from

With cost per successful outcome as the measure, optimisation becomes a disciplined exercise, much like reducing cloud spend: profile first, find what dominates, then apply levers in order of payoff and risk.

Profiling usually shows that a handful of workflows account for most spend; that input tokens dominate output tokens, because system prompts, tool definitions and context are sent on every call; and that a small fraction of runaway runs account for a disproportionate share of cost.

The levers follow. Removing waste carries no quality risk: hard limits that stop runaway runs, sending only the tool definitions relevant to the current step, and structured output that eliminates retries caused by malformed responses. Prompt caching carries no quality risk either: ordering every prompt so that its stable parts come first lets providers bill repeated input at a fraction of the normal price. Batch interfaces for work that doesn't need an immediate answer are typically substantially cheaper.

Routing between models carries quality risk and needs measurement. The idea is a cascade: try a smaller, cheaper model first, and escalate to a larger one only when the smaller model's result fails a check. The arithmetic is simple. If the large model costs 1.0 per call and the small one 0.1, and seventy percent of requests are handled successfully by the small model, the average cost becomes 0.1 for every request plus 1.0 for the thirty percent that escalate — 0.4 in total, a saving of sixty percent. That saving is real only if the small model's answers on that seventy percent are as good as the large model's would have been, and only if the check that decides escalation is reliable. Both must be established with the evaluation suite before routing goes live, and the escalation rate must be watched afterwards: if it drifts upward, the inputs have shifted and the economics with them.

Beyond routing, there are heavier options — training a smaller model on a larger one's outputs for a narrow, high-volume task — and the option that is easiest to forget: not using a language model at all where a conventional classifier or a rule does the job more cheaply and more reliably.

## The discipline underneath

Measuring against the right baseline is, in the end, a form of intellectual honesty applied to engineering. It asks what something actually costs, what it actually achieves, and what the realistic alternative would have achieved instead. Teams that adopt it build fewer agents, build them in the places where they genuinely outperform simpler approaches, and can defend every one of them with numbers.
