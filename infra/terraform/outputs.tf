output "resource_group" {
  value = azurerm_resource_group.atticus.name
}

output "container_app_fqdn" {
  value = try(azurerm_container_app.api.ingress[0].fqdn, null)
}
