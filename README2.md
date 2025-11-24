# Repository Reference Guide

## Project Overview
This project orchestrates a fish-identification workflow that combines large language models, Watsonx services, and Elasticsearch. It ingests curated fish descriptions, enriches them with physical and general embeddings, and exposes backend services capable of captioning images, searching similar species, and generating conversational answers about marine life.

## Directory Map
| Path | Purpose |
| --- | --- |
| `BE/` | Backend Flask service that fronts captioning, semantic search, and conversational features, plus supporting utilities and tests. |
| `EXTRACTION/` | Utilities for enriching source datasets with LLM-generated descriptions and preparing embedding-ready CSV outputs. |
| `INGESTION/` | Scripts to encode CSV descriptions, build dense vectors, and ingest them into Elasticsearch. |
| `NOTEBOOKS/` | Exploratory notebooks demonstrating API usage, data preparation pipelines, and ad-hoc experiments. |
| `snowflake-embedding/` | Standalone Flask microservice that serves Snowflake Arctic embeddings and deployment collateral. |
| `.github/workflows/` | CI workflow that builds Docker images and deploys Code Engine apps for backend and embedding services. |
| `.vscode/` | Editor configuration (Python analysis path tweaks). |
| `env-template` | Template of required environment variables spanning Watsonx, Elasticsearch, COS, and Code Engine. |
| `requirements.txt` & submodule requirement files | Python dependencies per component. |
| `image*.png`, `output_structure_embedding.png` | Application architecture and credential screenshots referenced by docs. |
| `README.md` | Primary quickstart covering ingestion/query flows and credential setup. |

## Root-Level Assets
- `README.md`: High-level ingestion and query walkthrough, plus environment variable sourcing instructions.
- `requirements.txt`: Consolidated dependencies for the common tooling layer (Flask, Elasticsearch client, pandas, sentence-transformers, dotenv).
- `env-template`: Starter `.env` skeleton for all IBM Cloud, Elasticsearch, and Watsonx credentials.
- `image*.png`, `output_structure_embedding.png`: Visual aids for environment setup and architecture overviews.

## Backend Service (`BE/`)
- `main.py`: Console demo that loads credentials, captions a sample image, embeds the caption, and executes a kNN search against Elasticsearch, illustrating end-to-end flow without the Flask API.
- `api_services.py`: Flask application exposing:
  - `GET /live` for health checks.
  - `POST /search` to embed free-form text (Watsonx embeddings) and retrieve the top-N fish by `physical_description_embedding` similarity.
  - `POST /image_captioning` to fetch an image from IBM Cloud Object Storage, caption it via Watsonx vision models, and return the textual description.
  - `POST /image_identification` to request a structured JSON description (Thai common names, habitats, physical traits) for COS-stored images.
  - `POST /generation` to produce conversational responses with optional context and chat history.
  - `POST /search_with_scientific_name` for exact scientific-name lookups.
  Each route relies on resilient fallback helpers and logs COS + Watsonx interactions for troubleshooting.
- `elasticsearch_query.py`: Helper class wrapping Elasticsearch connections for index inspection, text search, exact match queries, embedding-based kNN searches, and document counts.
- `embedding_service.py`: Abstraction that either loads the Snowflake Arctic sentence transformer locally or forwards embedding requests to an external Watsonx-backed endpoint (`EMBEDDING_SERVICE_URL`).
- `function.py`: Legacy Elastic utilities (semantic/match queries) and response massagers (`return_top_n_fish`, `return_fish_info`).
- `generation.py`: Watsonx-powered generative responder that builds rich fish references by combining physical and general embeddings before chatting with the `meta-llama/llama-3-3-70b-instruct` model. Includes a context-aware variant for species-specific chats.
- `watsonx_captioning.py`: Vision captioning and JSON-structured detail extraction against Watsonx vision instruct models. Handles IAM token exchange, system prompting, and JSON validation.
- `download_model.py`: Convenience script to prefetch the Snowflake embedding model/tokenizer into local cache (useful for air-gapped deployments).
- `Dockerfile`: Container recipe for deploying the backend Flask API (uses IBM Code Engine pipeline).
- `requirement.txt`: Component-specific dependency pinning aligning with IBM SDKs, Flask 3.x, Elasticsearch 8.x, and Watsonx clients.
- `tests/`:
  - `test_api.py`: Local manual tests for `/generation`, `/search`, `/image_captioning` using `requests`.
  - `test_api_services.py`: End-to-end smoke tests pointed at the deployed Code Engine endpoint (search, captioning, generation, COS integration, scientific name search).
  - `test_api_services.robot`: Robot Framework equivalents for automated regression of the REST endpoints.
  - `testcos.py`: Validation helper for downloading assets from IBM Cloud Object Storage buckets using COS credentials.

## Data Enrichment (`EXTRACTION/`)
- `create_embedding_csv.py`: Reads baseline fish lists, calls Watsonx (`physical_description_service`) for detailed physical descriptors with checkpointing, and emits a CSV containing fish names, descriptions, and templated COS object keys ready for embedding.
- `physical_description_service.py`: Text-only Watsonx prompt that produces consistent "body/colors/features/unique_marks" strings per species.
- `updating_description.py`: Patches physical description columns in the source CSV using the checkpointed JSON outputs, writing an updated dataset.
- `fish_descriptions_checkpoint.json`: Rolling cache of generated descriptions to resume long-running enrichment jobs.
- `embedding_format.csv`: Sample output containing enriched descriptions and object key templates.
- `requirement.txt`: Minimal dependency specification for Watsonx enrichment jobs.
- `DATA/`:
  - `fish-description-files/`: Canonical marine fish reference tables in CSV/TXT/PDF/XLSX formats.
  - `fish-random/`: Sample fish imagery used for captioning tests.

## Index Ingestion (`INGESTION/`)
- `main.py`: Command-line ingestion orchestrator; loads updated CSV data, obtains Watsonx embeddings for general and physical descriptions, appends the vectors to the dataframe, optionally recreates the Elasticsearch index, and bulk ingests documents.
- `elasticsearch_manager.py`: Index lifecycle manager—defines mappings with twin dense vectors, handles creation/deletion, counts documents, and executes the bulk upload via `elasticsearch.helpers.bulk`.
- `embedding_service.py`: Mirrors the backend embedding adapter, configurable between local Snowflake and remote Watsonx services.
- `test.py`: Diagnostic script that exercises the deployed embedding service endpoint and prints embedding lengths for each record.
- `Marine_Fish_Species_Full_Description_test.csv`: Reduced dataset variant for quick ingestion tests.
- `requirements.txt`: Dependencies for ingestion scripts (pandas, Elasticsearch client, sentence transformers, COS SDK, etc.).

## Exploratory Notebooks (`NOTEBOOKS/`)
- `api_demo.ipynb`: Likely demos the backend API calls (captioning, search) in an interactive environment.
- `service_example.ipynb`: Referenced by the main README as a companion walkthrough for `ElasticsearchManager`, `ElasticsearchQuery`, and `EmbeddingService` usage.
- `test-pipeline.ipynb`, `dump.ipynb`: Sandbox notebooks for experimentation, pipeline validation, or intermediate data dumps.
- `Marine_Fish_Species_Full_Description_test.csv`: Quick-access CSV copy for notebook workflows.

## Embedding Microservice (`snowflake-embedding/`)
- `app.py`: Flask service exposing `/extract_text` that encodes request sentences with the Snowflake Arctic embedding model and returns model outputs in the same schema expected by Watsonx inference responses.
- `download_model.py`: Preloads the transformer weights into cache for warm starts.
- `Dockerfile`: Container definition used by CI to publish the embedding service image.
- `requirements.txt`: Service-specific dependencies (Flask and sentence transformers).
- `README.md`: Placeholder for additional deployment notes (currently empty).
- `api-test.ipynb`: Notebook for local validation of the embedding endpoint.

## Automation & Tooling
- `.github/workflows/docker-image.yml`: GitHub Actions workflow that, on relevant pushes, builds container images for `BE/` and `snowflake-embedding/`, pushes them to IBM Container Registry, and updates/creates IBM Code Engine apps with configurable CPU/memory settings.
- `.vscode/settings.json`: Ensures the backend folder is included in Python analysis paths, smoothing imports inside VS Code.
- `.gitignore`: Omits environment files, virtual environments, cached artifacts, certificates, and local app folders from version control.

## Working With The Project
1. **Provision credentials**: Copy `env-template` to `.env`, fill Watsonx, Elasticsearch, COS, and Code Engine settings, and ensure images/indices exist in the referenced services.
2. **Enrich descriptions (optional refresh)**: Run scripts in `EXTRACTION/` to regenerate physical descriptions and produce `Marine_Fish_Species_Formatted_updated.csv`.
3. **Ingest data**: Execute `INGESTION/main.py` to embed descriptions via Watsonx (or switch to local models) and populate the target Elasticsearch index.
4. **Serve APIs**: Deploy `BE/` (locally via `python api_services.py` or through the provided Docker workflow) alongside the optional `snowflake-embedding/` microservice if you need on-demand embeddings.
5. **Validate**: Use tests under `BE/tests/` or the notebooks in `NOTEBOOKS/` to exercise captioning, search, and conversational features end-to-end.

This companion guide complements the existing README by cataloging the repository contents so new contributors can quickly orient themselves and locate the right scripts for enrichment, ingestion, and serving tasks.
