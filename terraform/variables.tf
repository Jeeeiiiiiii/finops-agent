variable "region" {
  type    = string
  default = "us-east-1"
}

variable "endpoint_url" {
  description = "Floci endpoint as seen from this machine. Everything in providers.tf points here."
  type        = string
  default     = "http://localhost:4566"
}

variable "internal_endpoint_url" {
  description = "Floci endpoint as seen from inside the Lambda container (by Docker service name). Set to null against a real account."
  type        = string
  default     = "http://floci:4566"
}

variable "name" {
  type    = string
  default = "finops-agent"
}

variable "package_path" {
  description = "The Lambda zip that scripts/package.sh builds."
  type        = string
  default     = "../agent/finops-agent.zip"
}

variable "daily_schedule" {
  description = "When the daily investigation runs. Cost Explorer data for a day is complete a few hours after midnight UTC."
  type        = string
  default     = "cron(0 16 * * ? *)"
}

variable "digest_schedule" {
  description = "When the weekly digest goes out."
  type        = string
  default     = "cron(0 8 ? * MON *)"
}

variable "slack_webhook_url" {
  description = "Slack incoming webhook. Stored in Secrets Manager, read by the function at start. Empty = notify to the log instead."
  type        = string
  sensitive   = true
  default     = ""
}

variable "anthropic_api_key" {
  description = "Claude API key for the explainer. Stored in Secrets Manager. Empty = rule-based explanations only."
  type        = string
  sensitive   = true
  default     = ""
}

variable "model_provider" {
  description = "anthropic (API key from Secrets Manager) or bedrock (IAM; adds bedrock:InvokeModel to the role)."
  type        = string
  default     = "anthropic"
}

variable "cost_source" {
  description = "ce = Cost Explorer; fixture = a bundled scenario (for demos, and for the emulator where spend is tiny)."
  type        = string
  default     = "ce"
}

variable "thresholds" {
  description = "Detection thresholds. Configuration, not prompt text."
  type = object({
    ratio                 = number
    min_delta_usd         = number
    new_service_floor_usd = number
  })
  default = {
    ratio                 = 0.25
    min_delta_usd         = 1.0
    new_service_floor_usd = 1.0
  }
}
