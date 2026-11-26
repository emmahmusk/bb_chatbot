# BullBear Risk website

This is a standalone, Django-template landing page for BullBear Risk. It uses
the same dark navy, electric blue, violet and green palette as the BullBear
web app and explains the sportsbook risk-monitoring model already implemented
in `chatbot_service`.

The production artifact is static: Django renders the template and collects
CSS, JavaScript and images into `dist/`. The intended production path is
`https://bullbearprime.com` and `https://www.bullbearprime.com` through
CloudFront to a **private** S3 bucket in `eu-north-1`. No Django server,
database, API key or runtime container is needed in production.

```text
Visitor -- HTTPS --> CloudFront -- signed OAC request --> private S3 bucket
```

## Local preview

```powershell
cd risk_website
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

The page uses Django's `{% static %}` template tag for every CSS, JavaScript
and image asset. WhiteNoise is enabled for local development. The build
command renders `index.html` and collects assets into `dist/static/` for
CloudFront and S3.

The optional Django service can be run with Docker:

```powershell
docker build -t bullbear-risk-website .
docker run --rm -p 8000:8000 bullbear-risk-website
```

Its health endpoint is `GET /health/`.

If Django reports `ModuleNotFoundError: No module named 'whitenoise'`, the
virtual environment predates the current dependency list. From this directory,
run:

```powershell
python -m pip install -r requirements.txt
python manage.py runserver
```

To create the exact static artifact used by S3/CloudFront:

```powershell
python manage.py build_landing --output dist
```

## Environment variables

Only the public links and branding are injected at build time:

| Variable | Required | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Local only | Local Django signing key; never needed by S3. |
| `DEBUG` | Local only | Set `true` for local development. |
| `ALLOWED_HOSTS` | Local only | Hosts accepted by local Django. |
| `CONTACT_EMAIL` | Recommended | Address used by the walkthrough CTAs. |

## AWS architecture and first-time setup

The bucket is storage only. Do not enable S3 static website hosting and do
not make the bucket public. CloudFront uses the S3 **regional REST endpoint**
and Origin Access Control (OAC), which signs requests so visitors can only
read the site through CloudFront.

1. Use the dedicated bucket `bullbearprime.com` in `eu-north-1`. The deploy
   workflow uses `aws s3 sync --delete`, so do not put unrelated files in this
   bucket.
2. In S3, enable all four Block Public Access settings, disable static website
   hosting, and keep default encryption enabled. Do not add a public-read ACL
   or public bucket policy.

   To enforce the public-access block with the AWS CLI before deployment:

   ```powershell
   aws s3api put-public-access-block --bucket bullbearprime.com --region eu-north-1 --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
   ```

   If S3 static website hosting was previously enabled, disable it after the
   CloudFront distribution is ready:

   ```powershell
   aws s3api delete-bucket-website --bucket bullbearprime.com --region eu-north-1
   ```
3. **Inspect and back up the existing bucket policy and contents before the
   stack is created.** The template owns the bucket policy and replaces the
   entire current policy with a rule that lets only this CloudFront distribution
   read objects. This can break another site or service using the bucket. In
   PowerShell, inspect the current policy and objects:

   ```powershell
   aws s3api get-bucket-policy --bucket bullbearprime.com --region eu-north-1
   aws s3 ls s3://bullbearprime.com --recursive --human-readable --summarize
   ```

   If there is a policy, save its JSON somewhere safe before continuing. An
   `NoSuchBucketPolicy` response means there is no existing policy to preserve.
   Confirm the bucket contains only this site's files. The GitHub workflow uses
   `aws s3 sync --delete`, which removes objects not present in the new build.
   Do not use this workflow with a shared bucket or one containing unrelated
   files. If the bucket is shared, stop and choose a dedicated bucket or change
   the deployment strategy first.
4. Request or use an ACM certificate in **us-east-1** covering both
   `bullbearprime.com` and `www.bullbearprime.com`. Complete DNS validation and
   wait for the certificate status to become `Issued`. CloudFront will reject
   the custom domains if the certificate is missing either name or is in the
   wrong region.
5. Deploy `infrastructure/cloudfront-s3.yaml` from CloudFormation in
   **us-east-1**. The S3 bucket stays in `eu-north-1`; this is the CloudFormation
   stack's region, not a move of the bucket. The template's bucket-policy
   resource manages a bucket in another region, and AWS requires that stack to
   be deployed in `us-east-1` for this cross-region policy operation. Use the
   bucket name `bullbearprime.com`, bucket region `eu-north-1`, and issued
   certificate ARN. **Leave `HostedZoneId` blank for this first stack creation,**
   even if DNS is in Route 53. The template creates the CloudFront distribution,
   private S3 origin with OAC, HTTPS redirect and security headers. IPv6 is
   enabled in the distribution to match the optional AAAA records.
6. Wait until CloudFormation completes and the CloudFront distribution status
   is **Deployed**. Record the stack outputs `DistributionId` and
   `DistributionDomainName`. CloudFront can take several minutes to finish its
   first deployment.
7. Only after the distribution is **Deployed**, configure DNS:

   - **Route 53:** verify the hosted-zone ID is for the **public**
     `bullbearprime.com` zone. Inspect existing root and `www` A/AAAA records
     first. Then update the CloudFormation stack, set `HostedZoneId` to that
     zone ID and keep all other parameters unchanged. The template creates or
     updates root and `www` A/AAAA aliases to this CloudFront distribution.
   - **Another DNS provider:** leave `HostedZoneId` blank. Point `www` to the
     distribution hostname using a CNAME, and point the apex using the
     provider's ALIAS, ANAME or CNAME-flattening feature. A normal CNAME cannot
     be used at the apex. Confirm the registrar delegates the domain to the DNS
     provider where you are making these changes.

   The bucket policy is retained if the stack is deleted, so deleting the stack
   does not automatically restore the old policy.

## GitHub/AWS deployment variables

Configure these in the repository that contains this directory:

- Secret `AWS_ROLE_TO_ASSUME`: IAM role trusted by GitHub Actions OIDC.
- Variable `AWS_REGION`: set to `eu-north-1` (the workflow default; this is the
  S3 bucket's region, not the CloudFormation stack region).
- Variable `RISK_WEBSITE_BUCKET`: set to `bullbearprime.com` (the workflow default).
- Variable `CLOUDFRONT_DISTRIBUTION_ID`: required; use the CloudFormation output.
- Variable `CONTACT_EMAIL`: optional; defaults to `risk@bbbprediction.com`.

The GitHub Actions workflow is at the repository root:
`.github/workflows/cd-risk-website-s3.yaml`. The IAM role needs
`s3:GetBucketLocation` and `s3:ListBucket` on the bucket, `s3:GetObject`,
`s3:PutObject`, and `s3:DeleteObject` on its objects, plus
`cloudfront:CreateInvalidation` on the distribution. The
workflow invalidates CloudFront after every successful upload. `--delete`
keeps the bucket in sync with the built site, which is why the bucket must be
dedicated to this website.

Configure the GitHub OIDC role trust policy for this repository and the
`main` branch, and grant only the S3 and CloudFront actions listed above. Store
the role ARN in the Actions secret `AWS_ROLE_TO_ASSUME`; do not store long-lived
AWS access keys in GitHub. The first deployment should be run only after the
CloudFormation stack is deployed and the CloudFront distribution ID is set.

To build locally, run `python manage.py build_landing --output dist`; upload
the contents of `dist/` to the bucket root, then invalidate `/*` in
CloudFront. Do not upload the `risk_website/` source directory itself.

The landing page contains no sportsbook credentials and does not call OpticOdds
directly. Live risk data remains inside the authenticated monitor application.
