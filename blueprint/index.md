---
layout: doc
title: Reference Architecture
section: Blueprint
wide: true
---

# Reference Architecture

This blueprint describes the components of a mature agentic platform: a platform where the guarantees the [specification]({{ '/spec/' | relative_url }}) requires are provided once, by shared components, rather than reinvented by every team. It is **informative**. No stack has to adopt this exact decomposition. It exists for three audiences:

- **Platform teams** deciding what to build around their agent framework.
- **Vendors** of gateways, policy engines, workflow engines, identity providers and observability tools, who can implement a component's interface and publish the controls it satisfies, so that adopters [inherit]({{ '/spec/conformance.html#inheritance' | relative_url }}) them.
- **Assessors**, who use it to turn structural findings into a remediation plan with a target design.

<figure class="diagram">
  <div class="diagram-scroll">{% include blueprint-diagram.svg %}</div>
  <figcaption>The EAS reference architecture. Solid arrows are the request path of a Run; dashed arrows are credentials, reads, tokens and outcome events. Select a component to see its role and the controls it satisfies.</figcaption>
</figure>

## How a Run flows through it

1. **Admission.** A Principal starts a Run. The `identity-broker` mints a short-lived credential naming the principal as subject and the agent as actor, scoped to the Workflow. The `scheduler` admits the Run through a durable queue according to capacity and priority, and `release-control` pins it to a Workflow version.
2. **Reasoning.** The `orchestrator` drives control flow and enforces bounds. It asks the `context-service` for the smallest sufficient, labelled context, and consults models only through the `model-gateway`, which owns retries, quotas and cost.
3. **The boundary.** Every ToolRequest goes to the `tool-gateway`, which checks it against the Tool's contract and asks the `policy-engine` for a decision. Read Tools run against systems of record that enforce the delegated identity at the data layer; their output is size-limited, labelled and marks the Run tainted if untrusted.
4. **Intent, not effect.** An effectful request becomes an ActionIntent, committed to the `action-ledger` atomically with the Run's checkpoint in the `state-store`. If policy requires it, the intent waits for the `approval-service`, which costs a database row rather than a held process.
5. **Execution.** A separate `executor` performs approved intents exactly once, through the `egress-proxy`, records the external reference and paces effects per account.
6. **Evidence.** Every component emits traces in the [common schema]({{ '/spec/telemetry.html' | relative_url }}) to the `telemetry-pipeline`, which redacts in-process (tokens go to the `pii-vault`) before anything is exported. The `outcome-store` joins Runs to business outcomes, and the `eval-platform` and `release-control` gate the next Change on that evidence.

## Components

{% assign domains = site.pages | where: "layout", "controls" | sort: "order" %}
{% for comp in site.data.components %}
<section class="component" id="{{ comp.id }}">
  <h3><code>{{ comp.id }}</code> <span class="plane">{{ comp.plane }} plane</span></h3>
  <p>{{ comp.role }}</p>
  <p class="refs"><strong>Interface:</strong> {% for i in comp.interfaces %}{{ i | markdownify | remove: '<p>' | remove: '</p>' | strip }}{% unless forloop.last %}; {% endunless %}{% endfor %}<br>
  <strong>Typically realised by:</strong> {{ comp.realised_by }}</p>
  <p class="refs"><strong>Satisfies:</strong>
  {% assign n = 0 %}{% for p in domains %}{% assign d = site.data.controls[p.domain] %}{% for c in d.controls %}{% if c.components contains comp.id %}{% assign n = n | plus: 1 %}<a href="{{ p.url | relative_url }}#{{ c.id | downcase | replace: '.', '-' }}" title="{{ c.title }}">{{ c.id }}</a> {% endif %}{% endfor %}{% endfor %}{% if n == 0 %}<em>No controls reference this component yet.</em>{% endif %}
  </p>
</section>
{% endfor %}

## Design rules the components share

These rules follow from the essays. A component that breaks one of them cannot be relied on to provide the controls listed for it.

1. **Nothing a model can influence decides a guarantee.** Gateways, policy, the ledger and the executor read identity from the Run's credential and decide in deterministic code.
2. **Every blocking component fails closed.** If the policy engine, identity broker or permission check is unavailable, the operation is refused, with any permission cache window stated explicitly.
3. **One owner per concern.** Retries live in the model gateway only; effects happen in the executor only; redaction happens in-process before every exporter.
4. **Waiting costs a row, not a process.** Approvals, timers and external events are state in the ledger and state store.
5. **Everything is tenant-scoped.** Queues, caches, indexes, memory, ledger partitions, traces and keys all carry the tenant.

## Implementing a component

A vendor or platform team implementing a component should publish:

- the component's identifier from this page and the interface it implements;
- the controls it claims to satisfy, with the evidence an assessor can collect for each (configuration it exposes, telemetry it emits using the [EAS attributes]({{ '/spec/telemetry.html' | relative_url }}));
- the hooks it binds, for each [stack profile]({{ '/profiles/' | relative_url }}) it supports;
- what it does **not** cover. For example, a tool gateway that cannot intercept a provider's hosted tools must say so, because those calls bypass it.

Adopters list implemented components in their [manifest]({{ '/spec/manifest.html' | relative_url }})'s `platform.components` section to inherit the controls.
