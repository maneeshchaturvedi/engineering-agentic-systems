---
layout: doc
title: Implementation Guide
section: Implementation
order: 0
---

# Implementation Guide

The [reference architecture]({{ '/blueprint/' | relative_url }}) shows the complete picture. Almost no team should build the complete picture. This guide is about getting there in proportion to need: which components a Workflow needs at each level of autonomy and risk, which existing open-source tools fit each one, and what little is genuinely left to build.

Three rules run through it:

1. **Invest by stage, not all at once.** A single model call needs a timeout, a retry policy, redacted tracing, an evaluation set and a kill switch — not a policy engine. The [stages](stages.html) show what each step up the autonomy ladder adds, and why.
2. **Reuse where the problem is generic.** Durable execution, policy evaluation, token exchange, egress control, tracing and feature flags are solved problems. The [technology choices](choices.html) map each to open-source options, with licences checked and the paid or gated features named.
3. **Build only where the specification is new.** A small layer exists nowhere else, because it encodes the spec's semantics: run context carrying credential, taint and budgets across sub-agents; the action ledger; pinning tool descriptions; and the policy rules themselves. That layer is thin, and listed at the end of each choice.

There is no single stack to adopt. Choices are interchangeable within a concern, and each Workflow should use the least that its [risk tier]({{ '/spec/conformance.html#risk-tiers' | relative_url }}) requires.

## The progression at a glance

{% assign tg = site.data.tech.groups %}
| Stage | Configuration | Tier → level | What it adds |
|---|---|---|---|
{% for s in site.data.stages.stages %}| [{{ s.n }}](stages.html#{{ s.slug }}) | {{ s.title }} | {{ s.tier }} → {{ s.level }} | {{ s.adds | first }} |
{% endfor %}

## Where each concern enters

| Concern | Introduced at stage | Typical first step |
|---|---|---|
{% for g in tg %}| [{{ g.title }}](choices.html#{{ g.id }}) | {{ g.introduce_at }} | {% assign o = g.options | first %}{{ o.name }} |
{% endfor %}

## How the guide was derived

The components came from the essays; the boundaries between them were checked bottom-up with an [event storm](event-storm.html) of a Run's life, which also surfaced the design questions that the choices have to answer.
