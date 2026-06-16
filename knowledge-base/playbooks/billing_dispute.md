# Billing Disputes — Handling Playbook

## When This Playbook Applies
Use this playbook when a customer:
- Reports an unexpected or unrecognised charge
- Believes they were charged the wrong amount
- Claims a refund has not arrived
- Disputes a subscription or renewal charge

---

## Step 1: Verify the Charge

Use the `lookup_customer_profile` and `lookup_order_status` CRM tools to:
- Confirm the customer's identity
- Retrieve the order or transaction in question
- Check whether the amount matches what the customer was quoted

If the charge cannot be found in our system, ask the customer for:
- The date of the charge
- The exact amount
- The last 4 digits of the card charged
- Their order ID (if they have it)

---

## Step 2: Classify the Dispute

| Dispute Type | Next Action |
|---|---|
| Duplicate charge | Verify in CRM; issue refund for the duplicate if confirmed |
| Charged wrong amount | Compare to order summary; issue adjustment refund if confirmed |
| Unrecognised charge | Check if charge is from a subscription or a family member; if still unrecognised, escalate to finance team |
| Refund not received | Check refund status (see Step 4) |
| Subscription renewal | Confirm whether customer consented to auto-renew; process cancellation and pro-rata refund if applicable |

---

## Step 3: Issuing a Refund (Confirmed Error)

1. Confirm the error with the customer and apologise sincerely.
2. Initiate the refund via the agent console — select the order line item and enter the refund amount.
3. Inform the customer:
   - Refunds are returned to the original payment method.
   - Credit/debit card refunds typically appear within **5–10 business days** depending on the issuing bank.
   - PayPal refunds typically appear within **3–5 business days**.
4. Provide the customer with a refund confirmation number.

---

## Step 4: Refund Status Check

If a customer says a refund has not arrived:
1. Use the CRM to confirm the refund was processed and note the processing date.
2. If the refund was processed less than **10 business days** ago, inform the customer of the typical bank processing window and ask them to wait.
3. If it has been **more than 10 business days**, escalate to the finance team with:
   - Customer account ID
   - Order ID
   - Refund amount and processing date
   - Last 4 digits of the card

---

## Step 5: Chargeback Situation

If the customer has already filed a chargeback with their bank:
- Do **not** process a manual refund at the same time — this would result in a double refund.
- Inform the customer that the chargeback process is now between them and their bank.
- Log the chargeback in the CRM and flag the order for the finance team.
- Outcome: if the chargeback is resolved in our favour, the customer owes nothing; if in the customer's favour, the bank issues the refund.

---

## Escalation Criteria
Escalate to the finance team if:
- Total disputed amount is over $500
- The charge cannot be explained after CRM review
- Suspected fraud or identity theft is involved
- A chargeback has been filed
- The customer is threatening legal action

## Communication Guidelines
- Always acknowledge the customer's concern without admitting fault until the charge is verified.
- Use language like: *"I understand how frustrating an unexpected charge can be. Let me look into this for you right now."*
- Never ask for full card numbers — last 4 digits are sufficient for verification.
- Always confirm next steps and expected timeline before closing the conversation.
