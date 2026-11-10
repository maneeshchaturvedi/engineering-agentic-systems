---
layout: doc
title: Questionnaire
section: Assessment
order: 2
---

# Questionnaire

Some controls concern process — release gates, approval practice, degradation plans, deletion — and cannot be established from code or traces alone. These are the questions an assessor puts to the owning team. Every answer should name a respondent and link to an artefact: a runbook, CI configuration, dashboard or policy document. An answer without an artefact is recorded, but it is weak evidence.

The questions are generated from the *attested* evidence of each control in the [catalog]({{ '/spec/controls/' | relative_url }}), so they stay in step with it.

{% assign domains = site.pages | where: "layout", "controls" | sort: "order" %}
{% for p in domains %}{% assign d = site.data.controls[p.domain] %}{% assign has = false %}{% for c in d.controls %}{% if c.evidence.attested %}{% assign has = true %}{% endif %}{% endfor %}{% if has %}
<h2 id="{{ d.slug }}">{{ d.domain }} {{ d.title }}</h2>
<table class="q">
  <thead><tr><th>Control</th><th>Level</th><th>Question</th></tr></thead>
  <tbody>
  {% for c in d.controls %}{% if c.evidence.attested %}
    <tr><td><a href="{{ p.url | relative_url }}#{{ c.id | downcase | replace: '.', '-' }}">{{ c.id }}</a></td><td><span class="lvl {{ c.level | downcase }}">{{ c.level }}</span></td><td>{{ c.evidence.attested | markdownify | remove: '<p>' | remove: '</p>' | strip }}</td></tr>
  {% endif %}{% endfor %}
  </tbody>
</table>
{% endif %}{% endfor %}
