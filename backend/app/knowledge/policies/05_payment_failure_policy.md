# Payment Failure and Double Charge Policy
Version: 2.0
Effective: 2024-02-01

## Payment Failure Handling
When a payment fails but the amount is deducted:
- This is typically a bank hold, not an actual charge
- Amount is usually auto-reversed within 3-5 business days
- If not reversed within 5 days, initiate manual reversal

## Action Steps for Payment Failure
1. Verify the payment status in the payment gateway
2. If payment was captured but order not created: initiate immediate refund
3. If payment is in "pending" state: advise customer to wait 3-5 business days
4. If payment shows as "failed": amount will auto-reverse, no action needed

## Double Charge Resolution
When a customer is charged twice for the same order:
- PRIORITY: This is always treated as HIGH urgency
- Verify both charges in the payment system
- Immediately refund the duplicate charge
- No approval needed for refunds of exact duplicate amounts
- Send confirmation with transaction IDs of both the charge and refund

## Double Charge Compensation
- Apologize for the inconvenience
- Process refund within 24 hours (expedited)
- Offer ₹200 store credit as goodwill gesture
- VIP customers: ₹500 store credit + priority processing

## Prevention Note
If a customer reports multiple double charges or payment issues:
- First occurrence: Handle normally
- Second occurrence: Flag for payment team review
- Third occurrence: Escalate to payment engineering team
