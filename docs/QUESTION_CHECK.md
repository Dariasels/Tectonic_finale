# Question check

Run with `cd backend && .venv/bin/python -m scripts.check_questions`. All data is simulated.

## Summary

- Curated questions: **77 of 77 pass** (understood correctly, right access, sensible result).
- Generated questions: 1274 (every country-specific topic in every country, English and a local-language synonym).
  - English phrasing understood (topic and country): **100.0%**
  - Local-language synonym understood: **100.0%**
  - Top answer is a correct document (hidden ground truth, 651 groups that contain both correct and outdated documents): **94.6%**
  - Search time: median 90 ms, 95th percentile 170 ms

## Curated questions

| Category | Question | As | Understood (topic/country/customer) | Results | Top | Verdict |
|---|---|---|---|---|---|---|
| HR policy | How much parental leave do I get in Belgium? | hr | parental_leave/BE/None | 10 | 84 green | OK |
| HR policy | parental leave Netherlands | pay | parental_leave/NL/None | 10 | 83 green | OK |
| HR policy | What is the retirement age in Belgium? | hr | pension/BE/None | 10 | 34 red | OK |
| HR policy | What is the retirement age in Germany? | hr | pension/DE/None | 10 | 86 green | OK |
| HR policy | company car policy in France | hr | company_car/FR/None | 10 | 31 red | OK |
| HR policy | sick leave rules Spain | es | sick_leave/ES/None | 10 | 89 green | OK |
| HR policy | How many remote days can I work in Poland? | dev | remote_work/PL/None | 10 | 83 green | OK |
| HR policy | working hours Italy | hr | working_hours/IT/None | 10 | 92 green | OK |
| HR policy | expense policy Germany | hr | expense_policy/DE/None | 10 | 24 red | OK |
| HR policy | How many leave days can I carry over in Sweden? | hr | leave_carryover/SE/None | 10 | 96 green | OK |
| HR policy | training budget in Belgium | hr | training_budget/BE/None | 10 | 81 green | OK |
| HR policy | sick leave | pay | sick_leave/NL/None | 10 | 84 green | OK |
| Other languages | Ouderschapsverlof in België | hr | parental_leave/BE/None | 10 | 84 green | OK |
| Other languages | Wat is de pensioenleeftijd in Nederland? | pay | pension/NL/None | 10 | 90 green | OK |
| Other languages | bedrijfswagen België | hr | company_car/BE/None | 10 | 92 green | OK |
| Other languages | ziekteverlof Nederland | pay | sick_leave/NL/None | 10 | 84 green | OK |
| Other languages | congé parental en Belgique | hr | parental_leave/BE/None | 10 | 84 green | OK |
| Other languages | télétravail en France | hr | remote_work/FR/None | 10 | 89 green | OK |
| Other languages | jubilación en España | es | pension/ES/None | 10 | 85 green | OK |
| Other languages | onkosten Nederland | pay | expense_policy/NL/None | 10 | 94 green | OK |
| Other languages | telewerk regels | hr | remote_work/BE/None | 10 | 87 green | OK |
| Payroll | payroll cut-off Belgium | hr | payroll_cutoff/BE/None | 10 | 93 green | OK |
| Payroll | What is the payslip format in Spain? | es | payslip_format/ES/None | 10 | 92 green | OK |
| Payroll | tax withholding rate Denmark | pay | tax_withholding/DK/None | 10 | 94 green | OK |
| Payroll | social security filing deadline France | pay | social_security/FR/None | 10 | 90 green | OK |
| Payroll | year-end closing Netherlands | pay | year_end_closing/NL/None | 10 | 88 green | OK |
| Payroll | How do I correct a payroll error in Germany? | pay | correction_process/DE/None | 10 | 92 green | OK |
| Payroll | When are bonuses paid in Belgium? | hr | bonus_payment/BE/None | 10 | 29 red | OK |
| Legal | GDPR retention period | hr | gdpr_retention/BE/None | 10 | 93 green | OK |
| Legal | How long do we keep personnel files in Poland? | dev | gdpr_retention/PL/None | 10 | 78 green | OK |
| Legal | works council notice period Germany | hr | works_council/DE/None | 10 | 97 green | OK |
| Legal | data processing agreement template | hr | dpa_template/BE/None | 10 | 86 green | OK |
| Legal | whistleblower procedure UK | hr | whistleblower/GB/None | 10 | 87 green | OK |
| Access | salary bands Belgium | hr | salary_bands/BE/None | 10 | 90 green | OK |
| Access | salary bands Belgium | dev | salary_bands/BE/None | 0 | - | OK |
| Access | salary bands in Poland | pay | salary_bands/PL/None | 0 | - | OK |
| Access | employment contract template Spain | hr | employment_contract/ES/None | 10 | 33 red | OK |
| Access | employment contract template Spain | es | employment_contract/ES/None | 0 | - | OK |
| Business | expat payroll Belgium | es | expat_payroll/BE/None | 10 | 91 green | OK |
| Business | shadow payroll reporting | es | shadow_payroll/ES/None | 10 | 84 green | OK |
| Business | cross-border tax threshold | es | cross_border_tax/ES/None | 10 | 89 green | OK |
| Business | posted workers rules | es | posting_rules/ES/None | 10 | 94 green | OK |
| Business | SMB onboarding | es | smb_onboarding/ES/None | 10 | 93 green | OK |
| Business | SMB support response time | es | smb_support/ES/None | 10 | 94 green | OK |
| Business | pricing sheet Spain | es | pricing_sheet/ES/None | 10 | 51 yellow | OK |
| Business | sales playbook | es | sales_playbook/ES/None | 10 | 91 green | OK |
| Business | client onboarding kick-off | es | client_onboarding/ES/None | 10 | 90 green | OK |
| Business | Who do I escalate to? | es | escalation_path/ES/None | 10 | 88 green | OK |
| Business | campaign playbook approval time | es | campaign_playbook/ES/None | 10 | 90 green | OK |
| Business | brand guidelines | es | brand_guidelines/ES/None | 10 | 91 green | OK |
| Engineering | build pipeline timeout | dev | build_pipeline/None/None | 10 | 93 green | OK |
| Engineering | How do I deploy to production? | dev | deployment_process/None/None | 10 | 94 green | OK |
| Engineering | incident response on-call | dev | incident_response/None/None | 10 | 94 green | OK |
| Engineering | API guidelines | dev | api_guidelines/None/None | 10 | 96 green | OK |
| Engineering | code review rules | dev | code_review/None/None | 10 | 95 green | OK |
| Engineering | release calendar | dev | release_calendar/None/None | 10 | 91 green | OK |
| Engineering | database migration freeze | dev | db_migration/None/None | 10 | 92 green | OK |
| Engineering | access requests | dev | access_requests/None/None | 10 | 97 green | OK |
| Customers | What do we know about Nike? | es | None/None/C01 | 10 | 93 green | OK |
| Customers | payroll cut-off for Nike in Belgium | es | payroll_cutoff/BE/C01 | 10 | 92 green | OK |
| Customers | Nike SLA | es | client_sla/None/C01 | 10 | 92 green | OK |
| Customers | Who is the contact at Decathlon? | lead | client_contacts/None/C02 | 10 | 97 green | OK |
| Customers | Zalando escalation agreement | lead | client_escalation/None/C03 | 9 | 96 green | OK |
| Customers | IKEA payroll cut-off | lead | payroll_cutoff/None/C07 | 10 | 92 green | OK |
| Customers | What do we know about Nike? | dev | None/None/C01 | 0 | - | OK |
| Who knows | Who knows the most about Nike? | es | None/None/C01 | 10 | 93 green | OK |
| Who knows | Who can I ask about parental leave in Belgium? | hr | parental_leave/BE/None | 10 | 84 green | OK |
| Who knows | Who knows how the build pipeline works? | dev | build_pipeline/None/None | 10 | 93 green | OK |
| Who knows | wie kent Nike? | es | None/None/C01 | 10 | 93 green | OK |
| Edge cases | (empty) | hr | None/None/None | 0 | - | OK |
| Edge cases | asdfghjkl qwerty | hr | None/None/None | 0 | - | OK |
| Edge cases | parental leave in Atlantis | hr | parental_leave/BE/None | 10 | 84 green | OK |
| Edge cases | '; DROP TABLE documents; -- | hr | None/None/None | 0 | - | OK |
| Edge cases | <script>alert(1)</script> parental leave Belgium | hr | parental_leave/BE/None | 10 | 84 green | OK |
| Edge cases | PARENTAL LEAVE BELGIUM!!! | hr | parental_leave/BE/None | 10 | 84 green | OK |
| Edge cases | payroll | pay | correction_process/NL/None | 10 | 99 green | OK |
| Edge cases | parental leave BE | hr | parental_leave/BE/None | 10 | 84 green | OK |
