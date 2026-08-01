# Author: Pritam Raha <rahapritam32@gmail.com>
terraform {
  required_version = ">= 1.14.0, < 2.0.0"

  backend "gcs" {
    prefix = "habot/student-onboarding/staging"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 7.0"
    }
  }
}
