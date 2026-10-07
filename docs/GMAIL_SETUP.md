# Gmail API Setup Guide

This guide explains how to obtain Gmail API credentials for the VoltWise
password-reset email feature. Follow every step carefully.

---

## Overview

VoltWise uses **Gmail API + OAuth 2.0** (via the `googleapis` Node.js package)
to send password reset emails. This is more secure than SMTP because:

- No Gmail password is stored anywhere.
- OAuth 2.0 access tokens are short-lived and auto-refreshed.
- Credentials never leave the server.

---

## Step 1 — Open Google Cloud Console

Go to: <https://console.cloud.google.com/>

Sign in with the Gmail account you want to use for sending emails
(e.g. `yourapp@gmail.com`).

---

## Step 2 — Create or Select a Project

1. Click the project selector at the top of the page.
2. Click **"New Project"**.
3. Name it (e.g. `VoltWise`) and click **"Create"**.
4. Select your new project from the dropdown.

---

## Step 3 — Enable the Gmail API

1. In the left sidebar, click **"APIs & Services"** → **"Library"**.
2. Search for **"Gmail API"**.
3. Click it, then click **"Enable"**.

---

## Step 4 — Configure the OAuth Consent Screen

1. Go to **"APIs & Services"** → **"OAuth consent screen"**.
2. Select **"External"** (unless you have a Google Workspace org) → **"Create"**.
3. Fill in:
   - **App name**: `VoltWise`
   - **User support email**: your Gmail address
   - **Developer contact email**: your Gmail address
4. Click **"Save and Continue"** through the Scopes and Test Users screens.
5. Add your Gmail address as a **Test User** (required for external apps in testing mode).
6. Click **"Save and Continue"** → **"Back to Dashboard"**.

> **Note**: While your app is in "Testing" mode, only emails belonging to
> test users will work. For production, submit the app for verification.

---

## Step 5 — Create an OAuth 2.0 Client ID

1. Go to **"APIs & Services"** → **"Credentials"**.
2. Click **"+ Create Credentials"** → **"OAuth client ID"**.
3. Application type: **"Web application"**.
4. Name: `VoltWise Reset Email Client`.
5. Under **"Authorized redirect URIs"**, add:
   ```
   https://developers.google.com/oauthplayground
   ```
6. Click **"Create"**.
7. A dialog appears — copy and save:
   - **Client ID** → `GMAIL_CLIENT_ID`
   - **Client Secret** → `GMAIL_CLIENT_SECRET`

---

## Step 6 — Obtain a Refresh Token via OAuth Playground

1. Open: <https://developers.google.com/oauthplayground>
2. Click the **gear icon** (⚙️) in the top-right corner.
3. Tick **"Use your own OAuth credentials"**.
4. Enter your **Client ID** and **Client Secret** from Step 5.
5. Close the settings panel.
6. In the left panel under **"Step 1 — Select & authorize APIs"**, find:
   ```
   Gmail API v1
   ```
   and select the scope:
   ```
   https://www.googleapis.com/auth/gmail.send
   ```
7. Click **"Authorize APIs"**.
8. Sign in with the Gmail account you want to send from and grant permission.
9. In **Step 2**, click **"Exchange authorization code for tokens"**.
10. Copy the **Refresh token** → `GMAIL_REFRESH_TOKEN`.

> Refresh tokens don't expire unless revoked. Store it safely.

---

## Step 7 — Add Credentials to `.env`

Open (or create) the `.env` file in the project root and add:

```env
GMAIL_USER=your-sending-account@gmail.com
GMAIL_CLIENT_ID=123456789-abc...apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-...
GMAIL_REDIRECT_URI=https://developers.google.com/oauthplayground
GMAIL_REFRESH_TOKEN=1//0g...
FRONTEND_URL=http://127.0.0.1:5000
```

Replace each value with the real credential from the steps above.

---

## Step 8 — Test the Email Service

From the project root, run:

```bash
cd ELECTRIC_BILL_ANALAYZER-main

node backend/utils/gmailService.js \
  "recipient@example.com" \
  "Test User" \
  "http://127.0.0.1:5000/reset-password.html?token=test123"
```

Expected output:

```json
{"success":true,"messageId":"some-id","recipient":"recipient@example.com"}
```

If you see an auth error, double-check all four `GMAIL_*` variables.

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `invalid_client` | Wrong Client ID/Secret | Re-copy from Google Cloud Console |
| `invalid_grant` | Expired/wrong refresh token | Repeat Step 6 |
| `insufficient permissions` | Wrong scope | Ensure `gmail.send` scope was selected |
| `User not in test users` | App in Testing mode | Add your email in OAuth consent screen → Test Users |
| `GMAIL_USER not set` | Missing env var | Add `GMAIL_USER` to `.env` |

---

## Security Notes

- Never commit `.env` to version control (already in `.gitignore`).
- Never put `GMAIL_*` variables in the frontend or prefix them with `VITE_`.
- The raw reset token is **never stored** in MongoDB — only its SHA-256 hash.
- Reset links expire in **15 minutes** and are single-use.
