---
id: nimbus-troubleshooting-data-mapping
title: Troubleshooting Data Mapping Errors
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-01-19
owner: Support Engineering
---

Data mapping is where a workflow fills one app's fields from another app's data, using double-brace expressions such as `{{trigger.body.email}}` or `{{steps.lookup_account.output.Id}}`. When an expression can't produce a usable value, the step fails with WF-400 and the run stops there. WF-400 is the most common workflow error that isn't caused by a connector, and it is usually fixed in the workflow or in the source data rather than in Nimbus.

The expression syntax is deliberately small: references to `trigger`, `steps`, `secrets` and `env`, plus functions such as `now()`, `lower()` and `default()`. There is no other template syntax, which is itself a source of errors when Builders paste in syntax from other tools.

## Symptoms

- A transform or connector step fails at once, without retries, with WF-400 and a message naming a field, for example `Required field 'Email' resolved to empty`.
- Some runs of a workflow fail with WF-400 while others succeed, depending on the record that triggered them.
- Every run started failing right after someone edited and published the workflow.
- The run succeeds, but the target record contains the wrong value, a blank where a value was expected, or the literal text of an expression.

## Common causes

**A step key changed.** Every step has a key, shown under its name in the builder, and expressions refer to other steps by that key. If a Builder renames `lookup_lead` to `find_lead` in the step's settings, every `{{steps.lookup_lead.output...}}` expression further down the workflow now refers to a step that doesn't exist. The builder flags the reference, but publishing is still allowed, and from that version on every run fails with WF-400 at the first step that needs the value.

**A wrong path.** Field names are case-sensitive and must match the output of the step exactly: `{{trigger.body.Email}}` is empty when the sender posts `email`. Nested and list values need the full path, for example `{{steps.get_order.output.lines[0].sku}}` rather than `{{steps.get_order.output.sku}}`.

**An empty required field.** The expression is right but the source record has no value, typically a contact without an email address or an optional field in the source app that is required in the target app. These failures depend on the data, so they affect some runs and not others.

**A type mismatch.** The value exists but can't be converted to the type the target field needs: the text `"12 units"` for a number field, `"23/10/2026"` for a date field that expects ISO 8601, or `"yes"` for a boolean.

**Unsupported syntax.** Filters and helpers from other template languages, such as `{{ name | upper }}` or `{{#if ...}}`, aren't Nimbus expressions and either fail with WF-400 or are written to the target as literal text.

**A missing secret or variable.** `{{secrets.NAME}}` or `{{env.NAME}}` refers to a name that doesn't exist in this workspace or environment, which often shows up after a workflow is promoted to Production; see [Troubleshooting Workflow Promotion](nimbus-troubleshooting-promotion.md).

## Diagnosing the problem

1. Open the failed run and select the step marked WF-400. The **Log** tab names the field, the expression and what it resolved to:

```text
2026-01-12T14:03:51Z run=run_4HC81ZQW step=create_contact code=WF-400 field=Email expression="{{steps.lookup_lead.output.email}}" resolved=<empty>
```

2. Check that every step key in the expression still exists. In the builder, the referenced step should appear with exactly that key; if it doesn't, the key was renamed or the step deleted. **Version history** shows which publish changed it.
3. Open the **Output** tab of the referenced step in the same run and find the field. Compare its name, case, nesting and type with the expression.
4. Test the corrected expression in the builder. In a transform step, the **Test** button next to each field evaluates the expression against the data from the latest test run and shows the result and its type. **Test step** runs the whole step with that data. Test runs don't count against the monthly workflow runs.
5. For a pattern across many runs, read the step details through `GET /runs/{id}/steps` (see [Run Steps and Logs API](nimbus-api-run-steps.md)) and compare the inputs of failed and successful runs.

## Error reference

WF-400 is the only data-mapping code. Its message tells you which case you are in:

| WF-400 message | Meaning |
|---|---|
| `Required field '<field>' resolved to empty` | The expression produced no value for a required field. |
| `Unknown step key '<key>'` | The expression refers to a step key that doesn't exist in this version. |
| `Cannot convert '<value>' to <type>` | The value can't be converted to the target field's type. |
| `Unknown function '<name>'` | The expression calls a function Nimbus doesn't have. |
| `Secret '<NAME>' not found` | The secret isn't stored in this workspace or environment. |
| `Invalid expression at position <n>` | The expression isn't valid Nimbus syntax. |

If the step fails with CONN-404 instead, the expression worked but the record it pointed to doesn't exist in the third-party app; see [Troubleshooting Failed Workflow Runs](nimbus-troubleshooting-failed-runs.md).

## Fixes

- **Renamed step key:** update every expression that uses the old key, or rename the step back. Avoid renaming keys of steps in published workflows; change the display name instead, which expressions don't use.
- **Wrong path:** copy the path from the referenced step's **Output** tab rather than typing it.
- **Empty values:** give optional source fields a fallback with `default()`, which returns its second argument when the first is empty. For fields that must come from the source, add a condition step before the mapping that sends incomplete records to a notification or a review list instead of failing the run.
- **Type conversion:** convert explicitly with `number()` and `string()`, and send dates in ISO 8601.
- **Secrets:** create the missing secret under **Settings > Secrets** in the right environment; see [Storing Credentials in the Secrets Vault](nimbus-admin-secrets-vault.md).

A mapping that applies these fixes:

```yaml
Email: "{{lower(default(steps.lookup_lead.output.email, trigger.body.email))}}"
Quantity: "{{number(trigger.body.qty)}}"
Region: "{{default(trigger.body.region, 'EMEA')}}"
External_Ref__c: "{{string(trigger.body.order_id)}}"
Synced_At__c: "{{now()}}"
```

Publishing creates a new version, and runs started after that use it. Runs that already failed don't change; start them again once the fix is published.

## Escalating to support

Escalate when an expression evaluates correctly with **Test** in the builder but fails with WF-400 in a real run on the same data. Collect:

- the run id (`run_...`), the workflow id (`wf_...`) and the version number;
- the step key, the field and the exact expression;
- the step's **Input** from the failed run and the output of the referenced step, with personal data redacted;
- the result shown by **Test** for the same expression.
