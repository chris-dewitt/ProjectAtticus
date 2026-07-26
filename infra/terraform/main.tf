terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "atticus" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

resource "azurerm_log_analytics_workspace" "atticus" {
  name                = "${var.name_prefix}-logs"
  location            = azurerm_resource_group.atticus.location
  resource_group_name = azurerm_resource_group.atticus.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "atticus" {
  name                       = "${var.name_prefix}-env"
  location                   = azurerm_resource_group.atticus.location
  resource_group_name        = azurerm_resource_group.atticus.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.atticus.id
}

# Placeholder container app — wire image/registry before apply.
resource "azurerm_container_app" "api" {
  name                         = "${var.name_prefix}-api"
  container_app_environment_id = azurerm_container_app_environment.atticus.id
  resource_group_name          = azurerm_resource_group.atticus.name
  revision_mode                = "Single"

  template {
    container {
      name   = "atticus-api"
      image  = var.api_image
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "ATTICUS_TELEMETRY"
        value = "1"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}
