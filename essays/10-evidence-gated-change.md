---
layout: post
title: "Evidence-Gated Change"
redirect_from: /10-evidence-gated-change.html
order: 10
---

# Evidence-Gated Change

In conventional software, change control is mature. Code changes go through review, run against test suites, deploy through staged rollouts and can be rolled back. A change that breaks a test does not ship.

Agentic systems have more kinds of change than ordinary software, and most of them bypass these controls. A prompt is edited to fix one complaint. A model is swapped for a cheaper or newer one. A tool's description is reworded. A retrieval setting is tuned. Each can alter behaviour as much as a code change, and often more unpredictably — yet they are frequently made in a configuration file or a vendor console, checked by trying a few examples, and shipped. The principle in this article is that every change that can alter an agent's behaviour goes through a gate, and the gate is evidence: an evaluation designed well enough to detect the regressions you care about.

## Why "it looks right" doesn't work

The traditional unit test asserts that a function given a certain input returns a certain output. That assumption fails for a nondeterministic component. The same input may produce a different, equally good answer each time, and occasionally a bad one. Exact-match tests are either too brittle to be useful or too loose to catch anything.

So teams fall back on inspection. They run a handful of examples, read the outputs, and decide whether things look better. This catches catastrophes and almost nothing else. A change that makes the agent slightly worse on a tenth of cases — a common outcome of a prompt edit aimed at fixing one specific complaint — is invisible in a dozen hand-checked examples, and very visible in production a week later.

Evaluating agents properly means borrowing from a different discipline: experimental design. An evaluation suite is an experiment, and like any experiment it has a sensitivity that can be calculated.

## Datasets built deliberately

The foundation is a dataset that represents what the agent actually faces. The best source is production itself: sampled real tasks, with personal data removed, so that the evaluation reflects the actual distribution of inputs rather than what engineers imagine it to be. To these, add every incident and every escalation, converted into a test case, so that the system's past failures become permanent checks. Add adversarial cases — injection attempts, edge cases, deliberately confusing inputs. And add synthetic cases for situations that are rare but important, which a production sample would include too seldom to measure.

The dataset should be stratified by the dimensions that matter: customer segment, task type, workflow branch, difficulty. A change that improves the common case while breaking a rare but important one should show up as exactly that, rather than disappearing into an average.

And the dataset should be versioned like code. A changed dataset means a changed baseline; comparisons between model or prompt versions are meaningful only when they use the same version of the data.

## Outcomes and trajectories

For an agent, the final answer is not the only thing worth checking. It matters how the agent got there.

**Outcome evaluation** asks whether the result was correct, grounded in its sources, compliant with policy and well-formed. **Trajectory evaluation** asks whether the path was sensible: the right tools chosen, with the right arguments, without unnecessary calls, and without any forbidden action along the way. An agent that reaches the correct answer by calling thirty tools where four would have done has regressed, even though its output passes. It now costs more, takes longer and has more opportunities to go wrong.

The metrics worth tracking follow from both: task success rate, precision of tool calls, groundedness and citation accuracy, rate of policy violations, steps and cost per task, latency to the first useful action, and the rate of failures that the agent could not recover from.

## Statistics, so you don't chase noise

Here is where most evaluation practices fall short, and where a little arithmetic changes the conversation.

Suppose your agent currently succeeds on 90% of tasks, and you want to know whether a change has dropped that to 85%. How many test cases do you need to detect that difference reliably? Using a standard two-proportion calculation with conventional settings — a 5% chance of a false alarm and an 80% chance of detecting a real drop — the answer is roughly seven hundred cases for each version, if the two versions are tested on independent samples.

Most teams' "golden sets" contain a few dozen examples. A fifty-case suite cannot reliably detect a five-point regression; it can detect a collapse. That is worth knowing, and worth saying, because it reframes the question from "did the evaluation pass?" to "what is the smallest regression our evaluation can see?" Every evaluation suite has a minimum detectable effect, and a team that knows its own can make honest statements: "our release gate will catch a three-point drop in task success." Very few teams can say that.

There are ways to do better with fewer cases. The most effective is a **paired design**: run both the old and the new version on exactly the same cases, and compare them case by case. For pass-or-fail outcomes, McNemar's test is the standard tool. Pairing removes the variation that comes from cases being different from one another, and so detects the same difference with considerably fewer cases. For tasks where the model's output varies a lot from run to run, sampling each case several times further reduces noise.

## Judges, calibrated

Many of the qualities we care about — was this explanation clear, was this message appropriate, did this summary capture what mattered — can't be checked with a simple rule. The common solution is to use another model as a judge. This scales well and can be very effective, provided it is treated as a measuring instrument that needs calibration, not as an oracle.

Calibration means having people label a sample of outputs and measuring how often the judge agrees with them, criterion by criterion, using a statistic such as Cohen's kappa that accounts for agreement by chance. A judge that agrees with humans on factual accuracy may disagree badly on tone. The calibration tells you which of its verdicts to trust.

Judges also have known biases. When comparing two outputs side by side, they tend to favour whichever is presented first, so the order should be randomised. They tend to prefer longer answers. And they tend to prefer outputs from models in their own family. Each bias can be measured and controlled.

The most useful rule is to prefer deterministic checks wherever possible. Whether output matches a schema, whether a cited source exists and supports the claim attached to it, whether a recipient is on the allowed list, whether a required disclosure is present — all of these can be checked by code, cheaply and exactly. Use the judge only for what code cannot assess. And when the judge model itself changes, recalibrate it, because a new judge is a new instrument.

## The gates

With a dataset, metrics, statistics and calibrated judges, change can be gated.

The first gate is in continuous integration. Every change to a prompt, model, tool description or workflow runs the evaluation suite. A statistically significant regression beyond a set threshold on a primary metric blocks the change. A regression on a secondary metric requires a written justification and a named person's sign-off. Because full suites can be slow and expensive, it helps to tier them: a smoke suite of a hundred or so cases on every change, the full suite before merging to the main branch and before release, and an extended suite with multiple samples per case overnight.

The second gate is **shadow** running. The new version processes real traffic alongside the current one, with its side effects disabled, and its decisions are compared with the current version's. Divergence is reviewed, case by case where it matters.

The third gate is a **canary**. A small share of real traffic goes to the new version, with live metrics — errors, policy rejections, escalation rate, cost per run — watched closely and an automatic rollback if any of them breach their threshold.

Behind all three sits a **kill switch**: the ability to disable a workflow, a specific version or a specific tenant's use of it instantly, without a deploy. Most of the time it is never used. When it is needed, nothing else will do.

## Offline evidence must predict online outcomes

There is one more check, and it is easy to forget. An evaluation suite measures proxies: task success on test cases, judge scores, policy compliance. The business cares about outcomes: problems resolved, customers retained, revenue generated. The value of the offline suite rests on the assumption that versions which score better on the proxies also do better on the outcomes.

That assumption should be tested periodically, by comparing offline scores with real results over time. If a proxy stops predicting the outcome — because the product changed, or users' behaviour changed, or the proxy was being gamed — it should stop being trusted, and the suite should be revised.

## What evidence buys

All of this can sound like heavy machinery for what used to be a quick prompt tweak. The point is that the quick tweak was never actually quick; its cost was simply deferred to production and paid by users. Evidence-gated change moves the cost to the moment of change, where it is cheaper, and turns arguments about whether a change is better into measurements.

It also changes how teams talk to each other. "I think the new prompt is better" invites a debate. "The new prompt improves task success by four points on the paired suite, with no significant change in policy violations, and our gate can detect a three-point drop" ends one.
