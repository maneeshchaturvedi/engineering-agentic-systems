---
layout: doc
title: Controls
section: Specification
order: 3
---

# Controls

Each domain corresponds to one principle in the essay series. The essay is the rationale; the controls are the testable requirements derived from it. Every control has a level, the evidence that can establish it, and the shape of its remediation: **local** (a configuration or code change within the existing design) or **structural** (a design change, for which an assessment produces a plan rather than a patch).

{% assign domains = site.pages | where: "layout", "controls" | sort: "order" %}
{% assign total = 0 %}{% assign l1 = 0 %}{% assign l2 = 0 %}{% assign l3 = 0 %}
<table class="index">
  <thead><tr><th>Domain</th><th>Controls</th><th>L1</th><th>L2</th><th>L3</th></tr></thead>
  <tbody>
  {% for p in domains %}{% assign d = site.data.controls[p.domain] %}{% if d %}
    {% assign n1 = d.controls | where: "level", "L1" | size %}{% assign n2 = d.controls | where: "level", "L2" | size %}{% assign n3 = d.controls | where: "level", "L3" | size %}
    {% assign total = total | plus: d.controls.size %}{% assign l1 = l1 | plus: n1 %}{% assign l2 = l2 | plus: n2 %}{% assign l3 = l3 | plus: n3 %}
    <tr><td><a href="{{ p.url | relative_url }}">{{ d.domain }} {{ d.title }}</a></td><td>{{ d.controls.size }}</td><td>{{ n1 }}</td><td>{{ n2 }}</td><td>{{ n3 }}</td></tr>
  {% endif %}{% endfor %}
  </tbody>
  <tfoot><tr><th>Total</th><th>{{ total }}</th><th>{{ l1 }}</th><th>{{ l2 }}</th><th>{{ l3 }}</th></tr></tfoot>
</table>

## Machine-readable catalog

The full catalog is published as JSON at [`catalog.json`](catalog.json), generated from the same source files as these pages (`_data/controls/*.yml` in the repository). Assessment tooling should consume the catalog, not scrape the pages.

## Reading a control

| Field | Meaning |
|---|---|
| **Level** | The lowest [conformance level](../conformance.html#levels) at which the control is required. |
| **Applies to** | The condition under which the control is in scope. Out-of-scope controls are assessed as `not_applicable`. |
| **Requirement** | Normative text using [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) keywords. |
| **Evidence** | What establishes conformance: *declared* in the [manifest](../manifest.html), *static* in code or configuration, *runtime* in [telemetry](../telemetry.html), or *attested* by the owning team. |
| **Remediation** | Local or structural, with guidance. |
| **Hooks / Components** | The [hook](../hooks.html) through which the control is enforced and the [blueprint]({{ '/blueprint/' | relative_url }}) components that implement it. |
