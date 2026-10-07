/**
 * Gmail API Email Service
 * Uses Google OAuth 2.0 via the official googleapis package.
 * Never exposes credentials. Called as a CLI subprocess from Python backend.
 *
 * Usage:
 *   node gmailService.js <to_email> <user_name> <reset_url>
 *
 * Required env vars:
 *   GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REDIRECT_URI,
 *   GMAIL_REFRESH_TOKEN, GMAIL_USER
 */

'use strict';

const path = require('path');
const { google } = require('googleapis');

// Load .env from project root (two levels up from backend/utils/)
require('dotenv').config({ path: path.join(__dirname, '..', '..', '.env') });
// Also try the backend folder
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

// ── OAuth2 Client ──────────────────────────────────────────────────────────────
function buildOAuth2Client() {
  const clientId     = process.env.GMAIL_CLIENT_ID;
  const clientSecret = process.env.GMAIL_CLIENT_SECRET;
  const redirectUri  = process.env.GMAIL_REDIRECT_URI;
  const refreshToken = process.env.GMAIL_REFRESH_TOKEN;

  if (!clientId || !clientSecret || !refreshToken) {
    throw new Error(
      'Missing Gmail API credentials. Set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, ' +
      'GMAIL_REDIRECT_URI, and GMAIL_REFRESH_TOKEN in your .env file.'
    );
  }

  const oauth2Client = new google.auth.OAuth2(clientId, clientSecret, redirectUri);
  oauth2Client.setCredentials({ refresh_token: refreshToken });
  return oauth2Client;
}

// ── Base64URL encoder (Gmail API requirement) ──────────────────────────────────
function encodeBase64URL(text) {
  return Buffer.from(text)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

// ── Build RFC 2822 raw email message ──────────────────────────────────────────
function buildRawMessage(from, to, subject, htmlBody) {
  const boundary = `voltwise_${Date.now()}`;
  const plainText = htmlBody.replace(/<[^>]+>/g, '').replace(/\s{2,}/g, ' ').trim();

  const message = [
    `MIME-Version: 1.0`,
    `From: ${from}`,
    `To: ${to}`,
    `Subject: ${subject}`,
    `Content-Type: multipart/alternative; boundary="${boundary}"`,
    ``,
    `--${boundary}`,
    `Content-Type: text/plain; charset="UTF-8"`,
    ``,
    plainText,
    ``,
    `--${boundary}`,
    `Content-Type: text/html; charset="UTF-8"`,
    ``,
    htmlBody,
    ``,
    `--${boundary}--`,
  ].join('\r\n');

  return encodeBase64URL(message);
}

// ── Professional HTML Email Template ──────────────────────────────────────────
function buildEmailHTML(userName, resetUrl) {
  const currentYear = new Date().getFullYear();
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset Your Password — VoltWise</title>
</head>
<body style="margin:0;padding:0;background-color:#0b0f19;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0b0f19;padding:30px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background:#111827;border-radius:16px;border:1px solid rgba(255,255,255,0.08);overflow:hidden;box-shadow:0 10px 40px rgba(0,0,0,0.5);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1e293b,#0f172a);padding:28px 32px;text-align:center;border-bottom:1px solid rgba(255,255,255,0.06);">
              <span style="font-size:28px;color:#fbbf24;">⚡</span>
              <span style="font-size:22px;font-weight:700;color:#ffffff;margin-left:8px;letter-spacing:-0.5px;">VoltWise</span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 32px;">
              <h2 style="margin:0 0 12px;font-size:22px;font-weight:700;color:#f8fafc;letter-spacing:-0.3px;">
                Reset Your Password
              </h2>
              <p style="margin:0 0 8px;font-size:15px;color:#94a3b8;line-height:1.6;">
                Hello <strong style="color:#f8fafc;">${userName}</strong>,
              </p>
              <p style="margin:0 0 28px;font-size:15px;color:#94a3b8;line-height:1.6;">
                We received a request to reset your VoltWise account password.
                Click the button below to create a new password.
              </p>

              <!-- CTA Button -->
              <table cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td align="center" style="padding:4px 0 28px;">
                    <a href="${resetUrl}"
                       target="_blank"
                       style="display:inline-block;background:linear-gradient(135deg,#3b82f6,#2563eb);color:#ffffff;text-decoration:none;font-weight:700;font-size:15px;padding:14px 36px;border-radius:10px;letter-spacing:0.3px;box-shadow:0 4px 16px rgba(59,130,246,0.4);">
                      🔐 Reset Password
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Expiry Notice -->
              <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);border-radius:10px;padding:14px 18px;margin-bottom:24px;">
                <p style="margin:0;font-size:13px;color:#f59e0b;line-height:1.5;">
                  ⏱️ <strong>This link expires in 15 minutes.</strong>
                  If you don't reset your password in time, you'll need to make a new request.
                </p>
              </div>

              <!-- Fallback link -->
              <p style="margin:0 0 6px;font-size:12px;color:#64748b;line-height:1.5;">
                If the button doesn't work, copy and paste this link into your browser:
              </p>
              <p style="margin:0 0 24px;font-size:12px;word-break:break-all;color:#3b82f6;">
                ${resetUrl}
              </p>

              <!-- Security note -->
              <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:20px;">
                <p style="margin:0;font-size:12px;color:#64748b;line-height:1.6;">
                  🔒 If you didn't request a password reset, you can safely ignore this email.
                  Your password will remain unchanged. Do not share this link with anyone.
                </p>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#0f172a;padding:16px 32px;text-align:center;">
              <p style="margin:0;font-size:12px;color:#475569;">
                © ${currentYear} VoltWise Smart Electricity Analyzer. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;
}

// ── Main send function ─────────────────────────────────────────────────────────
async function sendPasswordResetEmail(toEmail, userName, resetUrl) {
  if (!toEmail || !userName || !resetUrl) {
    throw new Error('Missing required arguments: toEmail, userName, resetUrl');
  }

  const auth = buildOAuth2Client();
  const gmail = google.gmail({ version: 'v1', auth });

  const fromAddress = process.env.GMAIL_USER;
  if (!fromAddress) {
    throw new Error('GMAIL_USER environment variable is not set.');
  }

  const from     = `"VoltWise Support" <${fromAddress}>`;
  const subject  = 'Reset Your VoltWise Account Password';
  const htmlBody = buildEmailHTML(userName, resetUrl);

  const rawMessage = buildRawMessage(from, toEmail, subject, htmlBody);

  const response = await gmail.users.messages.send({
    userId: 'me',
    requestBody: { raw: rawMessage },
  });

  return {
    success: true,
    messageId: response.data.id,
    recipient: toEmail,
  };
}

// ── CLI Entry Point ────────────────────────────────────────────────────────────
if (require.main === module) {
  const [,, toEmail, userName, resetUrl] = process.argv;

  if (!toEmail || !userName || !resetUrl) {
    process.stderr.write(JSON.stringify({
      success: false,
      error: 'Usage: node gmailService.js <to_email> <user_name> <reset_url>'
    }) + '\n');
    process.exit(1);
  }

  sendPasswordResetEmail(toEmail, userName, resetUrl)
    .then(result => {
      process.stdout.write(JSON.stringify(result) + '\n');
    })
    .catch(err => {
      // Log detailed error to stderr only — never exposed to frontend
      process.stderr.write(
        JSON.stringify({ success: false, error: err.message || 'Gmail API error' }) + '\n'
      );
      process.exit(1);
    });
}

module.exports = { sendPasswordResetEmail };
