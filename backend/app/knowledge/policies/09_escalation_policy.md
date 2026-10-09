# Escalation Policy
Version: 1.6
Effective: 2024-02-15

## When to Escalate
A case MUST be escalated to a human supervisor when:
- The resolution amount exceeds ₹10,000
- The customer mentions legal action, lawyers, or regulatory complaints
- The customer explicitly requests to speak to a manager/supervisor
- The case involves safety concerns or potential harm
- The AI system's confidence score is below 0.60
- The fraud detection system flags the case
- Two or more resolution attempts have failed
- The customer remains angry/unsatisfied after the initial resolution
- The case involves media or public relations risk
- Data privacy breach or potential data leak

## Escalation Levels
1. Level 1 - Supervisor: Amount ₹2,000-₹10,000, moderate complexity
2. Level 2 - Manager: Amount ₹10,000-₹50,000, high complexity, VIP issues
3. Level 3 - Director: Amount above ₹50,000, legal threats, media risk

## Escalation Handoff Requirements
When escalating, the AI agent MUST provide:
- Complete case summary (1-2 paragraphs)
- Customer sentiment assessment
- All evidence gathered (order data, policies, citations)
- Recommended resolution with confidence score
- Reason for escalation
- Priority level (critical/high/medium)

## Response Time After Escalation
- Critical: Human must respond within 1 hour
- High: Human must respond within 4 hours
- Medium: Human must respond within 24 hours

## De-escalation
If a supervisor resolves the case:
- Response is sent to the customer
- Case is marked as resolved
- Resolution is logged for future AI training
- Customer satisfaction follow-up is scheduled
