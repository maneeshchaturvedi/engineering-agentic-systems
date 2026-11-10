---
layout: doc
title: Stack Profiles
section: Profiles
order: 0
---

# Stack Profiles

A profile maps the [reference model]({{ '/spec/reference-model.html' | relative_url }}) and [hook contract]({{ '/spec/hooks.html' | relative_url }}) onto one agent framework. It tells adopting teams how to bind each hook and satisfy L1 in that framework, and tells assessors which signals to look for and which framework defaults are, or are not, bounded.

Profiles are informative, and versioned against the framework release they were checked against. Each states its verified version. Claims that could not be confirmed from the framework's documentation are marked *(unverified)*.

{% assign profiles = site.pages | where: "section", "Profiles" | where_exp: "p", "p.framework" | sort: "title" %}
<table class="index">
  <thead><tr><th>Profile</th><th>Verified version</th><th>Checked</th><th>Status</th></tr></thead>
  <tbody>
  {% for p in profiles %}
    <tr><td><a href="{{ p.url | relative_url }}">{{ p.framework }}</a></td><td>{{ p.verified_version }}</td><td>{{ p.verified_on }}</td><td>{{ p.status }}</td></tr>
  {% endfor %}
  </tbody>
</table>

The first three profiles cover the most widely adopted open-source agent frameworks by package downloads at the time of writing. Profiles for the Claude Agent SDK, Microsoft Agent Framework and Google ADK are planned.

## What the profiles show

Mapping frameworks onto the reference model shows a consistent pattern. These frameworks provide the **orchestration** layer well: control flow, a step or turn limit, interception points around model and tool calls, and some form of human-in-the-loop pause. In general they do **not** provide:

- an **action ledger** with semantic idempotency keys ([EAS-03]({{ '/spec/controls/actions.html' | relative_url }})). Human approval exists, but the effect still runs inside the agent loop.
- **delegated identity**: no native principal, credential or scope narrowing on delegation ([EAS-06]({{ '/spec/controls/identity.html' | relative_url }})).
- **Run taint** and **Tool trust or effect classification** ([EAS-07]({{ '/spec/controls/untrusted-content.html' | relative_url }})).
- **token and cost budgets** at Run level, as opposed to per-call limits ([EAS-05]({{ '/spec/controls/bounds.html' | relative_url }})).
- **version pinning** of in-flight Runs ([EAS-09.08]({{ '/spec/controls/durable-state.html#eas-09-08' | relative_url }})).

These gaps are not defects in the frameworks. They are the platform layer the [reference architecture]({{ '/blueprint/' | relative_url }}) describes, which has to be built or bought around whichever framework is chosen. The profiles show exactly where that layer attaches.

## Contributing a profile

A profile has seven sections: Scope, Concept mapping, Hook bindings, Evidence collection, Framework pitfalls, Satisfying L1, and Sources. Every API name, default and behavioural claim must cite the framework's documentation or source at a named version.
