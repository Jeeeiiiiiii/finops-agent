# ---------------------------------------------------------------------------
# The safety model, in one policy: the agent can read costs and the audit
# trail, write its own findings, read its two secrets, and log. There is no
# statement here that can create, modify or delete infrastructure, so
# nothing the model reads -- a resource tag, a CloudTrail event name -- can
# become an action.
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "agent" {
  name               = "${var.name}-role"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "agent" {
  statement {
    sid       = "ReadCosts"
    actions   = ["ce:GetCostAndUsage", "ce:GetDimensionValues"]
    resources = ["*"] # Cost Explorer has no resource-level scope
  }

  statement {
    sid       = "ReadAuditTrail"
    actions   = ["cloudtrail:LookupEvents"]
    resources = ["*"] # LookupEvents has no resource-level scope
  }

  statement {
    sid       = "WriteFindings"
    actions   = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.findings.arn, "${aws_s3_bucket.findings.arn}/*"]
  }

  statement {
    sid     = "ReadOwnSecrets"
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.slack.arn,
      aws_secretsmanager_secret.anthropic.arn,
    ]
  }

  statement {
    sid       = "Log"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.agent.arn}:*"]
  }

  dynamic "statement" {
    for_each = var.model_provider == "bedrock" ? [1] : []
    content {
      sid       = "InvokeModel"
      actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
      resources = ["arn:aws:bedrock:*::foundation-model/anthropic.*"]
    }
  }
}

resource "aws_iam_role_policy" "agent" {
  name   = "${var.name}-policy"
  role   = aws_iam_role.agent.id
  policy = data.aws_iam_policy_document.agent.json
}
