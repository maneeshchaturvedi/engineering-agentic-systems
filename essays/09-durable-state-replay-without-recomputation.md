---
layout: post
title: "Durable State, Replay Without Recomputation"
redirect_from: /09-durable-state-replay-without-recomputation.html
order: 9
---

# Durable State, Replay Without Recomputation

Imagine an agent workflow that prepares a contract amendment, sends it to a manager for approval, waits — perhaps for three days, because the manager is travelling — and then, once approved, sends it to the customer and updates the account record. Halfway through those three days, your team deploys a new version of the agent. What happens to the run that is waiting?

This question separates teams that have operated agents in production from teams that have built demos. It touches every hard problem in long-running computation: whether progress survives a crash, where execution restarts, whether restarting reproduces the same decisions, and what happens when the code changed while the work was paused. Workflow engines and stream processors have solved versions of these problems for years. Agents bring them back with a twist, because the component making decisions is nondeterministic.

## Four concerns, often blurred together

It helps to separate four questions that are easy to conflate.

**Durability** asks whether progress survives the death of the process doing the work. The answer is to write the state of the run to a durable store at every step boundary — a checkpoint — so that nothing completed is lost when a worker dies.

**Resumability** asks where execution restarts after an interruption. The answer is from the last committed checkpoint for that run, which requires that the checkpoint captures everything needed to continue.

**Determinism** asks whether resuming takes the same path as before. This is where agents differ from ordinary workflows, and we will spend some time on it.

**Versioning** asks what happens when the code that defines the workflow has changed while a run was paused. This is the hardest of the four, and the one most often ignored.

## Waiting should cost nothing

The first practical consequence of durability is that waiting — for a human, for a timer, for an external event — should consume no compute at all. When a run reaches a point where it needs approval, it should write its checkpoint and release its worker. Three days of waiting should cost a row in a database, not a process, a thread or a connection held open.

This sounds obvious, but a surprising number of agent implementations wait by keeping a coroutine alive, awaiting a future that resolves when the approval arrives. That design works until the first deploy, restart or node failure, at which point every waiting run is lost. Any design that holds a process open to wait for a human is a design that loses work.

## Know what re-executes on resume

The second practical consequence is subtler, and it depends on understanding exactly how your framework resumes. Taking LangGraph as an example, since it's widely used for agent orchestration: with a checkpointer configured, the framework saves state at each super-step — each round of node executions — keyed by a thread identifier. A node can call `interrupt()` to pause for human input; the run's state is persisted, and later the run is resumed by sending the human's answer to the same thread.

The detail that catches teams out is that **on resume, the interrupted node runs again from its beginning**, not from the line where it paused. Any code in that node before the `interrupt()` call executes a second time. If that code sent an email, the email goes twice. The same is true of a retry: a node that fails and is retried runs again from the start, and the framework discards the failed attempt's writes to state but cannot discard what it did to the outside world.

The rule that follows is simple: side effects never sit before a pause point in the same step. They go in their own step, whose completion is recorded in the checkpoint, so that resuming never repeats them. LangGraph's functional interface makes this explicit with tasks, whose results are saved and returned rather than recomputed on resume. Note what that does and doesn't cover: on resume, the entrypoint function itself runs again from its beginning, and only the results of completed tasks are returned from the record. Anything outside a task — including a model call — runs again. Other frameworks have their own mechanisms. The question to ask of any of them is the same: what exactly re-executes when a paused or retried run resumes, and what is guaranteed to have been persisted before a side effect happens?

Related details are worth knowing. When several steps run in parallel and one fails, LangGraph keeps the results of the ones that succeeded, so a retry reruns only the failure. And frameworks typically offer a choice of durability mode, trading latency against safety: checkpointing synchronously before the next step begins, asynchronously alongside it, or only at the end. For workflows that take actions, choose the synchronous mode. An asynchronous checkpoint lost in a crash means the last step will run again, and if that step had an effect, the effect happens twice. Check the default rather than assuming it: in LangGraph, the default is asynchronous, so the safe mode has to be chosen explicitly.

## Replay without recomputation

Determinism is where agents and conventional workflows part ways.

Durable workflow engines like Temporal resume work by replaying the workflow's code against its recorded history. This works because workflow code is required to be deterministic: given the same history, it makes the same decisions. Anything nondeterministic — calls to external services, random numbers, the current time — must happen inside *activities*, whose results are recorded in the history and returned from it during replay, rather than being executed again. A model call is the clearest possible example of something that must be an activity. Calling a model directly from workflow code would make replay produce different decisions from the original run, which the engine would reject as a determinism violation.

Agent frameworks that checkpoint state rather than replaying code can arrive at the same place by a different route: on resume, they continue from saved state rather than re-deriving it. But they only continue from the last *checkpoint*, and that is coarser than it sounds. A model call made inside the step that was interrupted, retried or lost to a crash has not been checkpointed, so it is made again, and the model may answer differently. Checkpointing gives you this principle only if you arrange for it: put the model call in a step of its own, or in a task whose result is recorded, so that its answer is committed before anything acts on it.

Either way, the principle is that **decisions, once made, are facts.** The model is asked once. Its answer is recorded. Recovery reads the record.

There is one deliberate exception, and it needs care. Many frameworks support forking a run from an earlier checkpoint — sometimes called time travel — to debug a failure or to try a different prompt against the same situation. This deliberately re-executes from a past point, producing a new branch of history: the model calls, the API requests and the pauses for human input all happen again. It is extremely valuable for debugging and evaluation, and it is dangerous if the branch can reach real systems. A platform that offers replay must guarantee that, in replay mode, side-effecting tools are replaced with recorded or sandboxed versions. Debugging an incident must never cause a second one.

## Deploys: drain, don't kill

With durable state in place, deploys become manageable. Workers pull runnable work from a queue. When a new version is rolled out, old workers stop taking new work, finish the step they are currently executing within a time limit, write their checkpoint and exit. Runs that are paused — waiting for a person or a timer — aren't on any worker, so they are unaffected by the deploy itself. New workers pick up runnable work and resume it from checkpoints.

That handles the mechanics. It leaves the hardest question open.

## Versioning: when code changes under a paused run

Suppose a run started on version 12 of a workflow and is paused waiting for approval. Version 13 is deployed. When the approval arrives, which version resumes the run?

Three things can go wrong if the answer is "the new one." The **topology** may have changed: the step the run is paused at may have been renamed or removed, so there is nowhere to resume. The **state schema** may have changed: a field may have been renamed or given a different type, so the saved state no longer fits the code. And the **semantics** may have changed: the step still exists and the state still fits, but the step now does something different — a new prompt, a different tool — so the first half of the run followed one set of rules and the second half another. The third is the most insidious, because nothing fails; the run simply does something nobody designed.

There are three ways to handle this, and mature systems use them in combination.

The default should be **pin and drain**. Each run records the version it started on. Old versions remain deployed, with workers able to run them, until their last run finishes or is cancelled. New runs start on the new version. This is how established workflow engines approach the problem, with explicit support for routing work to the version that started it, and it is the only approach that guarantees a run follows one consistent design from start to finish.

Agent frameworks do not necessarily share that default, and it is worth checking rather than assuming. LangGraph, for example, deliberately does the opposite: it applies the latest graph to every thread, including threads paused mid-run, so a renamed node can leave a paused run with nowhere to resume and a renamed state key silently drops the saved value. On a framework like that, pin and drain is application work. Record the version in the run's state when it starts, keep workers for old versions deployed, and route each resumption to a worker running the version that started the run.

For small changes, allow **compatible changes only**. Additive changes — a new optional field in the state, a new step that no paused run will reach — can be applied in place. Renames and removals of anything a paused run might touch are forbidden. This can be enforced automatically: the platform keeps an inventory of where every paused run is waiting, and CI compares each change against that inventory and blocks deploys that would strand someone.

For breaking changes that must apply to in-flight runs, write **explicit migrations**: code that transforms version-12 state into version-13 state when a run resumes, tested against real saved checkpoints sampled from production (with personal data removed). This is the same discipline as migrating event schemas in a streaming system, and it deserves the same care.

## Checkpoints are a real workload

Finally, checkpoint storage is a dependency that needs capacity planning, not an implementation detail.

A checkpoint captures the full state of a run, which with message history and tool outputs can be tens or hundreds of kilobytes per step, written at every step of every run. At scale, that is a substantial write workload. Large objects — documents, big tool results — should be stored in object storage, with references in the checkpoint rather than copies. The store should be sharded by run. And checkpoints need a retention policy: kept in full while a run is active and for a debugging window afterwards, then compacted to the final state, then deleted.

That last point connects to privacy. A checkpoint contains everything the agent saw. Checkpoints belong in the inventory of places personal data lives, and in the path of every deletion request.

## Testing for it

The confidence that all this works comes from deliberately breaking it. In CI, kill workers at every step boundary and at points inside steps, resume the runs, and assert two things: that no side effect happened more than once, and that the final state is the same as an uninterrupted run. Before each deploy, take a sample of real paused checkpoints and resume them on the candidate version, and fail the deploy if any can't continue.

The underlying idea is simple to state and demanding to implement: an agent's progress should survive anything that can happen to the machines running it, and a decision made once should never be made again.
