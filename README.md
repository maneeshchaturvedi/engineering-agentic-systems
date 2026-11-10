# Engineering Agentic Systems

An essay series on building LLM agents with the discipline of distributed systems engineering, and the **EAS specification** derived from it, by Maneesh Chaturvedi.

Read it online: https://maneeshchaturvedi.github.io/engineering-agentic-systems/

## Repository layout

| Path | Contents |
|---|---|
| `essays/` | The introduction and twelve principles (the rationale). |
| `spec/` | The specification: conformance model, reference model, manifest, telemetry conventions, hook contract, and one page per control domain. |
| `_data/controls/eas-NN.yml` | **Source of truth for the controls.** Control pages, the questionnaire, the blueprint's control mappings and `spec/controls/catalog.json` are all generated from these files. |
| `_data/components.yml` | Reference-architecture components. |
| `profiles/` | Stack profiles (LangGraph, OpenAI Agents SDK, CrewAI). |
| `blueprint/` | Reference architecture and diagram (`_includes/blueprint-diagram.svg`). |
| `assessment/` | Assessment method, report format, questionnaire. |
| `schemas/` | JSON Schemas for the agent manifest and assessment report, plus an example manifest. |

The site is built by GitHub Pages (Jekyll). Essays moved from the repository root to `essays/`; the old URLs redirect via `jekyll-redirect-from`.

## Building locally

```sh
gem install jekyll jekyll-seo-tag jekyll-redirect-from kramdown-parser-gfm webrick
jekyll serve
```
