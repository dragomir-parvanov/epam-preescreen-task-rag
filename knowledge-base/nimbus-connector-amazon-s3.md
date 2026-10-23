---
id: nimbus-connector-amazon-s3
title: Amazon S3 Connector
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2025-12-15
owner: Integrations Team
---

The Amazon S3 connector gives workflows access to objects in S3 buckets: it can start a run when a new object lands under a prefix, and it can upload, download, list, copy and delete objects. It has been in the catalogue since 3.0.0 and authenticates in one of two ways, with an IAM user's access key or with an IAM role that Nimbus assumes using an external id.

The IAM role is the better choice for most clients: no long-lived secret leaves their AWS account, and they can revoke Nimbus's access by editing the role's trust policy.

## Prerequisites

- An AWS account holding the bucket, and someone who can create IAM roles or users and policies in it.
- An IAM policy that grants the S3 permissions the workflows use (example below), attached to the role or user.
- If the bucket uses SSE-KMS encryption, `kms:Decrypt` and `kms:GenerateDataKey` on the key in the same policy.
- A Nimbus Builder or Admin to create the connection, and room under the Plan Tier's active-connector limit ([Plan Tiers and Entitlements](nimbus-plan-tiers.md)).

Each action needs these permissions:

| Trigger or action | IAM actions |
|---|---|
| New object (trigger), List objects | `s3:ListBucket` on the bucket |
| Download object | `s3:GetObject` on the objects |
| Upload object | `s3:PutObject` on the objects |
| Copy object | `s3:GetObject` on the source, `s3:PutObject` on the destination |
| Delete object | `s3:DeleteObject` on the objects |
| Test connection | `s3:GetBucketLocation` on the bucket |

An example policy that limits Nimbus to one prefix of one bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "NimbusList",
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": "arn:aws:s3:::acme-finance-exports",
      "Condition": { "StringLike": { "s3:prefix": ["nimbus/*"] } }
    },
    {
      "Sid": "NimbusObjects",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::acme-finance-exports/nimbus/*"
    }
  ]
}
```

## Creating the connection

1. In Nimbus, open **Connections > New connection** and choose **Amazon S3**.
2. Enter a **Connection name** and the bucket's **Region**, for example `eu-west-1`.
3. Under **Authentication**, choose **IAM role** or **Access key**.
4. For **IAM role**: Nimbus shows its AWS account id and a generated **External id**, unique to this connection. In AWS, create a role with a custom trust policy that allows `sts:AssumeRole` for that account on the condition `"sts:ExternalId": "<the external id shown>"`, attach the permissions policy, and paste the role's ARN into **Role ARN**.
5. For **Access key**: create an IAM user with only the permissions policy attached, create an access key for it, and paste the **Access key ID** and **Secret access key**.
6. Click **Save**, then **Test connection**. Nimbus calls `GetBucketLocation` on the **Default bucket**, if you set one, and shows **Connected**.

The external id stops another Nimbus workspace from assuming the client's role even if it learns the role ARN. Don't reuse it across roles, and don't remove the condition from the trust policy.

## Triggers and actions

| Name | Kind | Description |
|---|---|---|
| New object | Polling trigger | Starts one run per new object under a bucket and **Prefix**, e.g. `incoming/invoices/`. Optional **Suffix** filter such as `.csv`. |
| Upload object | Action | Writes a file from an earlier step to a key; optional content type and storage class. |
| Download object | Action | Reads an object into a file that later steps can use. |
| List objects | Action | Lists keys, sizes and last-modified times under a prefix. |
| Copy object | Action | Copies within a bucket or across buckets the connection can reach. |
| Delete object | Action | Deletes one key. On a versioned bucket this adds a delete marker. |

Keys ending in `/` (folder placeholders from the S3 console) never start runs.

## Field mapping

Object keys are built with expressions. A common pattern is to file each upload under a date path and a name from the trigger:

```yaml
# Step: Upload object
bucket: acme-finance-exports
key: "nimbus/exports/{{now()}}/{{lower(trigger.body.customer_code)}}.csv"
file: "{{steps.build_csv.output.file}}"
content_type: text/csv
metadata:
  source-workflow: "{{trigger.body.workflow_id}}"
```

The **New object** trigger outputs `bucket`, `key`, `size`, `etag` and `last_modified`. Pass `{{trigger.body.key}}` straight into **Download object** to fetch the file that started the run.

## Limits and behaviour

- **Polling.** The trigger lists the prefix every 5 minutes and starts runs for objects with a `LastModified` time after the previous poll. Objects already in the prefix when the workflow is activated are skipped. Overwriting an existing key counts as a new object.
- **Paging.** S3 returns at most 1,000 keys per list call. **List objects** follows the continuation token up to **Max keys** (default 1,000, maximum 50,000); a poll processes up to 1,000 new objects, and the rest wait for the next poll.
- **File size.** Upload and download handle objects up to 100 MB, the Nimbus limit for a file passed between steps. Larger objects fail before transfer; copy them with **Copy object**, which happens inside S3, or split them upstream.
- **Retries.** Failed steps are retried 3 times by default, after 30 seconds, 2 minutes and 10 minutes. S3's `SlowDown` responses are reported as CONN-429 and retried after a back-off.

## Troubleshooting

| Code | AWS error | What to check |
|---|---|---|
| CONN-401 | `InvalidAccessKeyId`, `SignatureDoesNotMatch` | The access key was deactivated, deleted or mistyped. Create a new key and update the connection. |
| CONN-401 | `AccessDenied` on `sts:AssumeRole` | The trust policy doesn't name the Nimbus account or the external id doesn't match. |
| CONN-403 | `AccessDenied` on an S3 or KMS action | A permission is missing from the policy, the key is outside the allowed prefix, or a bucket policy denies it. |
| CONN-404 | `NoSuchKey`, `NoSuchBucket` | The key was moved or deleted, or the bucket name or region is wrong. |
| CONN-429 | `SlowDown` | S3 asked for fewer calls; Nimbus retries. |
| WF-400 | – | The key expression resolved to empty. |
