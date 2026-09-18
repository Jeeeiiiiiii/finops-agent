# ---------------------------------------------------------------------------
# The two things the function must never carry in its environment or its
# package: where to post, and the model key. Both live in Secrets Manager;
# the function reads them at start with a role that can read these two ARNs
# and nothing else. Leave a variable empty and the secret exists with no
# value -- the function logs "secret unavailable" and degrades (log instead
# of Slack, rules instead of Claude).
# ---------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "slack" {
  name                    = "${var.name}/slack-webhook-url"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "slack" {
  count         = var.slack_webhook_url == "" ? 0 : 1
  secret_id     = aws_secretsmanager_secret.slack.id
  secret_string = var.slack_webhook_url
}

resource "aws_secretsmanager_secret" "anthropic" {
  name                    = "${var.name}/anthropic-api-key"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "anthropic" {
  count         = var.anthropic_api_key == "" ? 0 : 1
  secret_id     = aws_secretsmanager_secret.anthropic.id
  secret_string = var.anthropic_api_key
}
