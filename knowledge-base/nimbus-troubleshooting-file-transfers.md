---
id: nimbus-troubleshooting-file-transfers
title: Troubleshooting File Transfer Errors
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: reference
status: current
last_updated: 2025-11-17
owner: Support Engineering
---

File steps move content between the client's storage and their other applications: reading a CSV from an SFTP server, writing a report to Amazon S3 or Azure Blob Storage, or filing a contract in Box or Dropbox. Failures in these steps fall into a small number of patterns, and most of them can be identified from the step log alone.

This reference covers the SFTP, Amazon S3, Azure Blob Storage, Box and Dropbox connectors. Expired OAuth grants for Box and Dropbox are handled the same way as for any other connector; see [Troubleshooting Connector Authorization Errors](nimbus-troubleshooting-connection-errors.md).

## Symptoms

- A step fails with CONN-404 and a message such as `No such file: /outbound/reports/daily.csv` or `NoSuchKey`.
- A step fails before any data moves, with the message "File is larger than the 100 MB limit for files passed between steps".
- An SFTP connection that worked for months suddenly shows **Needs attention**, and its steps fail with "Host key does not match the stored fingerprint".
- Uploads to a bucket, container or folder fail with CONN-403 while downloads from the same place work.
- The target system receives a truncated file, a zero-byte file, or a file still named with the `.nimbus-part` suffix.

## Common causes

**Files over 100 MB.** A single file passed between steps can be up to 100 MB, whatever the connector. The check happens when the reading step finishes, so a large export fails at the first step rather than at the upload. Server-side actions such as **Copy object** in Amazon S3 and **Copy blob** in Azure Blob Storage don't pass the file between steps and aren't subject to the limit.

**Paths that don't resolve.** Paths are case-sensitive on SFTP, S3 and Azure Blob Storage. SFTP paths without a leading slash are relative to the login user's home directory, while S3 object keys never start with a slash. Box and Dropbox steps that take a folder ID keep working after a folder is renamed, but steps that take a path don't. A file can also disappear between the trigger and the read step when another process collects it first.

**SFTP host key changes.** On the first successful connection, Nimbus stores the server's host key fingerprint and refuses any other key afterwards. Rebuilding the server, rotating its host keys, or putting several servers with different keys behind one hostname all produce a mismatch. Nimbus treats this as a broken connection rather than a transient error, so the step isn't retried.

**Missing permissions.** The connected identity needs write as well as read access: `s3:PutObject` in the IAM policy, the `w` permission in an Azure SAS token, the Editor or Uploader role on a Box folder, or the `files.content.write` scope on the Dropbox app. On SFTP, the login user needs write permission on the target directory and, because of how uploads are finished, permission to rename files in it.

**Partial uploads.** The SFTP connector writes to `<name>.nimbus-part` and renames the file once the last byte is acknowledged. If the step is stopped mid-transfer (for example by the 10-minute step limit) or the server refuses the rename, the temporary file stays behind. For S3, an interrupted multipart upload leaves no visible object, only incomplete parts.

## Diagnosing the problem

1. Open the failed run under **Runs**, select the failing step and note its error code, the connector and the resolved path in the **Input** panel. A path built from an expression, such as `/inbound/{{trigger.body.filename}}`, shows its resolved value there.
2. Pull the same detail through the API if the client sends run ids rather than screenshots:

   ```http
   GET /runs/run_4Tz9Kp2Q/steps
   Authorization: Bearer <api-key>

   {"data": [{"step_key": "upload_report", "connector": "sftp", "status": "failed",
     "attempts": 1, "error": {"code": "CONN-404",
     "message": "No such file: /outbound/reports/2025-11-14/daily.csv"}}],
    "next_cursor": null}
   ```

3. For a host key mismatch, ask the client's server administrator to print the server's current fingerprint with the `ssh-keyscan` command under Fixes, and compare it with the fingerprint in the error message.
4. For CONN-403, confirm which identity the connection uses (the IAM user or role, the SAS token, the Box or Dropbox account shown on the connection) and check its rights on the exact target location, not on the parent.
5. For partial files, compare the step's duration with the 10-minute step limit and check the target for leftover `.nimbus-part` files.

## Error reference

| Code | What it means for a file step |
|---|---|
| CONN-401 | The connection is no longer authorised: an expired SAS token, a revoked Box or Dropbox grant, a rotated S3 access key, or an SFTP host key that no longer matches the stored fingerprint. |
| CONN-403 | The connected identity can't perform this operation on this path, bucket, container or folder. |
| CONN-404 | The file, folder, object key or container doesn't exist at the resolved path. |
| CONN-503 | The storage service, the SFTP server or the private connector agent in front of it is unavailable. |
| WF-200 | The transfer took longer than 10 minutes and the step was stopped, which can leave a partial file. |
| WF-400 | The expression that builds the path or file name resolved to empty. |

The 100 MB size check has no code of its own; the step fails with the size message shown under Symptoms.

## Fixes

| Problem | Fix |
|---|---|
| File over 100 MB | Split the export at source, compress it, or use a server-side copy action so the file never passes between steps. |
| Path not found | Correct case and leading slashes; use folder IDs for Box and Dropbox; add a condition step that checks the file exists before reading. |
| Upload denied | Add the missing permission to the identity the connection uses, then rerun. Nothing needs reconnecting. |
| Partial SFTP file | Allow rename in the target directory, delete the `.nimbus-part` file, and split transfers that approach 10 minutes. |
| Expired SAS token or key | Create a new token or key, open the connection and click **Reconnect**. |

### Host key changes

First, the client's server administrator prints the fingerprint of the server's current host key:

```bash
ssh-keyscan -t ed25519 sftp.client.example | ssh-keygen -lf -
```

When the client confirms the new key is genuine:

1. Open **Connections** and select the SFTP connection.
2. Click **Reconnect**. Nimbus connects, shows the server's new fingerprint and asks for confirmation.
3. Compare the fingerprint with the output of `ssh-keyscan` from the client's administrator, then click **Trust this key**.
4. Rerun the failed runs from run history.

Never accept a new fingerprint that the client can't explain: an unexpected key change is exactly what host key checking exists to catch. For SFTP connection fields, see [SFTP Connector](nimbus-connector-sftp.md).

## Escalating to support

Collect the following before raising a ticket:

- workspace id, run id and the step key of the failing step;
- the connector, the resolved path or object key, and the file size;
- for SFTP, the server software and the fingerprint the client expects;
- for S3 or Azure Blob Storage, the bucket or container name and the IAM policy or SAS permissions in use (never the secret itself);
- whether the server is reached through a private connector agent.
