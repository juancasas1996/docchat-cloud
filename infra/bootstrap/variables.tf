variable "subscription_id" {
  type    = string
  default = "3eb1ac8b-010e-411d-a8dd-bf3073a747d9"
}

variable "location" {
  type    = string
  default = "eastus2"
}

variable "resource_group_name" {
  type    = string
  default = "AgenticRAG"
}

variable "github_repository" {
  description = "GitHub repo (owner/name) trusted by the OIDC federated credentials"
  type        = string
  default     = "juancasas1996/docchat-cloud"
}

# GitHub embeds immutable ids in the OIDC subject claim
# (repo:owner@ownerId/name@repoId:...) so deleted-and-recreated repos or
# renamed accounts can never inherit the trust.
variable "github_owner_id" {
  type    = number
  default = 67381908
}

variable "github_repo_id" {
  type    = number
  default = 1312457834
}

variable "alert_email" {
  type    = string
  default = "juancasas1996@hotmail.com"
}

variable "budget_amount" {
  type    = number
  default = 5
}
