output "function_name" {
  value = aws_lambda_function.agent.function_name
}

output "findings_bucket" {
  value = aws_s3_bucket.findings.bucket
}

output "log_group" {
  value = aws_cloudwatch_log_group.agent.name
}

output "slack_secret_id" {
  value = aws_secretsmanager_secret.slack.name
}
