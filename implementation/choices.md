---
layout: doc
title: Technology Choices
section: Implementation
order: 2
---

# Technology Choices

For each concern in the [reference architecture]({{ '/blueprint/' | relative_url }}): when a team should invest in it, the open-source options that fit, which controls each helps satisfy, and what is left to build. Options within a concern are alternatives, not a bundle — choose by what you already run.

Licences were checked against each project's repository on {{ site.data.tech.verified_on }}. **Open** means an OSI-approved licence with no gated features relevant here; **open-core** means some relevant features need a commercial licence (named in the caveat); **source-available** means the licence is not OSI-approved. A tool helps satisfy a control only when it is configured to — and adopting one does not by itself establish conformance; the [assessment]({{ '/assessment/' | relative_url }}) still needs evidence.

<nav class="stage-nav">{% for g in site.data.tech.groups %}<a href="#{{ g.id }}">{{ g.title }}</a>{% endfor %}</nav>

{% for g in site.data.tech.groups %}
<section class="component" id="{{ g.id }}">
<h2>{{ g.title }}</h2>
<p class="refs">Components: {% for c in g.components %}<a href="{{ '/blueprint/' | relative_url }}#{{ c }}"><code>{{ c }}</code></a>{% unless forloop.last %}, {% endunless %}{% endfor %} · first needed at <a href="stages.html">stage {{ g.introduce_at }}</a></p>
<p><strong>When to invest.</strong> {{ g.invest | markdownify | remove: '<p>' | remove: '</p>' | strip }}</p>
<table>
<thead><tr><th>Option</th><th>Licence</th><th>Why it fits</th><th>Helps satisfy</th><th>Know before adopting</th></tr></thead>
<tbody>
{% for o in g.options %}<tr>
<td><a href="{{ o.url }}">{{ o.name }}</a><br><span class="tag">{{ o.model }}</span></td>
<td>{{ o.licence }}</td>
<td>{{ o.fit | markdownify | remove: '<p>' | remove: '</p>' | strip }}</td>
<td>{% for id in o.satisfies %}{% assign k = id | slice: 0, 6 | downcase %}<a href="{{ '/spec/controls/' | append: site.data.controls[k].slug | append: '.html' | relative_url }}#{{ id | downcase | replace: '.', '-' }}">{{ id }}</a>{% unless forloop.last %}<br>{% endunless %}{% else %}—{% endfor %}</td>
<td>{{ o.caveat | markdownify | remove: '<p>' | remove: '</p>' | strip }}</td>
</tr>{% endfor %}
</tbody>
</table>
<p><strong>Left to build.</strong> {{ g.build | markdownify | remove: '<p>' | remove: '</p>' | strip }}</p>
</section>
{% endfor %}

## The thin layer every stack builds

Across all concerns, the pieces no tool provides are the same handful, because they encode the specification's own semantics:

- **Run context** — the credential, taint flag, budgets and actor chain, carried across every model call, tool call and sub-agent, and bound to the framework through its [profile]({{ '/profiles/' | relative_url }}).
- **The action ledger** — intents with semantic keys, the executor's lease and reconciliation, and a review queue.
- **The policy library** — the rules that make the generic engines specific: the lethal combination, taint escalation, recipient constraints, identity never from arguments.
- **A manifest compiler** — turning the [agent manifest]({{ '/spec/manifest.html' | relative_url }}) into gateway, policy, budget and egress configuration, so the manifest is configuration rather than documentation.
- **Tool-description pinning, the token vault and the deletion orchestrator.**
