---
layout: doc
title: Report Format
section: Assessment
order: 1
---

# Report Format

An assessment report is a JSON document conforming to [`eas-report.schema.json`]({{ '/schemas/eas-report.schema.json' | relative_url }}), from which human-readable views are rendered. A report is about one Workflow version, assessed against one catalog version, at one time.

## Structure

| Section | Contents |
|---|---|
| `subject` | Workflow, version, stack and profile version, commit, manifest path. |
| `scope` | Declared and derived risk tier, required level, target level, the trace sample used. |
| `inventory` | The assessed Tool inventory, with differences from the manifest. |
| `results[]` | One entry per control in the catalog: verdict, evidence by kind, notes. Not-applicable controls are included with the reason. |
| `findings[]` | One entry per `not_met`, `partial` or drift result, ranked, each with remediation. |
| `summary` | Counts by verdict and level, the highest level fully met, and the claim if one can be made. |

## A finding

```json
{
  "id": "F-003",
  "control": "EAS-04.01",
  "verdict": "not_met",
  "severity": "critical",
  "title": "Refund limit exists only in the system prompt",
  "evidence": [
    { "kind": "static", "ref": "agents/support/prompts/system.md:14",
      "detail": "\"Do not issue refunds over $500.\"" },
    { "kind": "static", "ref": "agents/support/tools/refunds.py:22-41",
      "detail": "issue_refund(order_id, amount) calls the payment API with the model-supplied amount; no limit check on any path." },
    { "kind": "declared", "ref": "eas.yaml#/workflows/0/policies/1",
      "detail": "Declared enforced_at: [prompt, gateway]; no gateway rule found.",
      "drift": true }
  ],
  "remediation": {
    "scope": "local",
    "summary": "Enforce the limit in the tool.before hook and add must-block tests.",
    "patch": "--- a/agents/support/hooks.py\n+++ b/agents/support/hooks.py\n@@ ...",
    "verifies_with": "policies/refunds_test.py::test_refund_over_limit_is_escalated"
  },
  "related": ["EAS-02.04", "EAS-03.08"]
}
```

## Severity

| Severity | When |
|---|---|
| `critical` | An L1 control not met on a path with an irreversible or egress effect, or any break in [EAS-07.02]({{ '/spec/controls/untrusted-content.html#eas-07-02' | relative_url }}), [EAS-06.01]({{ '/spec/controls/identity.html#eas-06-01' | relative_url }}) or [EAS-04.01]({{ '/spec/controls/enforcement.html#eas-04-01' | relative_url }}). |
| `high` | Any other control not met at or below the required level. |
| `medium` | `partial` at or below the required level, or drift between declared and implemented. |
| `low` | Controls above the required level, recorded as next steps. |

## Remediation contents

- **Local:** a unified diff, the control it addresses, and the test or trace assertion that will show it is met. A patch must not bundle unrelated changes.
- **Structural:** target components, affected modules, a sequence of steps that each leave the system working, the interim compensating control (for example, human approval on all effectful Tools until a ledger exists), and the evidence that will close the finding.
