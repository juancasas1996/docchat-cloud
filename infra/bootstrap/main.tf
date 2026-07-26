data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}

# ---------------------------------------------------------------------------
# OIDC trust for GitHub Actions — the Azure equivalent of an AWS IAM role
# with a GitHub OIDC trust policy. No passwords are ever stored in GitHub.
# ---------------------------------------------------------------------------

resource "azuread_application" "github_actions" {
  display_name = "github-actions-docchat-cloud"
}

resource "azuread_service_principal" "github_actions" {
  client_id = azuread_application.github_actions.client_id
}

# Trust pushes to main (infra apply + app deploy).
resource "azuread_application_federated_identity_credential" "main_branch" {
  application_id = azuread_application.github_actions.id
  display_name   = "github-docchat-cloud-main"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_repository}:ref:refs/heads/main"
}

# Trust pull requests (terraform plan on PRs).
resource "azuread_application_federated_identity_credential" "pull_request" {
  application_id = azuread_application.github_actions.id
  display_name   = "github-docchat-cloud-pr"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_repository}:pull_request"
}

# CI can only touch the project resource group — nothing else in the account.
resource "azurerm_role_assignment" "github_actions_contributor" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.github_actions.object_id
}

# ---------------------------------------------------------------------------
# Remote Terraform state (the Azure equivalent of LegalSifter's S3 backend).
# Lives in its own resource group so a destroy of AgenticRAG can never take
# the state down with it.
# ---------------------------------------------------------------------------

resource "azurerm_resource_group" "tfstate" {
  name     = "rg-tfstate"
  location = var.location
}

resource "azurerm_storage_account" "tfstate" {
  name                     = "stdocchatjctfstate"
  resource_group_name      = azurerm_resource_group.tfstate.name
  location                 = azurerm_resource_group.tfstate.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  blob_properties {
    versioning_enabled = true
  }
}

resource "azurerm_storage_container" "tfstate" {
  name               = "tfstate"
  storage_account_id = azurerm_storage_account.tfstate.id
}

# Blob-level access for the CI principal and for the local operator.
resource "azurerm_role_assignment" "github_actions_state" {
  scope                = azurerm_storage_account.tfstate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azuread_service_principal.github_actions.object_id
}

resource "azurerm_role_assignment" "operator_state" {
  scope                = azurerm_storage_account.tfstate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# ---------------------------------------------------------------------------
# Budget guardrail: mail at $1 (20%), $4 (80%) and forecasted overrun.
# ---------------------------------------------------------------------------

resource "azurerm_consumption_budget_subscription" "guardrail" {
  name            = "budget-agenticrag"
  subscription_id = "/subscriptions/${var.subscription_id}"

  amount     = var.budget_amount
  time_grain = "Monthly"

  time_period {
    start_date = "2026-07-01T00:00:00Z"
  }

  notification {
    enabled        = true
    threshold      = 20
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = [var.alert_email]
  }

  notification {
    enabled        = true
    threshold      = 80
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = [var.alert_email]
  }

  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThan"
    threshold_type = "Forecasted"
    contact_emails = [var.alert_email]
  }
}
