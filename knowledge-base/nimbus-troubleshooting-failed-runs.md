---
id: nimbus-troubleshooting-failed-runs
title: Troubleshooting Failed Workflow Runs
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2026-08-31
owner: Support Engineering
---

A workflow run ends with the status `failed` when one of its steps fails and has no retries left. The run stops at that step: later steps don't run, and anything the earlier steps already did in third-party apps stays done. This reference covers how to read a failed run in run history, how step retries behave, what each WF- error code means, and how to decide whether the fix belongs in the data or in the workflow's configuration.

Connector authorisation problems, timeouts and data-mapping errors each have their own Article; this one is the starting point when a CSM only knows that "the workflow failed".

## Symptoms

A client usually notices a failed run in one of these ways:

- The run shows a red **Failed** badge under **Runs**, and the workflow's row in **Workflows** shows the time of its last failure.
- The workspace's failure alert email arrives, if alerts are configured under **Settings > Notifications** (see [Configuring Failure Notifications](nimbus-admin-failure-notifications.md)).
- Their own system receives a `workflow.run.failed` webhook event.
- Records that the workflow should have created or updated are missing in the target app.

Not every red or grey badge is a failure. A run stopped at the 60-minute limit has its own status, `timed_out`; a run an Admin or Builder stopped by hand is `cancelled`; and a run held back by the concurrent-run limit sits as `queued` with the notice WF-310, which is not an error.

## Common causes

Failed runs fall into a few groups, and the error code on the failed step tells you which one you are in:

| Group | Codes | What it usually means |
|---|---|---|
| Connector errors | CONN-401, CONN-403, CONN-404, CONN-503 | The third-party app refused or couldn't serve the request. |
| Data errors | WF-400, CONN-404 | The input for this run was empty, malformed or referred to a record that doesn't exist. |
| Configuration errors | WF-100, CONN-401, CONN-403 | The trigger, a connection or a permission is wrong for every run. |
| Platform limits | WF-200, WF-300 | A step ran too long, or the monthly runs were used up. |
| Approvals | WF-410 | Nobody approved or rejected an approval step in time. |
| Internal | WF-500 | Something failed inside Nimbus. |

Before a connector step is marked failed, Nimbus retries it. A failed connector step is retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes, and the run fails only when the last retry fails too. A Builder can set the retry count from 0 to 5 on each step under the step's **Settings > Retries**. Because of those waits, a connector step that keeps failing takes more than 12 minutes to fail the run, so a client may see a run "hang" before it goes red. Transform, condition and loop steps aren't connector steps and fail on the first error.

## Diagnosing the problem

1. Open **Runs**, filter **Status** to *Failed* and **Workflow** to the workflow in question. Note whether one run failed or every run since a certain time.
2. Open the failed run. The step timeline marks the failed step in red; select it to see its **Input**, **Output** and **Log** tabs. Each attempt is listed separately, so you can see whether the retries hit the same error.
3. Read the error code and message from the last attempt's log line:

```text
2026-08-24T06:02:14Z run=run_8QK2M7XD step=create_invoice attempt=4/4 status=failed code=CONN-404 message="NetSuite record customer/88213 not found"
```

4. If the client prefers the API, list the failed runs and then read the steps of one of them:

```http
GET /runs?workflow_id=wf_7730&status=failed&limit=25 HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>

GET /runs/run_8QK2M7XD/steps HTTP/1.1
Host: api.nimbus.omnicorp.example
Authorization: Bearer <api-key>
```

Each step in the response carries its `key`, `status`, `attempts` and an `error` object with `code` and `message`. See [Run Steps and Logs API](nimbus-api-run-steps.md).

5. Open the last successful run of the same workflow and compare the **Input** of the step that failed. A difference in the data points to a data problem; identical input with a different outcome points to configuration or the third-party app.

## Error reference

| Code | Meaning | Data or configuration? |
|---|---|---|
| WF-100 | The trigger configuration is invalid: a bad cron expression or a missing trigger field. | Configuration |
| WF-200 | A step ran longer than 10 minutes and was stopped. | Usually the volume of data |
| WF-210 | The run was still running after 60 minutes and was stopped; status `timed_out`. | Workflow design |
| WF-300 | The workspace has used its monthly workflow runs; the run was rejected. | Plan Tier |
| WF-310 | The concurrent-run limit was reached; the run waits as `queued`. A notice, not a failure. | Neither |
| WF-400 | A data-mapping expression failed, for example a required field resolved to empty. | Usually data |
| WF-410 | An approval expired after 7 days without a decision. | Process |
| WF-500 | An internal Nimbus error. The run can be retried. | Neither |
| CONN-401 to CONN-503 | Connector errors; see [Troubleshooting Connector Authorization Errors](nimbus-troubleshooting-connection-errors.md). | Mostly configuration |

## Fixes

### Data or configuration?

Use the pattern of failures. If some runs fail with WF-400 or CONN-404 while other runs of the same workflow version succeed, the input data is the problem: fix the record in the source app (fill in the missing email, restore the deleted customer) and retry the run. If every run has failed from the same step since a particular moment, something changed in the configuration: check **Version history** for a recent publish (see [Restoring a Previous Workflow Version](nimbus-admin-restoring-workflow-versions.md)), check whether the connection shows "Needs attention", and check the trigger settings. For WF-400 in detail, see [Troubleshooting Data Mapping Errors](nimbus-troubleshooting-data-mapping.md).

### Retrying a run

A Builder or Admin retries a failed run with **Retry** on the run's page, or with `POST /runs/{id}/retry` (available since release 3.8.0). A retry starts a new run with the same trigger input on the workflow's currently published version, not the version the original run used, so a fix you published is picked up. The new run's `retry_of` field holds the original run id. Keep three things in mind:

1. Every step runs again from the start, including steps that succeeded the first time. If those steps create records, check the target app for duplicates first, or make the step look up before it creates.
2. A retry is a new run, so it counts against the monthly workflow runs.
3. Retrying WF-300 runs only works once the quota has reset or the Plan Tier has been upgraded; see [Troubleshooting Run Quota Errors](nimbus-troubleshooting-run-quota.md).

WF-500 runs can be retried straight away with no change.

## Escalating to support

Open a ticket with OmniCorp support when a run fails with WF-500 again after a retry, or when the error doesn't match anything above. Collect:

- the workspace id (`ws_...`) and its data region;
- the run ids (`run_...`) of one or more failed runs, and the workflow id (`wf_...`) with its version number;
- the failed step's key, the error code and the full message from its log;
- the time of the first failure, in UTC, and whether a retry reproduced it;
- the step log, downloaded with **Download log** on the run page.

Run history is kept for 90 days on every Plan Tier, so raise the ticket while the failed runs are still there.
