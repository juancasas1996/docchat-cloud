# Dev environment stack — managed by the CI pipeline (infra-plan / infra-apply),
# authenticated via OIDC. State lives in the Azure Storage backend created by
# the bootstrap stack.
terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "stdocchatjctfstate"
    container_name       = "tfstate"
    key                  = "docchat-cloud/dev.terraform.tfstate"
    use_azuread_auth     = true
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}
