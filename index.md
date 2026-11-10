---
layout: default
title: Engineering Agentic Systems
---

# Engineering Agentic Systems

LLM-based agents put a nondeterministic, persuadable component at the centre of our systems: the part that decides what happens next. This site argues for one design stance and turns it into something you can build and assess against: **the model proposes; a deterministic system disposes.**

<div class="cards">
  <a class="card" href="{{ '/essays/' | relative_url }}">
    <span class="card-kicker">Why</span>
    <strong>Essays</strong>
    <span>An introduction and twelve principles for building agents with the discipline of distributed systems engineering.</span>
  </a>
  <a class="card" href="{{ '/spec/' | relative_url }}">
    <span class="card-kicker">What</span>
    <strong>Specification</strong>
    <span>The principles as testable controls, with levels, evidence rules, an agent manifest, telemetry conventions and a hook contract.</span>
  </a>
  <a class="card" href="{{ '/profiles/' | relative_url }}">
    <span class="card-kicker">Where</span>
    <strong>Stack profiles</strong>
    <span>How the specification maps onto LangGraph, the OpenAI Agents SDK and CrewAI, and where each falls short.</span>
  </a>
  <a class="card" href="{{ '/blueprint/' | relative_url }}">
    <span class="card-kicker">How</span>
    <strong>Reference architecture</strong>
    <span>The components of a mature agentic platform, and the controls each one satisfies.</span>
  </a>
  <a class="card" href="{{ '/assessment/' | relative_url }}">
    <span class="card-kicker">Check</span>
    <strong>Assessment</strong>
    <span>How to assess a Workflow and report findings with concrete remediation: patches for local gaps, plans for structural ones.</span>
  </a>
</div>

## Start here

- **Building an agent?** Read [The Unreliable Component]({{ '/essays/00-the-unreliable-component.html' | relative_url }}), then write a [manifest]({{ '/spec/manifest.html' | relative_url }}) for your Workflow. Declaring your Tools' effect and trust classes will surface most L1 gaps on its own.
- **Running a platform?** Start with the [reference architecture]({{ '/blueprint/' | relative_url }}) and the [conformance model]({{ '/spec/conformance.html' | relative_url }}), especially inheritance.
- **Building agent tooling?** The [control catalog]({{ '/spec/controls/catalog.json' | relative_url }}) and the [manifest]({{ '/schemas/eas-manifest.schema.json' | relative_url }}) and [report]({{ '/schemas/eas-report.schema.json' | relative_url }}) schemas are machine-readable.
