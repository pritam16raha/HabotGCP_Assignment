# Author: Pritam Raha <rahapritam32@gmail.com>
variable "project_id" {
  description = "Existing Google Cloud project identifier. Supply it through TF_VAR_project_id."
  type        = string
  nullable    = false

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid 6 to 30 character Google Cloud project identifier."
  }
}

variable "region" {
  description = "Single region shared by Cloud Storage, BigQuery, and Cloud Key Management Service."
  type        = string
  default     = "me-central1"
  nullable    = false

  validation {
    condition     = contains(["me-central1", "me-central2"], var.region)
    error_message = "region must be me-central1 (Doha) or me-central2 (Dammam)."
  }
}

variable "environment" {
  description = "Deployment environment label. This assignment provisions staging only."
  type        = string
  default     = "staging"
  nullable    = false

  validation {
    condition     = var.environment == "staging"
    error_message = "environment must remain staging for this blueprint."
  }
}

variable "raw_retention_seconds" {
  description = "Minimum period for retaining raw onboarding objects before deletion is permitted."
  type        = number
  default     = 604800
  nullable    = false

  validation {
    condition     = var.raw_retention_seconds >= 604800 && var.raw_retention_seconds <= 2592000
    error_message = "raw_retention_seconds must be between 7 and 30 days."
  }
}

