---
id: nimbus-v2-troubleshooting-workflow-runs
title: Troubleshooting Workflow Runs (v2)
product: OmniCorp Nimbus
applies_to: [v2]
doc_type: reference
status: deprecated
last_updated: 2025-04-28
owner: Support Engineering
---

This reference helps CSMs work out why a workflow run failed on the legacy Nimbus platform and how the client gets the work done afterwards. Failed runs are reported with a plain-language message rather than an error code, run history is kept for 30 days, and there is no retry: a failed run is started again by hand.

For the platform's limits and support timeline, see [Nimbus v2 Legacy Reference](nimbus-v2-legacy.md). The API calls used below are described in full in [Runs API (v2)](nimbus-v2-api-runs.md).

## Symptoms

- A workflow's **Runs** tab shows one or more runs with the red **Failed** badge.
- The run detail shows the failing step with a sentence such as "Connection authorization expired" or "Permission denied by Salesforce", and no code.
- Data the workflow should have created or updated is missing in the target application.
- The client asks about a failure from several weeks ago, and the run can no longer be found.
- An API call to list or read runs returns `{"error": "<message>"}` with an HTTP status and no further detail.

## Common causes

Most failures come from the connected application rather than from Nimbus itself:

- **Expired or revoked authorisation.** The person who connected the account left, changed their password, or revoked the app's access in the application.
- **Missing permission in the application.** The connected account can read records but not update them, or can't see a particular object or folder.
- **Missing records.** The record, file or channel a step refers to was deleted or renamed after the workflow was built.
- **Bad input data.** A field mapping expects a value the trigger didn't supply, for example an email address that is empty on some records.
- **The application was unavailable or throttling.** The step's message names the application and says it was unavailable or limited the connector.

Run history is kept for 30 days. A run older than that is gone from the console and the API, so a client asking about an older failure can only be helped from their own records or the target application's logs.

## Diagnosing the problem

1. Open **Workflows**, select the workflow and open its **Runs** tab. Filter to **Failed** and open the run the client is asking about.
2. Select the step marked in red. The **Error** panel shows the message, and the **Input** and **Output** panels show what the step received and returned.
3. Note whether earlier steps in the same run succeeded. Anything they created in other applications already exists and must not be created twice when the run is started again.
4. To review failures across a period, list them through the API. Pagination is page-based, and the response carries `total`:

```http
GET /runs?workflow_id=wf_3Gd8Lp1X&status=failed&page=1&per_page=50
Authorization: Bearer <api-key>

{"data": [{"id": "run_6Pm2Vc9H", "workflow_id": "wf_3Gd8Lp1X",
  "status": "failed", "started_at": "2025-04-22T06:00:04Z",
  "failed_step": "update_account",
  "error": "Permission denied by Salesforce: INSUFFICIENT_ACCESS_OR_READONLY"}],
 "page": 1, "per_page": 50, "total": 3}
```

5. Read one run in full with `GET /runs/{id}` to get every step's input, output and message, and save the response if the client may need it after the history expires.

## Error reference

Errors are plain messages. These are the ones CSMs see most often:

| Message (start of text) | Meaning | What to do |
|---|---|---|
| "Connection authorization expired" | The connected account's sign-in is no longer valid. | Edit the connection under **Admin > Connections** and sign in again. |
| "Permission denied by <app>" | The connected account lacks rights in the application. | Grant the right in the application, then start the run again. |
| "Record not found in <app>" | The record, file or channel doesn't exist any more. | Correct the step or the source data. |
| "Expression could not be evaluated" | A field mapping resolved to nothing or to the wrong type. | Fix the mapping or add a condition step for empty values. |
| "<app> is unavailable" | The application didn't respond or returned a server error. | Wait, then start the run again. |
| "<app> limited the connector" | The application throttled the connector. | Spread the workflow's schedule out, then start the run again. |
| "Step timed out" | The step didn't finish in time. | Reduce the amount of data the step handles. |

## Fixes

Fix the cause first, using the table above. Connection credentials are stored per connection, so an expired authorisation or a changed password is fixed by editing that connection under **Admin > Connections**; every workflow using it picks up the change.

Then start the work again. There is no retry button and no retry endpoint, so the run is started by hand:

- **Manual or scheduled workflows:** open the workflow and click **Run now**.
- **Event-triggered workflows:** copy the trigger input from the failed run's **Input** panel and start a run with it through the API, `POST /workflows/{id}/runs` with the input as the request body.
- **Partly completed runs:** if earlier steps already created records, either delete those records first or temporarily disable the steps that created them, so the new run doesn't duplicate them. Requests can't carry an idempotency key, so the API won't catch a duplicate for you.

For failures in a specific connector, check the connector's own reference, for example [Salesforce Connector (v2)](nimbus-v2-connector-salesforce.md) or [Slack Connector (v2)](nimbus-v2-connector-slack.md).

## Escalating to support

Escalate within the 30 days that run history is kept, since support can't investigate a run that has expired. Collect:

- the workspace id, workflow id and run id;
- the full error message, copied rather than paraphrased;
- the time of the failure in UTC and the connector involved;
- the saved `GET /runs/{id}` response, if the client has one.

The legacy platform receives security fixes only, so support can explain a failure but won't change the platform's behaviour. Clients who need error codes, automatic retries or longer run history get them by upgrading, which the CSM books with OmniCorp support; the upgrade itself takes under an hour.
