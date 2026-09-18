terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

# Every AWS call is redirected at the local emulator. The `endpoints` block is
# the only thing separating this from a real AWS deploy -- remove it (and the
# static credentials) and the same configuration targets a real account.
provider "aws" {
  region     = var.region
  access_key = "test"
  secret_key = "test"

  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_region_validation      = true
  skip_requesting_account_id  = true

  endpoints {
    lambda         = var.endpoint_url
    iam            = var.endpoint_url
    sts            = var.endpoint_url
    s3             = var.endpoint_url
    secretsmanager = var.endpoint_url
    events         = var.endpoint_url
    logs           = var.endpoint_url
    cloudwatch     = var.endpoint_url
    ce             = var.endpoint_url
    cloudtrail     = var.endpoint_url
  }
}
