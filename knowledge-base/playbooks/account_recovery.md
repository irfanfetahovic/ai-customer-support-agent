# Account Recovery Playbook
# Keywords: forgot password, can't log in, login help, locked out of account, lost account access, password reset, reset password link, account recovery, login issues, unable to login, password not working, recovery email, change email, account locked

## What This Covers

Customers contact us when they **forgot their password**, **can't log in**, are **locked out of their account**, or need to **reset their password**. Common reasons include:

- Forgot password / password not working → needs a password reset link
- Can't log in after multiple failed attempts → account may be temporarily locked
- Lost access to the recovery email → needs email change before password reset
- Lost MFA device → needs MFA reset
- Suspected account takeover → immediate lock + security escalation

Use the scenario below that matches the customer's situation.

## Frequently Asked Questions About Account Access

**Q: I forgot my password — how do I reset it?**
Use the "Forgot password" link on the login page. A **password reset link** will be emailed to your registered address and is valid for **60 minutes**.

**Q: I'm locked out of my account — how do I get back in?**
Accounts are **locked for 30 minutes** after 5 consecutive failed login attempts. After waiting, use the "Forgot password" flow to set a fresh password.

**Q: My password reset email never arrived — what do I do?**
Check your spam/junk folder. If still not there after 5 minutes, confirm the exact email address on file and re-request the reset link. Contact support if the problem persists.

**Q: I can no longer access my recovery email — how do I reset my password?**
Contact support. We will verify your identity through order history or registered phone number, update your recovery email, and then guide you through the forgot password flow.

**Q: How do I recover my account if I'm locked out?**
Wait 30 minutes for the automatic lockout to lift, then use "Forgot password" to set a new password. If the lockout keeps recurring, contact support to escalate to the security team.

## Overview

This playbook covers all account access issues including: forgotten passwords, password reset emails not arriving, locked accounts, lost MFA devices, changed recovery email addresses, and suspected account takeovers.

---

## Forgotten Password or Changed Recovery Email

### If the recovery email address is still accessible
1. Direct the customer to the login page → click **"Forgot password"**.
2. Enter the email address on the account and submit.
3. A reset link is sent; valid for **60 minutes**. Check spam/junk if not received within 5 minutes.
4. If no email arrives: confirm the exact email on file; try any alternate addresses they may have used.

### If the recovery email address has changed or is no longer accessible
1. Use `lookup_customer_profile` to verify identity via order history, phone number, or full name + address.
2. Once identity is confirmed, submit an **email change request** via the account management panel.
3. Verification is sent to the **new** email; the customer must confirm within 24 hours.
4. Notify the customer that the old email will receive a security notification (expected behaviour).
5. After the new email is confirmed, direct the customer to use the "Forgot password" flow with the new address.

---

## Scenario 3: Lost MFA / Authenticator Device
1. Ask the customer if they have backup codes (provided during MFA setup).
   - If yes: direct them to use a backup code at login.
2. If no backup codes:
   - Verify identity through order history or registered phone number.
   - Submit an MFA reset request to the account security team (SLA: 1 business day).
   - Inform the customer they will receive an email with next steps within 24 hours.

---

## Scenario 4: Account Locked (Too Many Failed Attempts)
- Accounts are temporarily locked for **30 minutes** after 5 consecutive failed login attempts.
- Inform the customer to wait 30 minutes and then use the "Forgot password" flow to set a fresh password.
- If the lockout recurs, escalate to the security team.

---

## Scenario 5: Suspected Account Takeover
**Immediate actions:**
1. Lock the account immediately using the agent console.
2. Escalate to the account security team — do NOT attempt recovery without their involvement.
3. Inform the customer the account has been secured and the security team will contact them within 2 hours.
4. Log the incident with timestamps and any suspicious activity details.

---

## Communication Guidelines
- Always acknowledge urgency and reassure the customer: *"I can help secure your account right away."*
- Never ask for the customer's full password, full card number, or full SSN.
- Only request the last 4 digits of a card or the last 4 digits of a phone number for verification.
- Share exact next steps and expected timelines at every stage.

## When To Escalate to Account Security Team
- Suspicious login patterns detected (unusual location/device)
- Repeated failed verification attempts during recovery
- Suspected or confirmed account takeover
- Customer reports unauthorised orders placed on their account

## Customer-Facing Opening Template
*"I can help recover your account right away. For your security, I'll first verify ownership and then guide you through a secure reset. This usually takes just a few minutes."
