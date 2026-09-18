#!/usr/bin/env bash
# Prove each piece, in order. Assumes: terraform applied, slack-catcher running.
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1

AWS="docker run --rm --network floci_default -e AWS_ACCESS_KEY_ID=test -e AWS_SECRET_ACCESS_KEY=test -e AWS_DEFAULT_REGION=us-east-1 amazon/aws-cli --endpoint-url=http://floci:4566"
FN=$(terraform -chdir=terraform output -raw function_name)
BUCKET=$(terraform -chdir=terraform output -raw findings_bucket)
LOGS=$(terraform -chdir=terraform output -raw log_group)
TODAY=$(date -u +%F)
# The agent investigates the last complete day (yesterday) unless told otherwise.
DAY=$(python -c "import datetime as d; print((d.datetime.now(d.timezone.utc).date()-d.timedelta(days=1)).isoformat())")

hr() { echo; echo "── $1"; echo; }

invoke() {  # invoke <payload-json>  -> prints the function's summary
  # The CLI runs in a container, so the response file must be its stdout, not a host path.
  $AWS lambda invoke --function-name "$FN" --cli-binary-format raw-in-base64-out --payload "$1"     --query 'StatusCode' --output text /dev/stdout 2>/dev/null | python scripts/summary.py
}

# A clean catcher log per run, so "what Slack received" is this run only.
docker restart finops-slack-catcher >/dev/null 2>&1 || true

hr "0. Where things stand"
echo "    function  $FN"
echo "    bucket    $BUCKET"
echo "    schedules:"
$AWS events list-rules --name-prefix "$FN" --query 'Rules[].[Name,ScheduleExpression]' --output text | sed 's/^/      /'

hr "1. A quiet day: nothing to say, nothing sent"
invoke '{"mode":"daily","cost_source":"fixture","scenario":"quiet"}'

hr "2. A NAT gateway spike: detected, correlated with the route change, archived, posted"
invoke '{"mode":"daily","cost_source":"fixture","scenario":"spike-nat"}'
echo "    the finding in S3:"
$AWS s3 ls "s3://$BUCKET/findings/$DAY/" | sed 's/^/      /'
echo "    what Slack received (from the catcher):"
sleep 1
docker logs finops-slack-catcher 2>/dev/null | tail -n 12 | sed 's/^/      /'

hr "3. The same spike the next day: archived again but suppressed (dedupe), nothing sent"
invoke "{\"mode\":\"daily\",\"cost_source\":\"fixture\",\"scenario\":\"spike-nat\",\"day\":\"$TODAY\"}"
echo "    (the fixture is anchored to the investigated day, so the next day sees the same spike; the archive remembers the delivered alert)"

hr "4. A service that did not exist yesterday"
invoke '{"mode":"daily","cost_source":"fixture","scenario":"new-service"}'

hr "5. Usage-driven: no change in the trail, and the agent says so"
invoke '{"mode":"daily","cost_source":"fixture","scenario":"usage-spike"}'

hr "6. The real cost source: Cost Explorer on the emulator (metered from the other labs)"
invoke '{"mode":"daily","cost_source":"ce","change_source":"cloudtrail"}'
echo "    (yesterday, the last complete day; tiny numbers, below the \$1 floor -> no anomaly. That floor is the point.)"

hr "7. Weekly digest from the archive"
invoke '{"mode":"digest"}'

hr "8. The function's own log: one JSON line per step"
$AWS logs filter-log-events --log-group-name "$LOGS" --filter-pattern '"finding archived"' \
  --query 'events[-3:].message' --output text | sed 's/^/      /'

echo
echo "Console: http://localhost:4500 (Lambda, S3 $BUCKET, Secrets Manager, EventBridge rules)"
