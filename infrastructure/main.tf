# Author: Pritam Raha <rahapritam32@gmail.com>
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

locals {
  required_services = toset([
    "bigquery.googleapis.com",
    "cloudkms.googleapis.com",
    "iam.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
  ])

  labels = {
    application = "student-onboarding"
    environment = var.environment
    managed_by  = "terraform"
    owner       = "pritam-raha"
  }
}

data "google_project" "current" {
  project_id = var.project_id
}

resource "google_project_service" "required" {
  for_each = local.required_services

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_project_service" "iam_credentials" {
  project            = var.project_id
  service            = "iamcredentials.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service_identity" "pubsub" {
  provider = google-beta
  project  = var.project_id
  service  = "pubsub.googleapis.com"

  depends_on = [google_project_service.required["pubsub.googleapis.com"]]
}

data "google_storage_project_service_account" "current" {
  project = var.project_id

  depends_on = [google_project_service.required["storage.googleapis.com"]]
}

data "google_bigquery_default_service_account" "current" {
  project = var.project_id

  depends_on = [google_project_service.required["bigquery.googleapis.com"]]
}

module "secure_data_landing" {
  source = "./modules/secure_data_landing"

  project_id                     = var.project_id
  project_number                 = data.google_project.current.number
  region                         = var.region
  environment                    = var.environment
  labels                         = local.labels
  raw_retention_seconds          = var.raw_retention_seconds
  storage_service_account_email  = data.google_storage_project_service_account.current.email_address
  bigquery_service_account_email = data.google_bigquery_default_service_account.current.email
  pubsub_service_account_email   = google_project_service_identity.pubsub.email
  bigquery_schema_json           = file("${path.root}/../contracts/bigquery/student_onboarding.schema.json")
  pubsub_schema_definition       = file("${path.root}/../contracts/pubsub/student_onboarding.avsc")

  depends_on = [google_project_service.required]
}
