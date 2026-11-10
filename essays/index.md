---
layout: default
title: Essays
section: Essays
---

# Essays

LLM-based agents put a nondeterministic, persuadable component at the centre of our systems: the part that decides what happens next. This series argues for one design stance: **the model proposes; a deterministic system disposes.** An introduction explains what agents do to distributed systems, and twelve principles show how to build around them.

Each principle is the rationale for one domain of the [EAS specification]({{ '/spec/' | relative_url }}).

{% assign articles = site.pages | where: "layout", "post" | sort: "order" %}
{% assign domains = site.pages | where: "layout", "controls" %}
<ol class="toc" start="0">
{% for a in articles %}
  {% assign dom = domains | where: "order", a.order | first %}
  <li><a href="{{ a.url | relative_url }}">{{ a.title }}</a>{% if dom %} <a class="tag" href="{{ dom.url | relative_url }}">{{ site.data.controls[dom.domain].domain }}</a>{% endif %}</li>
{% endfor %}
</ol>
