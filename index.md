---
layout: default
title: Engineering Agentic Systems
---

# Engineering Agentic Systems

LLM-based agents put a nondeterministic, persuadable component at the centre of our systems — the part that decides what happens next. This series argues for one design stance: **the model proposes; a deterministic system disposes.** An introduction explains what agents do to distributed systems, and twelve principles show how to build around them.

{% assign articles = site.pages | where: "layout", "post" | sort: "order" %}
<ol class="toc" start="0">
{% for a in articles %}
  <li><a href="{{ a.url | relative_url }}">{{ a.title }}</a></li>
{% endfor %}
</ol>
