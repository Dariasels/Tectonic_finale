# Pitch: Graphlas 2.0 (3 minutes, then 5 minutes of questions)

Rules from the Finals Guide: 3-minute pitch, 5 minutes questions, strict on time, no own device at the jury, pitch as **ppt or pdf** (put the demo video inside).
Slogan: **Find it. Understand it. Trust it. Keep it trusted.** Lead with the problem, then the three pillars: **1 platform integrations, 2 the graph, 3 the trust score**, then one example.
All numbers below come from simulated data (10,000+ people, 26 countries, about 9,600 documents). Say so once, out loud.

## Script (about 430 words, 3:00)

**0:00 Problem (20 s)**
"SD Worx grew from 1,500 to 10,000 people in 26 countries. The knowledge is in Teams, SharePoint, OneDrive, Notion, GitHub and old drives, and in people's heads. People can find a document. The hard question is: can I trust it, and who knows more? And nobody has time to maintain yet another knowledge system."

**0:20 Pillar 1: platform integrations (40 s)**
"Nothing is ever uploaded to Graphlas. A team signs up, picks the tools it already uses, and connects them with a login. From then on tools send events. When someone plans a Teams meeting, we read the title: topic, customer, country. The people who attend get expertise points, if they opted in. A meeting called 'catch-up' is not stored at all. When someone saves a file in a connected tool, we keep the link and the metadata, never the document. Zero extra work for anyone."

**1:00 Pillar 2: the graph (35 s)**
"Everything lands in one graph of the company: country, department, team, people, documents, topics and customers. A question is scoped to the right branch. 'Payroll cut-off for Nike in Belgium' goes to Belgium, to Nike's agreement and the general policy. The same graph answers 'who knows': people are linked to topics by what they wrote, approved, reviewed, attended and did with customers. Colleagues who left are skipped, and team leads who are only listed do not distort the result."

**1:35 Pillar 3: the trust score (45 s)**
"Every document gets a score from 0 to 100 with a colour, and plain-language reasons: how old, who owns it, whether the owner left, who reviewed it, what it contradicts, whether it was replaced. A model learns this from colleague feedback, and the graph adds what simple rules cannot see, like a popular but outdated policy. Why can you trust the score? On our data the top answer is a correct document 92% of the time, against 83% for 'always take the newest' and 42% for 'the most linked'. And 98% of green documents state the current value, against 20% of the red ones. People are only asked when it matters: a conflict with a verified claim, or an unsure prediction. One click, by someone above the author. Nobody approves their own work. And it cleans up after itself: a replaced policy leaves as soon as its successor is verified, and only a very low score goes to the team lead, with the reasons. 'This helped' remembers the right contact for the next person."

**2:20 Example (30 s, video)**
"A salesperson in Spain asks: payroll cut-off for Nike in Belgium. The banner shows two sources disagree: day 15 and day 20. The Nike agreement, verified by a manager, says 15 and wins. The old meeting notes are red: the author left and a newer version replaced them. Right of it: who knows Nike, in other countries too. A new file arrives in SharePoint: 40 milliseconds, not a six-second rebuild, and nobody filled in anything."

**2:50 Close (10 s)**
"Find it. Understand it. Trust it. Keep it trusted. Graphlas: connect the dots, unlock what matters."

## Slides (ppt/pdf, 7 slides)
1. Logo + slogan.
2. The problem (26 countries, 10,000 people, scattered tools) and the five questions we answer.
3. **Pillar 1: platform integrations** (diagram: tools -> events -> link + metadata; meeting title dissected; 'catch-up' dropped).
4. **Pillar 2: the graph** (country > department > team, people, documents, topics, customers; a question scoped to a branch).
5. **Pillar 3: the trust score** (colour, reasons, the validation chart: 92/83/42/59 and 98/46/20).
6. Demo video (embedded, under 60 s) and the keep-it-trusted loop: automatic, human only when needed, retrain weekly or at 100 documents.
7. Assumptions and next steps (see below).

## The five questions of the challenge
| Question | Answer |
|---|---|
| What happens automatically? | Meeting titles read, links and metadata captured, topic found, duplicates dropped, new documents scored in about 40 ms, retraining weekly or at 100 new documents |
| When is a human valuable? | Only conflicts with a verified claim, an unclear topic, or an unsure prediction; one click by someone above the author |
| How is maintenance prevented? | Nobody documents anything; tools send events; signals are opt-in; "this helped" captures know-how as a by-product |
| How does it fit the workflow? | It sits on Teams, SharePoint, OneDrive, Notion, GitHub; no migration |
| Understandable without attention? | Calm UI: a colour and a reason; attention only on a conflict, a low score or an approval |

## Assumptions slide
All documents are in English (questions can use other languages through synonyms). Country > department > team is the standard hierarchy. Not every team has a team lead. Every role exists in every country. Teams adopt templates for new HR documents. Data and colleague feedback are simulated; the validation shows the method works, not real-world accuracy. Tool connections are simulated; real OAuth is the next step. The interview left open: how versions are tracked, whether templates exist, how often documents are made; the sign-in questionnaire collects exactly that.

## Likely questions (and honest answers)
- **Is the data real?** No, simulated, with a hidden ground truth to check the method. Real accuracy needs real feedback.
- **Why not a chatbot / their copilot?** A copilot retrieves and summarises. We sit in front and score and explain what it retrieves.
- **How do you protect privacy?** Metadata and links only; signals are opt-in and can be switched off, which updates scores at once; access rights are enforced on the server; the LLM never sees documents (we use none for scoring).
- **How do you stop a manager from inflating expertise?** Only authored, approved, reviewed and attended count; being listed does not.
- **What if the model is wrong?** Every score has reasons, colleagues can confirm or flag (and change their mind), and low confidence goes to a human.
- **Who can retrain?** Higher management and a system admin.
- **How does it scale?** A new document costs about 40 ms; a full rebuild of 9,600 documents takes about 6 s and runs weekly or at 100 new documents.
- **What about documents in Greek or Spanish?** We assume English for now; the next step is translation of the extracted fact.
- **What is not finished?** Real OAuth and connectors, real feedback, multilingual documents, dark mode check, a production login.
- **Security (Aikido)?** No free-form queries from a language model, validated inputs, server-side access checks, no secrets in the repo; the scan is run before the deadline.

## Demo checklist (video, no own device at the jury)
1. Record the video on the day from the local app (`./dev.sh`), 60 seconds, sound optional. Start with `?nosplash&...` links to skip screens.
2. Live capture and Model & scale are only visible to the system admin, the CEO, country leads and department heads: switch to "System admin" or "CEO" in the menu for those two steps.
3. Click path: Search "payroll cut-off for Nike in Belgium" (as Sales, Spain) -> banner and reasons -> who knows -> "This helped" -> Live capture: a meeting "Nike payroll cut-off review" -> a file saved in SharePoint -> approval (switch to the approver) -> Model & scale: the validation chart.
4. Put the video in the ppt, save a pdf copy, copy both to a USB stick, test on another computer.
5. Run `.venv/bin/python -m pytest tests -q` before the last commit.
