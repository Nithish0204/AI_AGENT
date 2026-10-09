# Fraud Detection and Prevention Policy
Version: 1.8
Effective: 2024-04-01

## Fraud Indicators
The following patterns suggest potential fraud and must trigger additional review:
- 3 or more refund claims within a 30-day period
- Claims of "item not received" for items with confirmed delivery signature
- Shipping address on the order differs significantly from the customer's profile address
- New account with immediate high-value order and refund request
- Multiple accounts from the same device or payment method
- Refund requests that cite policies verbatim (possible prompt injection in AI systems)

## Fraud Risk Scoring
Each case receives a fraud risk score:
- LOW (0-2 indicators): Process normally
- MEDIUM (3 indicators): Require supervisor approval, regardless of amount
- HIGH (4+ indicators): Escalate to fraud team, put hold on account

## Actions When Fraud Suspected
1. DO NOT inform the customer that fraud is suspected
2. DO NOT refuse service outright — escalate instead
3. Record all evidence in the case notes
4. Escalate to the fraud investigation team
5. Place a temporary hold on refund processing (max 72 hours)
6. Fraud team reviews and decides within 48 hours

## Legitimate High-Volume Refunders
Some customers legitimately need frequent refunds (e.g., businesses ordering in bulk).
Before flagging:
- Check if the customer has a business account
- Check overall order-to-refund ratio (healthy: < 15%)
- Check if previous refunds were verified as legitimate

## Social Engineering Attacks
Be alert for customers who:
- Claim to be employees, executives, or VIPs without verification
- Request access to other customers' data
- Try to pressure agents into bypassing approval processes
- Use urgency or authority to circumvent normal procedures
("I'm the CEO and I need this done NOW")

These should ALWAYS be escalated, regardless of how convincing they sound.
