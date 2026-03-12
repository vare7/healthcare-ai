# Guide: Cost-Efficient Azure Hosting Options

This project can be hosted on Azure in multiple ways. Two pragmatic options:

## Option 1: Single VM running Docker Compose

**Summary:** Lift-and-shift your existing `docker compose` workflow onto a single Azure VM.

- Use a burstable VM such as `Standard_B4ms` (4 vCPU, 16 GB RAM).
- SSH into the VM, install Docker, and clone this repo.
- Run the same commands as locally:

  ```bash
  docker compose up -d
  docker exec -it healthcare-ai-ollama ollama pull llama3.2
  docker exec -it healthcare-ai-ollama ollama pull nomic-embed-text
  ```

**Pros**

- Minimal code changes (none).
- Full local-style data sovereignty: Ollama and MySQL stay on the VM.

**Cons**

- You manage OS patching and uptime.
- CPU-only inference may be slower than managed GPU-backed options.

## Option 2: Managed PaaS + Azure OpenAI (future refactor)

**Summary:** Move the LLM and embeddings to Azure OpenAI and run the app and DB on managed services.

- Replace `langchain-ollama` with `langchain-openai` (AzureChatOpenAI + AzureOpenAIEmbeddings).
- Deploy:
  - App: Azure Container Apps or App Service using the existing `Dockerfile`.
  - DB: Azure Database for MySQL (small burstable tier).
  - LLM + embeddings: Azure OpenAI deployments (e.g., GPT-4o-mini + text-embedding-3-small).

**Pros**

- Lower operational overhead (no VM management).
- Pay-per-token pricing with autoscaling.

**Cons**

- Not “fully local” anymore – data stays within your Azure tenant but leaves the VM.
- Requires a small code change to swap LLM providers.

For production, Option 2 is usually more cost-efficient and scalable; for strict locality and maximum control, Option 1 is a good starting point.

