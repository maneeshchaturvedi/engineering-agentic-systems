---
layout: doc
title: Progressive Configurations
section: Implementation
order: 1
---

# Progressive Configurations

Six configurations, from a single model call to a shared platform. Each keeps every component in the same place, so reading them in order shows one system growing rather than six different drawings. Each stage lists the controls that newly matter, and the condition for climbing to the next — following [Principle 1]({{ '/essays/01-use-the-simplest-pattern-that-works.html' | relative_url }}): climb only when a specific requirement cannot be met at the current stage.

In every diagram, the evaluation suite gates changes through the release control, and every component emits traces to the telemetry pipeline; those edges are omitted for clarity.

<nav class="stage-nav">{% for s in site.data.stages.stages %}<a href="#{{ s.slug }}">{{ s.n }}. {{ s.title }}</a>{% endfor %}</nav>

{% for s in site.data.stages.stages %}
<section class="stage" id="{{ s.slug }}">
<h2>Stage {{ s.n }} — {{ s.title }}</h2>
<p class="stage-meta"><span>rung: {{ s.rung }}</span><span>tier {{ s.tier }}</span><span>required level {{ s.level }}</span></p>
<p>{{ s.when }}</p>
<figure class="diagram"><div class="diagram-scroll">{% capture f %}stages/stage-{{ s.n }}.svg{% endcapture %}{% include {{ f }} %}</div></figure>
<p><strong>What this stage adds</strong></p>
<ul>{% for a in s.adds %}<li>{{ a | markdownify | remove: '<p>' | remove: '</p>' | strip }}</li>{% endfor %}</ul>
<p class="refs"><strong>Controls that newly matter:</strong> {% for id in s.controls %}{% assign k = id | slice: 0, 6 | downcase %}<a href="{{ '/spec/controls/' | append: site.data.controls[k].slug | append: '.html' | relative_url }}#{{ id | downcase | replace: '.', '-' }}">{{ id }}</a>{% unless forloop.last %}, {% endunless %}{% endfor %}</p>
<p class="refs"><strong>Technology:</strong> {% assign intro = site.data.tech.groups | where: "introduce_at", s.n %}{% if intro.size > 0 %}concerns introduced here — {% for g in intro %}<a href="choices.html#{{ g.id }}">{{ g.title }}</a>{% unless forloop.last %}, {% endunless %}{% endfor %}; {% endif %}see <a href="choices.html">technology choices</a> for what each stage should invest in.</p>
<p><strong>When to climb:</strong> {{ s.next }}</p>
</section>
{% endfor %}
