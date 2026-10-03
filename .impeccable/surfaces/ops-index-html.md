---
version: 1
slug: "ops-index-html"
primary_target: "ops/index.html"
related_targets: ["ops/server.py"]
---

Scope: ops/index.html, the finops-agent ship's log. Mode: Operate.
Audience: the lab's owner, a DevOps engineer learning how a scheduled cost agent works; job: put each of the five cost stories in front of the deployed agent and watch the arithmetic, the evidence, the explanation, the archive and what was (or was not) sent.

## Direction contract

THESIS: The account is a ship and every AWS service is an engine; each day's cost is that engine's fuel burn, entered in an engine-room log. A deviation is an entry ringed in red; orders from the bridge (audit-trail write calls) are logged beside it; the officer's remark explains; a radio message goes to the owners only when something is wrong. Refuses the category default of a cost dashboard with line charts and an alerts table.

OWN-WORLD: Ruled logbook pages (pale green-grey stock, blue horizontal rules, red vertical margin rules) inside a dark cloth binding; iron-gall black ink entries in a ledger hand; red ink reserved for the deviation ring and threshold lines; a pink radio-message form for Slack; the archive as a shelf of dated log sheets.

STORY: Pick a voyage day (scenario); the agent runs; see the 14-day log of burn per engine with the median and both threshold lines drawn on the deviating engine; the bridge orders that explain it; the remark and who wrote it; the radio message as received, or "nothing to report" on a quiet day; repeats noted as already reported.

FIRST VIEWPORT: Binding header with ship status (function, schedule, bucket, explainer); a row of five voyage-day tabs (the scenarios) with a Run control; below, the open log page: day rows x engine columns with the investigated day at the bottom, the deviation ringed; right margin holds the remark and the radio form.

FORM: Ship's Logbook, 7 of 7 on the ordered list. Seed key f5f3aac1. Raises: wide annotation margin where remarks hang beside the rows they explain (centre-rail reference setting); thresholds drawn as visible construction lines on the series (Crouwel grid); the object under the eye ringed in red (star atlas).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
