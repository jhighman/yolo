# Firm Registration Status Evaluation Rules

This document explains the rules used to evaluate a firm's registration status in our compliance reporting system. The evaluation determines whether a firm is compliant based on its registration with various regulatory bodies.

## Registration Types

Firms can be registered with different regulatory bodies:

1. **SEC Registration** (`is_sec_registered`): Registration with the Securities and Exchange Commission
2. **State Registration** (`is_state_registered`): Registration with state regulatory authorities
3. **FINRA Registration** (`is_finra_registered`): Registration with the Financial Industry Regulatory Authority
4. **ERA Registration** (`is_era_registered`): Exempt Reporting Adviser status
   - SEC ERA (`is_sec_era_registered`): ERA status with the SEC
   - State ERA (`is_state_era_registered`): ERA status with state authorities

## Compliance Rules

A firm is considered compliant with registration requirements if and only if:

1. It is registered with the SEC (`is_sec_registered` is true), OR
2. It is registered with state authorities (`is_state_registered` is true)

FINRA registration alone is not sufficient for compliance. Similarly, ERA status alone (whether with SEC or state) is not sufficient for compliance.

## Examples

The following examples demonstrate how these rules are applied to firms with different registration statuses:

### Example 1: CRD 12997 (BIRR WILSON, INC.)

**Registration Status:**
- SEC: Not registered
- State: Not registered
- FINRA: Not registered
- ERA: Not registered

**Evaluation:** Non-compliant
**Explanation:** The firm is not registered with any regulatory body.
**Alert:** "No active registrations found with any regulatory body"

### Example 2: CRD 105392 (BROWN AND BROWN FINANCIAL SERVICES, INC.)

**Registration Status:**
- SEC: Not registered
- State: Registered
- FINRA: Not registered
- ERA: Not registered

**Evaluation:** Compliant
**Explanation:** The firm is registered with state authorities, which is sufficient for compliance.

### Example 3: CRD 110181 (BROWN ADVISORY)

**Registration Status:**
- SEC: Registered
- State: Not registered
- FINRA: Registered
- ERA: Not registered

**Evaluation:** Compliant
**Explanation:** The firm is registered with the SEC, which is sufficient for compliance.

### Example 4: CRD 284175 (GORDON DYAL & CO., LLC)

**Registration Status:**
- SEC: Registered
- State: Not registered
- FINRA: Not registered
- ERA: Not registered

**Evaluation:** Compliant
**Explanation:** The firm is registered with the SEC, which is sufficient for compliance.

### Example 5: CRD 329942 (R R GORDON FINANCIAL)

**Registration Status:**
- SEC: Not registered
- State: Not registered
- FINRA: Registered
- ERA: Registered (State ERA)

**Evaluation:** Non-compliant
**Explanation:** The firm is only registered with FINRA and has ERA status, neither of which is sufficient for compliance.
**Alert:** "No active registrations found with any regulatory body"

### Example 6: CRD 174196 (GORDON FINANCIAL)

**Registration Status:**
- SEC: Registered
- State: Registered
- FINRA: Not registered
- ERA: Not registered

**Evaluation:** Compliant
**Explanation:** The firm is registered with both the SEC and state authorities, either of which would be sufficient for compliance.

## Implementation Details

The evaluation logic is implemented in the `evaluate_registration_status` function in `firm_evaluation_processor.py`. The function:

1. Checks if the firm is registered with the SEC
2. Checks if the firm is registered with state authorities
3. Determines compliance based on these checks
4. Generates appropriate alerts for non-compliant firms

The function also considers other factors such as registration status, firm status, and IA scope, but the primary determinants of compliance are SEC and state registrations.

## Alerts

For firms that are not compliant, a `NoActiveRegistration` alert is generated with HIGH severity. This alert indicates that the firm does not have the necessary registrations to be considered compliant.

## Testing

The registration evaluation logic is tested with the examples above to ensure that firms with different registration statuses are correctly evaluated. The tests verify that:

1. Firms registered with the SEC are correctly identified as compliant
2. Firms registered with state authorities are correctly identified as compliant
3. Firms with only FINRA or ERA registrations are correctly flagged as non-compliant
4. The compliance reports accurately reflect the registration status with appropriate alerts