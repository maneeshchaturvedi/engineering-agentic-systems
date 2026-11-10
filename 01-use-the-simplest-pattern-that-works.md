---
layout: post
title: "Use the Simplest Pattern That Works"
order: 1
---

# Use the Simplest Pattern That Works

There is a predictable arc to how teams adopt agents. Someone builds a demo in an afternoon: a model, a handful of tools, a loop. It does something impressive. The demo becomes a project, the project grows sub-agents — a planner, a researcher, a writer, a critic — and within a quarter the team is operating a system whose behaviour nobody can fully predict, whose costs vary tenfold between similar inputs, and whose failures take days to diagnose. Then someone notices that ninety percent of what it does could have been a fixed sequence of three steps.

The first principle of agentic architecture is restraint. Every increase in autonomy buys flexibility and pays for it in reliability, latency, cost, testability and debuggability. The architect's job is to buy only as much autonomy as the problem genuinely requires.

## A ladder, not a menu

It helps to think of the options as rungs on a ladder rather than items on a menu, because each rung includes the costs of the ones below it and adds its own.

At the bottom is **deterministic code**. If the logic is known — an eligibility rule, a routing table, a compliance check, a calculation — write it as code. A language model can often get these things right, but "often" is the problem. Code that must be exactly right should not be delegated to a component that is right ninety-eight percent of the time, however impressive that percentage sounds. An LLM in this position adds cost, latency and an error rate to a problem that previously had none.

The next rung is **a single model call**: one transformation of unstructured input into structured output. Classify this message. Extract these fields from this contract. Summarise this ticket. There is no loop and no tool use; the model receives an input and returns a result in a defined schema. This is the workhorse of practical LLM engineering. It is easy to test, easy to cache, has predictable cost, and fails in ways you can measure.

Above that is **a fixed workflow with model steps**. The sequence of steps is known in advance, but some of them need language understanding. You might classify an inbound request, route it to one of four handlers depending on the classification, have each handler draft a response using a model, and validate the draft with deterministic rules before it goes anywhere. The control flow belongs to you. The model is called at specific points to do specific things. This pattern — sometimes called prompt chaining, routing or fan-out and aggregation, depending on the shape — covers a surprisingly large share of real business problems, and it inherits most of the testability of ordinary software.

Then there is **an agent** in the strict sense: a model that chooses tools in a loop, deciding at each step what to do next based on what it has learned so far. This is the right tool when the path genuinely depends on discovery. Investigating why a metric moved, researching an open-ended question, diagnosing a failure across several systems — these are problems where you cannot write the sequence of steps in advance because the next step depends on what the last one found. Here, autonomy is not a luxury; it is the point.

At the top are **multiple cooperating agents**. They multiply every cost of a single agent — tokens, latency, error compounding across hand-offs, difficulty of evaluation — and they should be reserved for situations with a concrete justification. We will come back to what those justifications are.

## The test for climbing a rung

The discipline that makes this ladder useful is a single question: *what specific requirement can the lower rung not meet?*

"It would be more flexible" is not an answer, because flexibility is only valuable when you need it, and you pay for it whether you need it or not. "The model might find a better path" is not an answer unless you can say why the paths you can write down are insufficient. A real answer sounds like: "The number and order of lookups depends on what the first lookup returns, and there are too many combinations to enumerate," or "The inputs are so varied that any fixed routing would send a large fraction to the wrong handler."

Requiring this justification in writing, as part of architecture review, changes behaviour more than any amount of exhortation. Engineers are rarely over-building out of carelessness. They over-build because the agentic version is more interesting to build, demos better, and the costs are invisible until production. A short design note that asks "why not the simpler pattern?" makes the costs visible at the point of decision.

## A worked example: handling replies

Consider a system that sends outbound messages on behalf of users and must handle the replies. It looks like a natural agent problem. Replies are unstructured, varied and sometimes ambiguous. Surely we want an agent that reads each reply and decides what to do?

Look more closely at what "decide what to do" means. Replies fall into a small number of categories: the recipient is interested; not now; wrong person, with a referral; unsubscribe; out of office; something else. For each category, the right action is a matter of business policy, not judgement. Interested replies go to a person. Unsubscribe requests must be honoured, immediately and every time, for legal reasons. Out-of-office replies reschedule the next message. Referrals create a new contact.

The genuinely hard part — understanding what an unstructured reply means — is a classification problem. That is a single model call with a schema for its output. Everything after it is routing, which is deterministic. The "agent" design would ask the model both to understand the reply and to decide the policy response, and the second half is exactly the part we must never get wrong. An unsubscribe must not be honoured "usually". It must be honoured by code.

Built as a classifier plus deterministic routing, the system is cheaper, faster and easier to test. You can measure classification accuracy against a labelled set. You can unit-test the routing. And when a new reply category emerges, you add a label and a route rather than hoping the agent's general reasoning copes.

## When multiple agents are justified

None of this means multi-agent systems are always wrong. There are four reasons that hold up under scrutiny.

The first is **context isolation**. A sub-agent can explore a large space — read fifty documents, make thirty tool calls — and return a compact summary, keeping the parent's context window small and focused. Without the sub-agent, all that exploration would accumulate in one context and degrade the parent's reasoning.

The second is **permission separation**. If one part of a task needs to read untrusted content and another needs to take consequential actions, separating them into agents with different credentials means a compromise of the first cannot reach the capabilities of the second. This is a security boundary, and it is one of the strongest reasons to split.

The third is **genuine parallelism**: independent sub-problems that can run concurrently and whose results can be combined.

The fourth is **independent ownership**: capabilities built, tested and versioned by different teams, where a clean contract between agents mirrors a clean contract between organisations.

What does not justify a multi-agent design is role-play. "A researcher agent, a writer agent and a manager agent" describes a human org chart, not a technical requirement. Each hand-off between agents is a lossy compression of context, each additional agent multiplies tokens and latency, and errors compound across hops in ways that are very difficult to trace.

## Restraint as a platform property

On a platform used by many teams, restraint cannot depend on every engineer making the right call every time. It has to be built into the defaults.

The most effective lever is to make the simple path the easy path. If the platform's templates, scaffolding and documentation start at "workflow with model steps," most teams will start there. If moving up to a full agent or a multi-agent design requires a short written justification, reviewed by someone who has seen these systems fail, the expensive patterns are used where they pay off and nowhere else.

The second lever is evidence. When a team is convinced their problem needs autonomy, the most productive response is not an argument but an experiment: build both versions against the same evaluation set and compare task success, cost and failure modes. Sometimes the agent wins, and then the decision is easy. Surprisingly often, the constrained version matches it on quality at a fraction of the cost, and the evidence settles a disagreement that opinion could not.

Restraint is not conservatism. It is the recognition that autonomy is a cost you pay for flexibility, and that the best architectures spend it deliberately, in the places where the problem demands it, and nowhere else.
