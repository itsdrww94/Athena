# Google Cloud Storage (GCS) Configuration Guide

## Overview
Athena can upload files to Google Cloud Storage for cloud backup and cross-device access. This requires authentication to your GCP project.

---

## Option 1: Application Default Credentials (Recommended)

Run this command once on your machine:

```powershell
gcloud auth application-default login
```

This opens a browser to authenticate with your Google account.

---

## Option 2: Service Account Key

1. Go to [GCP Console > IAM > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Create a new service account with "Storage Object Admin" role
3. Download the JSON key file
4. Add to your `.env`:

```
GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\your-key.json
```

---

## Required Environment Variable

Add to your `.env` file:

```
GCS_BUCKET=your-bucket-name
```

---

## Verification

After configuration, Athena will automatically upload processed files to:
```
gs://your-bucket-name/athena_data/...
```

You can check upload status with:
```
athena> /status
```

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| "Could not automatically determine credentials" | Run `gcloud auth application-default login` |
| "Permission denied" | Ensure bucket exists and account has write access |
| "GCS_BUCKET not set" | Add `GCS_BUCKET=...` to your `.env` file |
