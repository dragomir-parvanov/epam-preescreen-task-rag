---
id: nimbus-faq-workflow-builder
title: Workflow Builder FAQ
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-07-27
owner: Customer Success Enablement
---

The workflow builder is where Builders and Admins assemble a workflow: one trigger, then an ordered list of steps that pass data to each other through expressions. This FAQ covers the builder questions CSMs hear most often, from expression syntax and step keys to loops, conditions, test runs, version history and folders.

The builder lives under Workflows in the admin console. Viewers can open a workflow there but can't change it.

## General questions

**What kinds of step can a workflow contain?**

After the trigger, a workflow can contain any mix of six step types: a connector action (for example "Jira Cloud > Create issue"), a transform that maps fields with expressions, a condition, a loop over a list, a delay, and an approval step. Approval steps need the Business or Enterprise tier; the rest are available everywhere.

**What is a step key?**

Every step has a key, a short identifier such as `find_invoices` or `notify_finance`, shown under the step title. The builder suggests one from the step name when the step is added; it can be edited in the step's Settings tab until the workflow is first published. Expressions use the key, not the title, so renaming the title is always safe.

**Which expressions can I use?**

Nimbus uses double-brace expressions only; there is no other template syntax.

| Expression | Resolves to |
|---|---|
| `{{trigger.body.<field>}}` | A field of the trigger's payload |
| `{{steps.<step-key>.output.<field>}}` | A field of an earlier step's output |
| `{{secrets.<NAME>}}` | A value from the secrets vault |
| `{{env.<NAME>}}` | An environment variable of the current environment |
| `{{now()}}`, `{{lower(x)}}`, `{{default(x, y)}}` | Built-in functions: current time, lower-case text, fallback value |

Functions can be nested, for example `{{lower(default(trigger.body.email, "unknown@client.example"))}}`.

## Setup questions

**How do I add a condition?**

Add a Condition step and write the comparison in the builder's rule editor: a left-hand expression, an operator (equals, contains, greater than, is empty and so on) and a value. The step has two branches, If true and Otherwise. A branch can be left empty, which simply skips to the step after the condition.

**How do I test a workflow without using up the quota?**

Use Test run in the builder. Test runs don't count against the workspace's monthly run quota. The builder asks for a sample trigger payload, which it remembers per workflow:

```json
{
  "invoice_id": "INV-20931",
  "customer": { "name": "Harlow & Pike Ltd", "email": "ap@harlowpike.example" },
  "amount": 1840.5,
  "due_date": "2026-08-14"
}
```

Connector steps in a test run call the real apps through the real connections, so a test that creates a Jira issue creates a real one.

**How do folders work?**

Workflows can be grouped into folders from the Workflows list (New folder, then drag workflows in). Folders are one level deep, and they don't change permissions: every Builder can still see and edit every workflow.

### How do I loop over a list of records?

Add a Loop step after the step that returns the list, then put the steps to repeat inside it:

1. Click + after the list-producing step (say `find_invoices`, a NetSuite search) and choose Loop.
2. In List, enter the expression for the array, for example `{{steps.find_invoices.output.records}}`.
3. Give the loop a key such as `each_invoice`.
4. Drag or add the steps to repeat into the loop body. Inside it, the current item is `{{steps.each_invoice.output.item}}`, so a field reads `{{steps.each_invoice.output.item.amount}}`.
5. Click Test run and expand the loop in the run panel to see one entry per item.

After the loop, `{{steps.each_invoice.output.results}}` holds the list of outputs from the last step in the body.

## Limits and edge cases

**How long can a step or a run take?**

A single step that takes longer than 10 minutes fails with WF-200. A whole run still running after 60 minutes is stopped with status `timed_out` (WF-210). Delay steps count towards the run's 60 minutes.

**What happens when a connector step fails?**

It is retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. The retry count can be set from 0 to 5 on each step's Settings tab. The run fails only when the last retry fails.

**How large can data passed between steps be?**

A single file passed between steps can be up to 100 MB.

**How many versions are kept?**

Publishing a workflow creates a new version, and the last 50 versions are kept. Any of them can be restored from Version history; restoring creates a new version rather than rewriting history, so the version being replaced stays available too.

## Troubleshooting questions

**A run failed with WF-400.**

A data-mapping expression failed, usually because a required field resolved to empty. Open the failed step in Runs, compare the expression with the actual input shown in the step log, and either correct the field path or supply a fallback with `{{default(x, y)}}`.

**The test run worked but the live run fails.**

The sample payload probably differs from what the trigger really sends. Copy the trigger output from the failed run's first step and paste it as the new sample, then run the test again.

**An expression shows "Unknown step key".**

The expression refers to a step that was deleted or to a step that comes later in the workflow. Expressions can only read steps that run before them.

**The trigger shows WF-100.**

The trigger configuration is invalid, most often a malformed cron expression or a required trigger field left empty.

## Where to find more

- [Workflow Version History](nimbus-tier-version-history.md) and [Restoring a Previous Workflow Version](nimbus-admin-restoring-workflow-versions.md).
- [Troubleshooting Data Mapping Errors](nimbus-troubleshooting-data-mapping.md) for WF-400 in depth.
- [Troubleshooting Step and Run Timeouts](nimbus-troubleshooting-timeouts.md) for WF-200 and WF-210.
- [Folders API](nimbus-api-folders.md) and [Workflows API](nimbus-api-workflows.md) for doing the same through the API.
