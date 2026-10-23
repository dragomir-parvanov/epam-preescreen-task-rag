---
id: nimbus-connector-sftp
title: SFTP Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-06-08
owner: Integrations Team
---

The SFTP connector moves files between Nimbus workflows and an SFTP server. It is the usual choice for batch exchanges that still run on files: payroll exports, bank statements, supplier catalogue drops and nightly data extracts. A workflow can start when a new file lands in a directory, then download, transform and pass the file on, and finally move it to an archive folder.

The connector authenticates with a username plus an SSH key or a password, and pins the server's host key so that Nimbus only ever talks to the server the client confirmed. Servers that can't be reached from the internet are supported on Enterprise through the private connector agent.

## Prerequisites

- **An SFTP account for Nimbus.** Ask the client for a dedicated user whose home directory, or chroot, contains only the directories the workflows need. Read access is enough for a trigger and downloads; uploads, moves and deletes need write access.
- **A way in.** Either the server is reachable from the internet on its SFTP port (usually 22), or the client is on Enterprise and runs the private connector agent inside their network.
- **The server's host key fingerprint**, obtained from the server administrator through a channel other than the connection itself, so it can be compared during setup.
- **A Builder or Admin** in Nimbus to create the connection, and room for another active connector on the workspace's tier (see [Plan Tiers and Entitlements](nimbus-plan-tiers.md)).

SSH key authentication is recommended over a password. Keys can't be guessed, they can be scoped to one server, and the client can revoke one without changing a password other systems may share. Supported key types are Ed25519, ECDSA and RSA of 2048 bits or more.

## Creating the connection

1. In the Nimbus admin console, open **Connections > New connection** and choose **SFTP**.
2. Enter the **Host** (a hostname such as `sftp.client.example`), the **Port** and the **Username**.
3. Under **Connect through**, keep **Internet**, or pick a registered private connector agent from the list. Agents are registered by an Admin under **Settings > Agents**.
4. Under **Authentication**, choose **SSH key** or **Password**. For **SSH key**, either click **Generate key pair**, which creates an Ed25519 key in Nimbus and shows the public key to send to the client, or paste an existing private key in OpenSSH format with its passphrase, if any.
5. Click **Test**. Nimbus connects and shows the server's host key fingerprint.
6. Compare the fingerprint with the one the server administrator provided. Only if they match, click **Trust this host key and save**.

The server administrator can read the fingerprint on the server itself:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
# 256 SHA256:Xq3hP8tT0mZ1v7bWc2kQ9rJ4nYfLs6dE5gHa1uKoR0w root@sftp01 (ED25519)
```

After saving, the credentials are encrypted and can't be viewed again, and the pinned fingerprint is shown on the connection page.

## Triggers and actions

| Name | Type | Behaviour |
|---|---|---|
| New file in directory | Polling trigger | Lists a directory and starts one run per new file matching the **File pattern**. Output: `path`, `name`, `size`, `modified_at`. |
| Upload file | Action | Writes a file from an earlier step to a remote path. **If file exists**: overwrite, fail, or add a timestamp suffix. |
| Download file | Action | Reads a remote file and outputs it for later steps. |
| Move file | Action | Moves or renames a file on the server, typically into `archive/` after processing. |
| Delete file | Action | Deletes a remote file. |

The trigger's **File pattern** is a glob such as `*.csv` or `payroll_*.xml`, and subdirectories are not searched. A **Minimum file age** (default 1 minute) stops the trigger from picking up a file the sender is still writing; raise it if the client's sender writes large files slowly, or have the sender upload under a temporary name and rename on completion.

## Field mapping

Paths and file names are built with expressions. This pair of steps downloads the file that started the run and, after the processing steps, moves it into a dated archive folder:

```yaml
- key: fetch
  action: sftp.download_file
  path: "{{trigger.body.path}}"
- key: archive
  action: sftp.move_file
  from: "{{trigger.body.path}}"
  to: "/outbound/archive/{{now()}}_{{trigger.body.name}}"
```

Remote paths are case-sensitive on most servers and are relative to the account's home directory unless they start with `/`. Upload actions take the file from an earlier step, for example `{{steps.build_report.output.file}}`, and the remote file name can be any expression.

## Limits and behaviour

- **Polling.** The trigger polls every 5 minutes. A file counts as new when its name hasn't been seen before or its modified time has changed. The first poll records what is already in the directory and starts no runs for it.
- **File size.** Each file can be up to 100 MB, the limit for any file passed between steps. Larger files are skipped by the trigger, which lists them as skipped on the workflow's trigger panel, and a download step given one fails.
- **Volume.** Each poll starts at most 200 runs; further new files are picked up on later polls. Each run counts towards the monthly workflow runs.
- **Retries.** Failed steps are retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. **Delete file** treats a file that is already gone as success, so a retry after a partial failure doesn't fail the run.
- **Private agent.** Through an agent, file transfers run inside the client's network and the agent sends the data to Nimbus over its outbound TLS connection. If the agent sends no heartbeat for 2 minutes it shows **Offline**, and steps on its connections fail with CONN-503 until it is back.

## Troubleshooting

| Error | Cause on the SFTP server | Fix |
|---|---|---|
| CONN-401 | Password changed, public key removed from `authorized_keys`, or the server's host key no longer matches the pinned fingerprint. | Update the credentials, or confirm the new fingerprint with the server administrator, then click **Reconnect**. |
| CONN-403 | The account can't write to, or list, the directory. | Ask the client to fix the directory permissions for the Nimbus user. |
| CONN-404 | The file or directory doesn't exist, often because an earlier run already moved it. | Check the path; make sure only one workflow processes each directory. |
| CONN-503 | The server refused the connection, or the private connector agent is offline. | Check that the SFTP service is running; check the agent under **Settings > Agents**. |
| WF-200 | A transfer took longer than 10 minutes. | Check the link speed between the server and Nimbus or the agent, and split very large exports. |

Treat a host key change as a security event. A legitimate change, such as a rebuilt server, should be announced by the client before it happens; an unannounced one should be confirmed with the server administrator before anyone accepts the new fingerprint.
