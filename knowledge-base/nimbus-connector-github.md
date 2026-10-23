---
id: nimbus-connector-github
title: GitHub Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-05-25
owner: Integrations Team
---

The GitHub connector connects Nimbus to repositories on GitHub.com, including organisations on GitHub Enterprise Cloud. Workflows can start on pull request, issue and release events and can create issues, post comments, add labels and create releases. Typical uses are posting merged pull requests to a release-notes channel, opening an issue from a failed workflow run, or labelling issues raised by customers.

Unlike OAuth-based connectors, the GitHub connector is a GitHub App. The client installs the **OmniCorp Nimbus** app on their organisation and chooses which repositories it may access; the connection then acts as the app, not as any person, so it keeps working when the person who installed it leaves.

## Prerequisites

- **An organisation owner**, or a member allowed to install apps, to install the app. When a member without that right starts the installation, GitHub sends a request to the organisation owners instead, and the Nimbus connection waits in "Pending approval" until an owner approves it.
- **A decision on repository access**: all repositories, or only selected ones. Selecting only the repositories the workflows need is the safer choice.
- **A Builder or Admin role** in Nimbus. The connector is available on every Plan Tier.

The app requests the following permissions. Owners see this list on the installation screen and can't install with a subset.

| Permission | Level | Why Nimbus needs it |
|---|---|---|
| Metadata | Read-only | Mandatory for every GitHub App; lists repositories |
| Issues | Read and write | Issue events, create issue, comment, add label |
| Pull requests | Read and write | Pull request events, comments on pull requests |
| Contents | Read and write | Creating releases and their tags |

The app subscribes to the **Issues**, **Issue comment**, **Pull request** and **Release** webhook events. When a later Nimbus release adds a permission, GitHub asks the owners to accept the change; until they do, the app keeps its old permissions.

## Creating the connection

1. In Nimbus, open **Connections**, click **New connection** and choose **GitHub**.
2. Click **Install GitHub App**. GitHub opens the app's installation page.
3. Pick the organisation to install on. Only organisations where you can install apps are listed.
4. Choose **All repositories** or **Only select repositories**, and pick the repositories.
5. Review the permissions and click **Install**. GitHub returns you to Nimbus with the installation ID filled in.
6. Name the connection, for example `github-acme-platform`, click **Test connection** to list the repositories it can reach, and click **Save**.

One connection corresponds to one installation, that is, one organisation. To work with a second organisation, install the app there too and create a second connection. Repositories added to the installation later in GitHub (organisation **Settings > GitHub Apps > OmniCorp Nimbus > Configure**) become available to the connection immediately, without reconnecting.

## Triggers and actions

| Name | Type | Filter options |
|---|---|---|
| Pull request event | Push trigger | Repository; actions `opened`, `closed`, `reopened`, `ready_for_review`, `review_requested`; **Merged only** |
| Issue event | Push trigger | Repository; actions `opened`, `edited`, `closed`, `labeled`; label name |
| Release published | Push trigger | Repository; include or exclude pre-releases |
| Create issue | Action | Title, body, labels, assignees, milestone |
| Comment | Action | Posts a comment on an issue or pull request by number |
| Add label | Action | Adds one or more labels; missing labels are created |
| Create release | Action | Tag, target branch or commit, name, notes, draft, pre-release |

A closed pull request has `closed` as its action whether it was merged or not; turn on **Merged only** to start runs just for merges.

## Field mapping

Trigger output is GitHub's own event payload, so field names follow GitHub's documentation. A workflow that opens a tracking issue in an ops repository whenever a pull request labelled `needs-docs` is merged could map its Create issue step like this:

```json
{
  "repository": "acme/docs-tracker",
  "title": "Document: {{trigger.body.pull_request.title}}",
  "body": "Merged in {{trigger.body.repository.full_name}}#{{trigger.body.pull_request.number}} by @{{trigger.body.pull_request.merged_by.login}} on {{trigger.body.pull_request.merged_at}}.\n\n{{default(trigger.body.pull_request.body, 'No description.')}}",
  "labels": ["docs", "from-nimbus"],
  "assignees": ["{{lower(trigger.body.pull_request.user.login)}}"]
}
```

Issues and pull requests share one number sequence in a repository, and the Comment action takes that number, so `{{trigger.body.pull_request.number}}` and `{{trigger.body.issue.number}}` both work. The Create issue output gives `{{steps.<step-key>.output.html_url}}` for linking back from a Slack or email step.

## Limits and behaviour

- **Delivery.** GitHub pushes events to Nimbus as they happen; a run normally starts within seconds. Each event starts one run, so a pull request that is labelled three times starts three runs if the trigger listens for `labeled`.
- **Authentication.** Nimbus exchanges the installation for a short-lived installation token for each run; there is no token for the client to rotate or that can expire.
- **Text sizes.** Issue bodies and comments can be up to 65,536 characters; longer mapped text fails the step with WF-400. Release assets attached by Create release can be up to 100 MB each.
- **Releases.** Create release fails if the tag already exists with a release; to make the step safe to retry, add a condition that checks for an existing release first.
- **Retries.** Failed steps are retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. When GitHub throttles the installation, Nimbus waits for the reset time GitHub returns before retrying.

## Troubleshooting

| Code | Cause | Fix |
|---|---|---|
| CONN-401 | The app was uninstalled from the organisation or suspended by an owner | Reinstall or unsuspend it under the organisation's **GitHub Apps** settings, then click **Reconnect**. |
| CONN-403 | The repository isn't selected in the installation, or owners haven't accepted a new permission | Add the repository under **Configure**, or accept the pending permission request. |
| CONN-404 | The repository was renamed or transferred, or the issue number doesn't exist | Update the repository in the step; transferred repositories must be in an organisation with the app installed. |
| CONN-429 | GitHub throttled the installation | Nothing to do; Nimbus waits and retries. |
| WF-400 | A required field such as the issue title resolved to empty, or text is too long | Fix the expression or add `default()`. |

If a trigger never fires, the client can't see the deliveries in their own GitHub settings, because the app's webhook belongs to OmniCorp. Check **Runs** in Nimbus, the trigger's repository and action filters, and that the repository is still selected in the installation. For GitLab repositories, see [GitLab Connector](nimbus-connector-gitlab.md).
