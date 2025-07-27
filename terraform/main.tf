# Terraform configuration for Google Cloud deployment
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud Region"
  type        = string
  default     = "us-central1"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sql-component.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "containerregistry.googleapis.com"
  ])
  
  project = var.project_id
  service = each.value
  
  disable_dependent_services = true
}

# Cloud SQL instance for PostgreSQL
resource "google_sql_database_instance" "postgres" {
  name             = "the-assistant-db"
  database_version = "POSTGRES_14"
  region           = var.region
  
  settings {
    tier = "db-f1-micro"  # Adjust based on your needs
    
    backup_configuration {
      enabled = true
    }
    
    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "all"
        value = "0.0.0.0/0"  # Restrict this in production
      }
    }
  }
  
  deletion_protection = false  # Set to true in production
}

# Database
resource "google_sql_database" "the_assistant" {
  name     = "the_assistant"
  instance = google_sql_database_instance.postgres.name
}

# Database user
resource "google_sql_user" "the_assistant" {
  name     = "the_assistant"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

# Secrets
resource "google_secret_manager_secret" "db_encryption_key" {
  secret_id = "db-encryption-key"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "jwt-secret"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "telegram_token" {
  secret_id = "telegram-token"
  
  replication {
    auto {}
  }
}

# Cloud Storage bucket for Obsidian vault (optional)
resource "google_storage_bucket" "obsidian_vault" {
  name     = "${var.project_id}-obsidian-vault"
  location = var.region
  
  uniform_bucket_level_access = true
}

# Output important values
output "database_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "database_ip" {
  value = google_sql_database_instance.postgres.ip_address.0.ip_address
}

output "bucket_name" {
  value = google_storage_bucket.obsidian_vault.name
}