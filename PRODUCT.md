# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS in one file (`ops/index.html`), served by a standard-library Python server (`ops/server.py`) on the operator's machine, started by `scripts/ops.sh`. It invokes the deployed Lambda on the Floci emulator and reads S3, CloudWatch Logs, EventBridge and the Slack stand-in container. No build step, nothing new deployed. Chosen by the user, matching the rag-lab and order-lab pages.

## Users

One DevOps engineer, the lab's owner, learning how a scheduled cost agent works, on their own Windows laptop with the lab running locally. They know AWS billing and alerting from work; they want to *see* the run step by step (costs, the arithmetic, the evidence, the explanation, what gets sent and why) rather than read JSON from `aws lambda invoke`. They prefer plain-language explanations and cause → effect they can trigger themselves.

## Product Purpose

The page lets them put each of the five cost stories in front of the real agent and watch what it does with it: a quiet day (nothing sent), a NAT gateway spike (detected, correlated with route changes, explained, archived, posted), a service that did not exist yesterday, a usage spike with no change behind it (the agent says so instead of inventing a cause), and several at once (biggest first, capped). Success: they can explain, from what they watched, the two thresholds that must both trip (+25% over the 7-day median AND +$1), why the median and not the mean, why the arithmetic is scripted and only the meaning is explained, why the rules floor exists, why a quiet day sends nothing, and why every finding is archived before anything is sent.

Scenario scope (confirmed by the user): the five fixtures (quiet, spike-nat, new-service, usage-spike, multi). Out of scope for now: forcing the Slack stand-in down, the live Cost Explorer source, the weekly digest.

## Positioning

Every result comes from the deployed function: the page invokes `finops-agent` on the emulator with `{"mode":"daily","cost_source":"fixture","scenario":...}`, then reads the findings it archived in S3, the message the Slack stand-in received, and the function's own JSON log lines. The fixtures are the *input* (a spike cannot be waited for); everything after the input is the real agent's work.

## Operating Context

- Started after the lab is up: Floci (`floci-ui`, `docker compose up -d`), the Slack stand-in (`scripts/slack-catcher.sh`), and `terraform apply`.
- The explainer is the rules floor locally (no `ANTHROPIC_API_KEY`); `explained_by` says which path wrote the words, and the page must say so.
- Runs write to the real archive, so dedupe is real: the same spike again within 3 days of a delivered alert is archived and suppressed. The page must make that legible, not look like a failure.
- The investigated day is yesterday (UTC) unless a run overrides it.

## Capabilities and Constraints

- Lambda summary: `services_seen`, `account_total_usd`, findings (`service`, `kind`, `delta_usd`, `explained_by`, `confidence`, `suppressed`), `notified`, `notes`, `explainer`, `notifier`.
- Archived finding (S3 `findings/<day>/<service>.json`): the anomaly (today, baseline median, delta, ratio, kind), the 14-day series, the audit-trail changes (time, event, source, actor, resources), the explanation (cause, confidence, recommendation, explained_by), suppressed + reason, sent.
- Terminology: anomaly, baseline (7-day median), floor ($1), ratio (+25%), evidence, change, explanation, rules floor, suppressed, dedupe window, archive, digest.
- Thresholds are configuration (`Thresholds`, Terraform `var.thresholds`).

## Evidence on Hand

The five fixture scenarios in `agent/finops_agent/fixtures/`, the deployed function and bucket, and the README's account of each demo step. No live Claude explanations exist; the page must not show any.

## Product Principles

1. Show the arithmetic: every alert shows the series, the median, and both thresholds it crossed.
2. Silence is a result: a quiet day is shown as a decision, not an empty state.
3. Evidence before explanation: the changes and the numbers sit beside the words that interpret them.
4. Say who wrote the words: rules or a model, every time.
