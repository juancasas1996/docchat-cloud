# The three values GitHub Actions needs for OIDC login (none are secrets).
output "azure_client_id" {
  value = azuread_application.github_actions.client_id
}

output "azure_tenant_id" {
  value = data.azurerm_client_config.current.tenant_id
}

output "azure_subscription_id" {
  value = var.subscription_id
}

output "state_storage_account" {
  value = azurerm_storage_account.tfstate.name
}
