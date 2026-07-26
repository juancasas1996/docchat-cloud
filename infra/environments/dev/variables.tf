variable "subscription_id" {
  type    = string
  default = "3eb1ac8b-010e-411d-a8dd-bf3073a747d9"
}

variable "resource_group_name" {
  type    = string
  default = "AgenticRAG"
}

# Container apps start with a public placeholder image; the CI/CD pipeline
# replaces it with the real GHCR images and Terraform ignores that drift.
variable "bootstrap_image" {
  type    = string
  default = "mcr.microsoft.com/k8se/quickstart:latest"
}
