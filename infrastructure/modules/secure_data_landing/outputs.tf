# Author: Pritam Raha <rahapritam32@gmail.com>
output "raw_landing_bucket" {
  value = google_storage_bucket.raw_landing.name
}

output "raw_upload_prefix" {
  value = "gs://${google_storage_bucket.raw_landing.name}/${local.incoming_prefix}"
}

output "staged_table" {
  value = "${var.project_id}.${google_bigquery_dataset.staged.dataset_id}.${google_bigquery_table.onboarding.table_id}"
}

output "validated_topic" {
  value = google_pubsub_topic.validated.id
}

output "raw_ingestor_service_account" {
  value = google_service_account.raw_ingestor.email
}

output "data_pipeline_service_account" {
  value = google_service_account.data_pipeline.email
}

output "analytics_reader_service_account" {
  value = google_service_account.analytics_reader.email
}

output "security_controls" {
  value = {
    bucket_public_access_prevention = google_storage_bucket.raw_landing.public_access_prevention
    bucket_uniform_access           = google_storage_bucket.raw_landing.uniform_bucket_level_access
    bucket_versioning               = google_storage_bucket.raw_landing.versioning[0].enabled
    table_deletion_protection       = google_bigquery_table.onboarding.deletion_protection
    region                          = var.region
  }
}
