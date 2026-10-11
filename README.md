# Local Knowledge Vault

A private, local-first document search and question-answering app. Upload PDFs, images, DOCX, text, or ZIP archives; OCR and index them locally; retrieve cited passages; and ask an OpenAI-compatible model running on your own machine.

## Privacy model

- The server binds to `127.0.0.1` and rejects non-loopback clients.
- State-changing requests require a same-origin browser request.
- Raw model Markdown is rendered with DOM text nodes; raw HTML is never executed.
- Documents, indexes, databases, model caches, logs, credentials, and `.env` files are excluded from Git.
- The private data directory is selected before the RAG module loads and is printed at startup, preventing a restart from silently opening a different empty vault.
- No telemetry or cloud LLM is configured. The first run downloads the local embedding/reranking models from Hugging Face unless they are already cached.
- Your OpenAI-compatible model endpoint is configurable and defaults to local Ollama at `http://127.0.0.1:11434`.

## Turnkey setup

Requirements: Python 3.11+ and a local OpenAI-compatible model server (Ollama, llama.cpp, LM Studio, etc.). OCR and ranking run on CPU.

### Windows

```powershell
.\setup.ps1
.\start.ps1
```

### Linux/macOS

```sh
chmod +x setup.sh start.sh
./setup.sh
./start.sh
```

Open <http://127.0.0.1:1337/rag>.

Use Enter to invoke **Ask local model** and Shift+Enter for a newline. Answers render safe Markdown including headings, lists, emphasis, links, blockquotes, and code.

## Configuration

Environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AIWS_KNOWLEDGE_ROOT` | `./data` | Private originals, SQLite database, and FAISS indexes |
| `AIWS_ACTIVE_BACKEND` | `http://127.0.0.1:11434` | Default OpenAI-compatible local model endpoint |
| `AIWS_PROFILE_ROUTER` | same as active backend | Endpoint used for explicitly selected models |
| `KNOWLEDGE_PORT` | `1337` | Local web port |
| `HF_HOME` | `./.cache/huggingface` | Hugging Face cache |
| `AIWS_FASTEMBED_CACHE` | `./.cache/fastembed` | Embedding/reranker cache |

Copy `.env.example` as a reference, but export variables in your shell or launcher; the app deliberately does not load `.env` files implicitly.

## Limits and storage

Uploads are streamed in 8 MiB chunks and can resume. Individual uploads and ZIPs may be up to 20 GiB; expanded archives are capped at 100 GiB and 100,000 members. Archive paths, links, encryption, compression ratios, and available disk space are validated. Keep backups of the private data directory separately—the repository never contains it.
