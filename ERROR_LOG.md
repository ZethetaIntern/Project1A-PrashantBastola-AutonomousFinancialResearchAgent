# Error Log — Autonomous Financial Research Agent

## Status

The assignment specifies seven deliberate errors across Parts A–E. Findings below are based on inspection of the original specification. Only supported findings should be counted as confirmed errors; unresolved candidates are explicitly identified.

## Findings

| ID | Location | Error and impact | Correction | Status |
|---|---|---|---|---|
| ERR-01 | Page 19, AB-4 — Memory Utilization | The definition describes a ratio of memory hits to external API calls, but the calculation says to multiply the two values. This does not calculate the defined ratio. | Calculate `memory_hits / total_api_calls`; handle a zero denominator. | Confirmed |
| ERR-02 | Page 24, A7.3 — Handling Ambiguous Queries | The specification places SCAP stress tests in 2007 after the Dodd–Frank Act. SCAP was conducted in 2009; Dodd–Frank was enacted in 2010. | Correct the dates and chronology. | Confirmed |
| ERR-03 | Page 42, C4.2 — Indian Market Research | The specification says Indian companies file Form 20-F annual returns with the MCA. Form 20-F is an SEC filing for eligible foreign private issuers, not the Indian MCA annual-return form. | Use the applicable MCA filing requirements for Indian companies. | Confirmed |
| ERR-04 | Page 21, A6.2 — Source Reliability Hierarchy | Forms 10-K and 10-Q are grouped together as audited filings. Form 10-Q generally contains unaudited interim financial statements. | Distinguish audited annual financial statements from generally unaudited quarterly statements. | Confirmed |
| ERR-05 | Page 63, E3.1 — OpenAI API Rate Limits | The specification attributes 500 RPM and 30,000 TPM to a GPT-4o “free tier.” The stated tier and limits are not established by the specification itself. | Verify the model-specific limits against the applicable API tier and documentation date. | Needs verification |
| ERR-06 | Page 63, E3.1 — OpenAI API Credits | The specification says new accounts receive $5 in free credits. This is a time-sensitive account-policy claim and cannot safely be treated as universally applicable without a dated source. | Verify the account-credit policy for the relevant date and region. | Needs verification; not yet counted as a confirmed error |
| ERR-07 | Parts A–E — Additional deliberate error | A seventh distinct error has not been established with sufficient evidence from the passages reviewed. | Inspect the remaining original passages and record the exact text and correction before counting it. | Unverified |

## Verification Notes

- The JSON Schema example on pages 10–11 places `required` at the correct schema-object level. It is not an error.
- The 1,024-dimensional configuration for `text-embedding-3-large` is possible; the omission of the default dimension alone does not establish an error.
- API rate limits and account-credit policies are time-sensitive and require dated evidence.
- Do not report seven confirmed errors until all seven have been verified.
