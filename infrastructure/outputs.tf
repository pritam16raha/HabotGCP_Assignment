# Author: Pritam Raha <rahapritam32@gmail.com>
output "raw_landing_bucket" {
  description = "Name of the private D0 raw landing bucket."
  value       = module.secure_data_landing.raw_landing_bucket
}

output "raw_upload_prefix" {
  description = "Only object prefix to which the ingestion identity can write."
  value       = module.secure_data_landing.raw_upload_prefix
}

output "staged_table" {
  description = "Fully qualified D1 enforced BigQuery table identifier."
  value       = module.secure_data_landing.staged_table
}

output "validated_topic" {
  description = "Pub/Sub topic accepting only schema-valid canonical onboarding events."
  value       = module.secure_data_landing.validated_topic
}

output "raw_ingestor_service_account" {
  description = "Service account that can only create new raw objects under the incoming prefix."
  value       = module.secure_data_landing.raw_ingestor_service_account
}

output "data_pipeline_service_account" {
  description = "Service account with validation-pipeline access to raw objects and staged data."
  value       = module.secure_data_landing.data_pipeline_service_account
}

output "analytics_reader_service_account" {
  description = "Demonstration analytics identity restricted to Dubai rows by BigQuery row-level security."
  value       = module.secure_data_landing.analytics_reader_service_account
}
