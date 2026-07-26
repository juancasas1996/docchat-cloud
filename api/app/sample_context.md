# DocChat Cloud

DocChat Cloud is a portfolio project by Juan Sebastián Casas that demonstrates
a production-style deployment of an agentic RAG system on Microsoft Azure.

## Architecture

The system runs on Azure Container Apps with scale-to-zero, inside the
AgenticRAG resource group. It has two services: a FastAPI backend (the API)
and a Streamlit frontend. Container images are built by GitHub Actions and
stored in GitHub Container Registry (GHCR).

All infrastructure is defined with Terraform, split in two stacks: a bootstrap
stack (run locally once, creating the OIDC trust and the remote-state storage)
and a dev environment stack managed entirely by CI/CD.

## CI/CD

The main branch is protected: every change enters through a pull request.
On each PR, GitHub Actions runs terraform plan (commented on the PR) and test
builds of the Docker images. On merge, a pipeline applies the infrastructure
first, then builds and deploys the application images. GitHub authenticates
to Azure with OIDC federated credentials, so no cloud passwords are stored.

## The agent

The chat endpoint is powered by a LangGraph workflow with three nodes:

1. Triage — classifies whether the question can be answered from the context.
2. Answer — drafts an answer using only the provided context.
3. Verify — checks the draft against the context and reports unsupported
   claims; if verification fails, the answer is retried once.

The agent uses the NVIDIA API (OpenAI-compatible) with the
meta/llama-3.1-8b-instruct model by default, chosen because the free tier
serves it in about one second while larger models often queue or time out.

## Roadmap

Upcoming phases: Azure Key Vault for secrets (phase 4), PostgreSQL with a
pluggable vector store (phase 5), and document ingestion with full RAG
retrieval (phase 6).
