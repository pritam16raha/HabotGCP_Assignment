# Author: Pritam Raha <rahapritam32@gmail.com>
mock_provider "google" {
  mock_data "google_project" {
    defaults = {
      number = "123456789012"
    }
  }

  mock_data "google_storage_project_service_account" {
    defaults = {
      email_address = "service-123456789012@gs-project-accounts.iam.gserviceaccount.com"
    }
  }

  mock_resource "google_project_service_identity" {
    defaults = {
      email = "service-123456789012@gcp-sa-pubsub.iam.gserviceaccount.com"
    }
  }
}

mock_provider "google-beta" {
  mock_resource "google_project_service_identity" {
    defaults = {
      email = "service-123456789012@gcp-sa-pubsub.iam.gserviceaccount.com"
    }
  }
}

variables {
  project_id = "habot-staging-pritam-raha-2026"
}

run "secure_staging_plan" {
  command = plan

  assert {
    condition     = module.secure_data_landing.security_controls.bucket_public_access_prevention == "enforced"
    error_message = "The D0 bucket must fail closed against public access."
  }

  assert {
    condition     = module.secure_data_landing.security_controls.bucket_uniform_access
    error_message = "The D0 bucket must use uniform bucket-level access."
  }

  assert {
    condition     = module.secure_data_landing.security_controls.bucket_versioning
    error_message = "The D0 bucket must preserve object versions."
  }

  assert {
    condition     = module.secure_data_landing.security_controls.table_deletion_protection
    error_message = "The D1 table must have deletion protection."
  }

  assert {
    condition     = module.secure_data_landing.security_controls.region == "me-central1"
    error_message = "All data resources must remain in the selected Middle East region."
  }
}
