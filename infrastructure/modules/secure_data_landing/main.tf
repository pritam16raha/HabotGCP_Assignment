# Author: Pritam Raha <rahapritam32@gmail.com>
locals {
  name_prefix       = "habot-onboarding-${var.environment}"
  raw_bucket_name   = "${var.project_id}-d0-raw-${var.environment}"
  dataset_id        = "student_onboarding_d1_${var.environment}"
  table_id          = "student_onboarding_enforced"
  incoming_prefix   = "incoming/"
  quarantine_prefix = "quarantine/"
}

resource "google_service_account" "raw_ingestor" {
  project      = var.project_id
  account_id   = "onboarding-raw-ingestor"
  display_name = "Onboarding raw object creator"
  description  = "Workload identity for creating immutable objects under the D0 incoming prefix."
}

resource "google_service_account" "data_pipeline" {
  project      = var.project_id
  account_id   = "onboarding-data-pipeline"
  display_name = "Onboarding validation pipeline"
  description  = "Workload identity for validation, publication, and D1 maintenance."
}

resource "google_service_account" "analytics_reader" {
  project      = var.project_id
  account_id   = "onboarding-dubai-reader"
  display_name = "Onboarding Dubai analytics reader"
  description  = "Demonstration workload identity filtered to Dubai rows by row-level security."
}

resource "google_kms_key_ring" "data" {
  project  = var.project_id
  name     = "${local.name_prefix}-data"
  location = var.region
}

resource "google_kms_crypto_key" "storage" {
  name            = "d0-raw-storage"
  key_ring        = google_kms_key_ring.data.id
  rotation_period = "7776000s"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_kms_crypto_key" "bigquery" {
  name            = "d1-bigquery"
  key_ring        = google_kms_key_ring.data.id
  rotation_period = "7776000s"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_kms_crypto_key" "pubsub" {
  name            = "validated-events"
  key_ring        = google_kms_key_ring.data.id
  rotation_period = "7776000s"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_kms_crypto_key_iam_member" "storage_service_agent" {
  crypto_key_id = google_kms_crypto_key.storage.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${var.storage_service_account_email}"
}

resource "google_kms_crypto_key_iam_member" "bigquery_service_agent" {
  crypto_key_id = google_kms_crypto_key.bigquery.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${var.bigquery_service_account_email}"
}

resource "google_kms_crypto_key_iam_member" "pubsub_service_agent" {
  crypto_key_id = google_kms_crypto_key.pubsub.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${var.pubsub_service_account_email}"
}

resource "google_storage_bucket" "audit_logs" {
  #checkov:skip=CKV_GCP_62:This is the terminal log destination; recursive access logging creates unbounded logs.
  project                     = var.project_id
  name                        = "${var.project_id}-security-logs-${var.environment}"
  location                    = upper(var.region)
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = var.labels

  encryption {
    default_kms_key_name = google_kms_crypto_key.storage.id
  }

  versioning {
    enabled = true
  }

  retention_policy {
    retention_period = 2592000
    is_locked        = false
  }

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age        = 90
      with_state = "ANY"
    }
  }

  depends_on = [google_kms_crypto_key_iam_member.storage_service_agent]
}

resource "google_storage_bucket_iam_member" "audit_log_writer" {
  bucket = google_storage_bucket.audit_logs.name
  role   = "roles/storage.objectCreator"
  member = "group:cloud-storage-analytics@google.com"
}

resource "google_storage_bucket" "raw_landing" {
  project                     = var.project_id
  name                        = local.raw_bucket_name
  location                    = upper(var.region)
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = var.labels

  encryption {
    default_kms_key_name = google_kms_crypto_key.storage.id
  }

  versioning {
    enabled = true
  }

  retention_policy {
    retention_period = var.raw_retention_seconds
    is_locked        = false
  }

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  logging {
    log_bucket        = google_storage_bucket.audit_logs.name
    log_object_prefix = "d0-raw-access/"
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age                   = 30
      matches_prefix        = [local.quarantine_prefix]
      with_state            = "ANY"
      matches_storage_class = ["STANDARD"]
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      days_since_noncurrent_time = 30
      with_state                 = "ARCHIVED"
    }
  }

  depends_on = [
    google_kms_crypto_key_iam_member.storage_service_agent,
    google_storage_bucket_iam_member.audit_log_writer,
  ]
}

resource "google_storage_bucket_iam_member" "raw_object_creator" {
  bucket = google_storage_bucket.raw_landing.name
  role   = "roles/storage.objectCreator"
  member = google_service_account.raw_ingestor.member

  condition {
    title       = "incoming_objects_only"
    description = "Fail closed: allow creation only below the immutable incoming object prefix."
    expression = join(" && ", [
      "resource.type == 'storage.googleapis.com/Object'",
      "resource.name.startsWith('projects/_/buckets/${google_storage_bucket.raw_landing.name}/objects/${local.incoming_prefix}')",
    ])
  }
}

resource "google_storage_bucket_iam_member" "pipeline_object_viewer" {
  bucket = google_storage_bucket.raw_landing.name
  role   = "roles/storage.objectViewer"
  member = google_service_account.data_pipeline.member

  condition {
    title       = "incoming_objects_only"
    description = "Allow validation reads only below the incoming object prefix."
    expression = join(" && ", [
      "resource.type == 'storage.googleapis.com/Object'",
      "resource.name.startsWith('projects/_/buckets/${google_storage_bucket.raw_landing.name}/objects/${local.incoming_prefix}')",
    ])
  }
}

resource "google_bigquery_dataset" "staged" {
  project                    = var.project_id
  dataset_id                 = local.dataset_id
  friendly_name              = "D1 Staged and Enforced Student Onboarding"
  description                = "Validated onboarding events with deterministic schema and row-level security."
  location                   = upper(var.region)
  delete_contents_on_destroy = false
  max_time_travel_hours      = 96
  is_case_insensitive        = false
  labels                     = var.labels

  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.bigquery.id
  }

  depends_on = [google_kms_crypto_key_iam_member.bigquery_service_agent]
}

resource "google_bigquery_table" "onboarding" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.staged.dataset_id
  table_id            = local.table_id
  description         = "Canonical schema-enforced student onboarding records."
  schema              = var.bigquery_schema_json
  deletion_protection = true
  labels              = var.labels

  time_partitioning {
    type          = "DAY"
    field         = "ingested_at"
    expiration_ms = 7776000000
  }

  clustering = ["organisation_id", "student_external_id"]

  encryption_configuration {
    kms_key_name = google_kms_crypto_key.bigquery.id
  }
}

resource "google_bigquery_dataset_iam_member" "pipeline_editor" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.staged.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.data_pipeline.member
}

resource "google_bigquery_dataset_iam_member" "analytics_viewer" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.staged.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = google_service_account.analytics_reader.member
}

resource "google_project_iam_member" "pipeline_job_runner" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = google_service_account.data_pipeline.member
}

resource "google_project_iam_member" "analytics_job_runner" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = google_service_account.analytics_reader.member
}

resource "google_bigquery_row_access_policy" "pipeline_full_access" {
  project          = var.project_id
  dataset_id       = google_bigquery_dataset.staged.dataset_id
  table_id         = google_bigquery_table.onboarding.table_id
  policy_id        = "pipeline_full_access"
  filter_predicate = "TRUE"
  grantees         = [google_service_account.data_pipeline.member]
  deletion_policy  = "PREVENT"
}

resource "google_bigquery_row_access_policy" "dubai_analytics_only" {
  project          = var.project_id
  dataset_id       = google_bigquery_dataset.staged.dataset_id
  table_id         = google_bigquery_table.onboarding.table_id
  policy_id        = "dubai_analytics_only"
  filter_predicate = "emirate = 'DUBAI'"
  grantees         = [google_service_account.analytics_reader.member]
  deletion_policy  = "PREVENT"
}

resource "google_pubsub_schema" "onboarding" {
  project    = var.project_id
  name       = "student-onboarding-v1"
  type       = "AVRO"
  definition = var.pubsub_schema_definition
}

resource "google_pubsub_topic" "validated" {
  project = var.project_id
  name    = "student-onboarding-validated-v1"
  labels  = var.labels

  schema_settings {
    schema   = "projects/${var.project_id}/schemas/${google_pubsub_schema.onboarding.name}"
    encoding = "JSON"
  }

  message_retention_duration = "604800s"
  kms_key_name               = google_kms_crypto_key.pubsub.id

  depends_on = [google_kms_crypto_key_iam_member.pubsub_service_agent]
}

resource "google_bigquery_dataset_iam_member" "pubsub_writer" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.staged.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${var.pubsub_service_account_email}"
}

resource "google_project_iam_member" "pubsub_metadata_viewer" {
  project = var.project_id
  role    = "roles/bigquery.metadataViewer"
  member  = "serviceAccount:${var.pubsub_service_account_email}"
}

resource "google_pubsub_subscription" "bigquery_sink" {
  project = var.project_id
  name    = "student-onboarding-bigquery-v1"
  topic   = google_pubsub_topic.validated.id
  labels  = var.labels

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"
  retain_acked_messages      = false
  expiration_policy {
    ttl = "2678400s"
  }

  bigquery_config {
    table               = "${var.project_id}:${google_bigquery_dataset.staged.dataset_id}.${google_bigquery_table.onboarding.table_id}"
    use_topic_schema    = true
    drop_unknown_fields = false
  }

  depends_on = [
    google_bigquery_dataset_iam_member.pubsub_writer,
    google_project_iam_member.pubsub_metadata_viewer,
    google_bigquery_row_access_policy.pipeline_full_access,
    google_bigquery_row_access_policy.dubai_analytics_only,
  ]
}
