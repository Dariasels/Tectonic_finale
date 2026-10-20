"""Mock questions per category with what the system is expected to understand and do.

Persona keys: es = sales Spain (works with Nike), hr = HR advisor Belgium, dev = developer Poland,
pay = payroll Netherlands, lead = country lead Belgium.
expect keys: topic, country ("user" = the persona's own country), client, results (min count, 0 = must be empty),
banner (conflict banner expected), experts (expert list expected), ask_expert (nothing trustworthy).
"""

# (category, question, persona, expect)
CURATED = [
    # --- HR policies, English
    ("HR policy", "How much parental leave do I get in Belgium?", "hr", {"topic": "parental_leave", "country": "BE", "banner": True, "results": 3}),
    ("HR policy", "parental leave Netherlands", "pay", {"topic": "parental_leave", "country": "NL", "results": 1}),
    ("HR policy", "What is the retirement age in Belgium?", "hr", {"topic": "pension", "country": "BE", "ask_expert": True, "experts": True}),
    ("HR policy", "What is the retirement age in Germany?", "hr", {"topic": "pension", "country": "DE", "results": 1}),
    ("HR policy", "company car policy in France", "hr", {"topic": "company_car", "country": "FR", "results": 1}),
    ("HR policy", "sick leave rules Spain", "es", {"topic": "sick_leave", "country": "ES", "results": 1}),
    ("HR policy", "How many remote days can I work in Poland?", "dev", {"topic": "remote_work", "country": "PL", "results": 1}),
    ("HR policy", "working hours Italy", "hr", {"topic": "working_hours", "country": "IT", "results": 1}),
    ("HR policy", "expense policy Germany", "hr", {"topic": "expense_policy", "country": "DE", "results": 1}),
    ("HR policy", "How many leave days can I carry over in Sweden?", "hr", {"topic": "leave_carryover", "country": "SE", "results": 1}),
    ("HR policy", "training budget in Belgium", "hr", {"topic": "training_budget", "country": "BE", "results": 1}),
    ("HR policy", "sick leave", "pay", {"topic": "sick_leave", "country": "user", "results": 1}),
    # --- Dutch, French, Spanish
    ("Other languages", "Ouderschapsverlof in België", "hr", {"topic": "parental_leave", "country": "BE", "results": 3}),
    ("Other languages", "Wat is de pensioenleeftijd in Nederland?", "pay", {"topic": "pension", "country": "NL", "results": 1}),
    ("Other languages", "bedrijfswagen België", "hr", {"topic": "company_car", "country": "BE", "results": 1}),
    ("Other languages", "ziekteverlof Nederland", "pay", {"topic": "sick_leave", "country": "NL", "results": 1}),
    ("Other languages", "congé parental en Belgique", "hr", {"topic": "parental_leave", "country": "BE", "results": 1}),
    ("Other languages", "télétravail en France", "hr", {"topic": "remote_work", "country": "FR", "results": 1}),
    ("Other languages", "jubilación en España", "es", {"topic": "pension", "country": "ES", "results": 1}),
    ("Other languages", "onkosten Nederland", "pay", {"topic": "expense_policy", "country": "NL", "results": 1}),
    ("Other languages", "telewerk regels", "hr", {"topic": "remote_work", "country": "user", "results": 1}),
    # --- Payroll
    ("Payroll", "payroll cut-off Belgium", "hr", {"topic": "payroll_cutoff", "country": "BE", "results": 1}),
    ("Payroll", "What is the payslip format in Spain?", "es", {"topic": "payslip_format", "country": "ES", "results": 1}),
    ("Payroll", "tax withholding rate Denmark", "pay", {"topic": "tax_withholding", "country": "DK", "results": 1}),
    ("Payroll", "social security filing deadline France", "pay", {"topic": "social_security", "country": "FR", "results": 1}),
    ("Payroll", "year-end closing Netherlands", "pay", {"topic": "year_end_closing", "country": "NL", "results": 1}),
    ("Payroll", "How do I correct a payroll error in Germany?", "pay", {"topic": "correction_process", "country": "DE", "results": 1}),
    ("Payroll", "When are bonuses paid in Belgium?", "hr", {"topic": "bonus_payment", "country": "BE", "results": 1}),
    # --- Legal and compliance
    ("Legal", "GDPR retention period", "hr", {"topic": "gdpr_retention", "country": "user", "results": 1}),
    ("Legal", "How long do we keep personnel files in Poland?", "dev", {"topic": "gdpr_retention", "country": "PL", "results": 1}),
    ("Legal", "works council notice period Germany", "hr", {"topic": "works_council", "country": "DE", "results": 1}),
    ("Legal", "data processing agreement template", "hr", {"topic": "dpa_template", "country": "user", "results": 1}),
    ("Legal", "whistleblower procedure UK", "hr", {"topic": "whistleblower", "country": "GB", "results": 1}),
    # --- Access control (HR-only documents)
    ("Access", "salary bands Belgium", "hr", {"topic": "salary_bands", "country": "BE", "results": 1}),
    ("Access", "salary bands Belgium", "dev", {"topic": "salary_bands", "country": "BE", "results": 0}),
    ("Access", "salary bands in Poland", "pay", {"topic": "salary_bands", "country": "PL", "results": 0}),
    ("Access", "employment contract template Spain", "hr", {"topic": "employment_contract", "country": "ES", "results": 1}),
    ("Access", "employment contract template Spain", "es", {"topic": "employment_contract", "country": "ES", "results": 0}),
    # --- Internationals, SMB, sales, customer success, marketing
    ("Business", "expat payroll Belgium", "es", {"topic": "expat_payroll", "country": "BE", "results": 1}),
    ("Business", "shadow payroll reporting", "es", {"topic": "shadow_payroll", "country": "user", "results": 1}),
    ("Business", "cross-border tax threshold", "es", {"topic": "cross_border_tax", "country": "user", "results": 1}),
    ("Business", "posted workers rules", "es", {"topic": "posting_rules", "country": "user", "results": 1}),
    ("Business", "SMB onboarding", "es", {"topic": "smb_onboarding", "country": "user", "results": 1}),
    ("Business", "SMB support response time", "es", {"topic": "smb_support", "country": "user", "results": 1}),
    ("Business", "pricing sheet Spain", "es", {"topic": "pricing_sheet", "country": "ES", "results": 1}),
    ("Business", "sales playbook", "es", {"topic": "sales_playbook", "country": "user", "results": 1}),
    ("Business", "client onboarding kick-off", "es", {"topic": "client_onboarding", "country": "user", "results": 1}),
    ("Business", "Who do I escalate to?", "es", {"topic": "escalation_path", "country": "user", "results": 1}),
    ("Business", "campaign playbook approval time", "es", {"topic": "campaign_playbook", "country": "user", "results": 1}),
    ("Business", "brand guidelines", "es", {"topic": "brand_guidelines", "country": "user", "results": 1}),
    # --- Engineering
    ("Engineering", "build pipeline timeout", "dev", {"topic": "build_pipeline", "results": 1}),
    ("Engineering", "How do I deploy to production?", "dev", {"topic": "deployment_process", "results": 1}),
    ("Engineering", "incident response on-call", "dev", {"topic": "incident_response", "results": 1}),
    ("Engineering", "API guidelines", "dev", {"topic": "api_guidelines", "results": 1}),
    ("Engineering", "code review rules", "dev", {"topic": "code_review", "results": 1}),
    ("Engineering", "release calendar", "dev", {"topic": "release_calendar", "results": 1}),
    ("Engineering", "database migration freeze", "dev", {"topic": "db_migration", "results": 1}),
    ("Engineering", "access requests", "dev", {"topic": "access_requests", "results": 1}),
    # --- Customers
    ("Customers", "What do we know about Nike?", "es", {"client": "C01", "results": 3, "experts": True}),
    ("Customers", "payroll cut-off for Nike in Belgium", "es", {"topic": "payroll_cutoff", "country": "BE", "client": "C01", "banner": True, "results": 2}),
    ("Customers", "Nike SLA", "es", {"topic": "client_sla", "client": "C01", "results": 1}),
    ("Customers", "Who is the contact at Decathlon?", "lead", {"topic": "client_contacts", "client": "C02", "results": 1}),   # country leads may see customer documents
    ("Customers", "Zalando escalation agreement", "lead", {"topic": "client_escalation", "client": "C03", "results": 1}),
    ("Customers", "IKEA payroll cut-off", "lead", {"topic": "payroll_cutoff", "client": "C07", "results": 1}),
    ("Customers", "What do we know about Nike?", "dev", {"client": "C01", "results": 0}),
    # --- Who knows
    ("Who knows", "Who knows the most about Nike?", "es", {"client": "C01", "experts": True}),
    ("Who knows", "Who can I ask about parental leave in Belgium?", "hr", {"topic": "parental_leave", "country": "BE", "experts": True}),
    ("Who knows", "Who knows how the build pipeline works?", "dev", {"topic": "build_pipeline", "experts": True}),
    ("Who knows", "wie kent Nike?", "es", {"client": "C01", "experts": True}),
    # --- Edge cases
    ("Edge cases", "", "hr", {"results": 0}),
    ("Edge cases", "asdfghjkl qwerty", "hr", {"results": 0}),
    ("Edge cases", "parental leave in Atlantis", "hr", {"topic": "parental_leave", "country": "user", "results": 1}),
    ("Edge cases", "'; DROP TABLE documents; --", "hr", {"results": 0}),
    ("Edge cases", "<script>alert(1)</script> parental leave Belgium", "hr", {"topic": "parental_leave", "country": "BE", "results": 1}),
    ("Edge cases", "PARENTAL LEAVE BELGIUM!!!", "hr", {"topic": "parental_leave", "country": "BE", "results": 1}),
    ("Edge cases", "payroll", "pay", {"ambiguous": True}),
    ("Edge cases", "parental leave BE", "hr", {"topic": "parental_leave", "country": "BE", "results": 1}),
]


def persona_ids(engine):
    """Map persona keys to demo user ids."""
    u = {x["label"]: x["person_id"] for x in engine.demo_users()}
    pick = lambda start: next(v for k, v in u.items() if k.startswith(start))
    return {"es": pick("Sales, Spain"), "hr": pick("HR Advisor"), "dev": pick("Back-end"),
            "pay": pick("Payroll"), "lead": pick("Country Lead")}
