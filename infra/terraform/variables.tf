variable "name_prefix" {
  type        = string
  description = "Short prefix for Azure resources"
  default     = "atticus"
}

variable "resource_group_name" {
  type        = string
  description = "Azure resource group name"
  default     = "rg-atticus-demo"
}

variable "location" {
  type        = string
  description = "Azure region"
  default     = "eastus"
}

variable "api_image" {
  type        = string
  description = "Container image for atticus-api"
  default     = "ghcr.io/example/projectatticus:latest"
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default = {
    project = "ProjectAtticus"
    track   = "b"
  }
}
