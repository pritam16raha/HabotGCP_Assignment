# Author: Pritam Raha <rahapritam32@gmail.com>
variable "project_id" {
  type        = string
  description = "Google Cloud project identifier."
}

variable "project_number" {
  type        = string
  description = "Google Cloud project number."
}

variable "region" {
  type        = string
  description = "Region for all stored data and encryption keys."
}

variable "environment" {
  type        = string
  description = "Deployment environment."
}

variable "labels" {
  type        = map(string)
  description = "Labels applied consistently to supported resources."
}

variable "raw_retention_seconds" {
  type        = number
  description = "Minimum raw-object retention in seconds."
}

variable "storage_service_account_email" {
  type        = string
  description = "Google-managed Cloud Storage service account email."
}

variable "bigquery_service_account_email" {
  type        = string
  description = "Google-managed BigQuery service account email."
}

variable "pubsub_service_account_email" {
  type        = string
  description = "Google-managed Pub/Sub service account email."
}

variable "bigquery_schema_json" {
  type        = string
  description = "Validated BigQuery schema JSON from the shared contract."
}

variable "pubsub_schema_definition" {
  type        = string
  description = "Validated Avro definition from the shared Pub/Sub contract."
}

