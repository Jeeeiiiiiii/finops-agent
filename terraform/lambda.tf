# ---------------------------------------------------------------------------
# The agent. One function, two schedules (daily investigation, weekly digest).
# scripts/package.sh builds the zip: the package plus the anthropic SDK; boto3
# comes with the runtime.
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "agent" {
  function_name = var.name
  role          = aws_iam_role.agent.arn

  runtime     = "python3.12"
  handler     = "finops_agent.handler.handler"
  timeout     = 120 # a Claude investigation with follow-ups can take a minute
  memory_size = 512

  filename         = var.package_path
  source_code_hash = filebase64sha256(var.package_path)

  environment {
    variables = {
      FINOPS_BUCKET                = aws_s3_bucket.findings.bucket
      FINOPS_COST_SOURCE           = var.cost_source
      FINOPS_CHANGE_SOURCE         = var.cost_source == "ce" ? "cloudtrail" : "fixture"
      FINOPS_EXPLAINER             = "auto"
      FINOPS_MODEL_PROVIDER        = var.model_provider
      FINOPS_NOTIFIER              = "auto"
      FINOPS_SLACK_SECRET_ID       = aws_secretsmanager_secret.slack.name
      FINOPS_ANTHROPIC_SECRET_ID   = aws_secretsmanager_secret.anthropic.name
      FINOPS_RATIO                 = tostring(var.thresholds.ratio)
      FINOPS_MIN_DELTA_USD         = tostring(var.thresholds.min_delta_usd)
      FINOPS_NEW_SERVICE_FLOOR_USD = tostring(var.thresholds.new_service_floor_usd)
      # The function runs in its own container and reaches the emulator by
      # service name. Empty against a real account.
      FINOPS_ENDPOINT = var.internal_endpoint_url == null ? "" : var.internal_endpoint_url
    }
  }

  depends_on = [aws_cloudwatch_log_group.agent, aws_iam_role_policy.agent]
}

# ---------------------------------------------------------------------------
# Two EventBridge rules, one function. The payload selects the mode; the same
# function can also be invoked by hand with a scenario (scripts/demo.sh).
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "daily" {
  name                = "${var.name}-daily"
  description         = "Daily cost anomaly investigation"
  schedule_expression = var.daily_schedule
}

resource "aws_cloudwatch_event_target" "daily" {
  rule  = aws_cloudwatch_event_rule.daily.name
  arn   = aws_lambda_function.agent.arn
  input = jsonencode({ mode = "daily" })
}

resource "aws_lambda_permission" "daily" {
  statement_id  = "AllowDailyRule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.agent.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily.arn
}

resource "aws_cloudwatch_event_rule" "digest" {
  name                = "${var.name}-digest"
  description         = "Weekly FinOps digest"
  schedule_expression = var.digest_schedule
}

resource "aws_cloudwatch_event_target" "digest" {
  rule  = aws_cloudwatch_event_rule.digest.name
  arn   = aws_lambda_function.agent.arn
  input = jsonencode({ mode = "digest" })
}

resource "aws_lambda_permission" "digest" {
  statement_id  = "AllowDigestRule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.agent.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.digest.arn
}
