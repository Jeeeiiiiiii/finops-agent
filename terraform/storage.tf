# ---------------------------------------------------------------------------
# Where findings go, alerted or not. Versioned so a re-run of the same day
# keeps both records; encrypted at rest; nothing public.
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "findings" {
  bucket        = "${var.name}-findings"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "findings" {
  bucket = aws_s3_bucket.findings.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "findings" {
  bucket = aws_s3_bucket.findings.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "findings" {
  bucket                  = aws_s3_bucket.findings.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudwatch_log_group" "agent" {
  name              = "/aws/lambda/${var.name}"
  retention_in_days = 30
}
