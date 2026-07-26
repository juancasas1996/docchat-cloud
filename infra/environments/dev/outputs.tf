output "api_url" {
  value = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "frontend_url" {
  value = "https://${azurerm_container_app.frontend.ingress[0].fqdn}"
}

output "mcp_endpoint" {
  value = "https://${azurerm_container_app.mcp.ingress[0].fqdn}/mcp"
}
