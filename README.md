# 🤖 WhatsApp RAG Agent

A production-ready **Retrieval-Augmented Generation (RAG)** agent integrated with the **WhatsApp Business API**. Users can ask questions via WhatsApp and receive intelligent, context-aware answers extracted from a custom PDF knowledge base — all in real time.

---

## 📌 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [How It Works](#how-it-works)
- [Limitations & Future Improvements](#limitations--future-improvements)

---

## Overview

This agent allows end-users to interact with a PDF document through **WhatsApp** as the front-end interface. Instead of building a web UI, the conversational interface lives directly inside WhatsApp — making it highly accessible.

Under the hood, the system uses a **LangGraph-powered RAG pipeline** that retrieves semantically relevant chunks from a Chroma vector store and generates grounded answers using a large language model (LLaMA 3.3 70B via Groq).

If no relevant context is found, the agent gracefully falls back to a predefined response rather than hallucinating.

---

## Architecture

```
WhatsApp User
      │
      ▼
WhatsApp Cloud API (Webhook POST)
      │
      ▼
FastAPI Server  (/webhook)
      │
      ▼
LangGraph RAG Pipeline
   ┌──┴──────────────────┐
   │                     │
[Retrieve Node]    [Generate Node]
   │                     │
Chroma Vector DB    Groq LLM (LLaMA 3.3 70B)
(Gemini Embeddings)
      │
      ▼
Answer sent back via WhatsApp Cloud API
```

**Pipeline flow:**
1. User sends a message on WhatsApp
2. WhatsApp Cloud API forwards it to the FastAPI webhook
3. LangGraph retrieves relevant document chunks from ChromaDB
4. LLM generates a grounded answer from retrieved context
5. Answer is sent back to the user via WhatsApp

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Server | FastAPI |
| RAG Orchestration | LangGraph + LangChain |
| Vector Store | ChromaDB (persisted locally) |
| Embeddings | Google Gemini Embedding 001 |
| LLM | LLaMA 3.3 70B via Groq API |
| Document Loader | LangChain PyPDFLoader |
| Messaging Interface | WhatsApp Business Cloud API |
| Environment Management | python-dotenv |

---

## Project Structure

```
whatsapp_rag_agent/
│
├── ingest.py          # PDF loading, chunking, and vector store creation
├── graph.py           # LangGraph RAG pipeline (retrieve → generate)
├── main.py            # FastAPI server + WhatsApp webhook handlers
├── .env               # API keys and tokens (never commit this)
├── vector_store/      # Persisted ChromaDB vector store
└── README.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- A [WhatsApp Business Account](https://developers.facebook.com/docs/whatsapp) with Cloud API access
- A publicly accessible server or tunnel (e.g., [ngrok](https://ngrok.com/)) for webhook delivery
- API keys for **Groq** and **Google AI (Gemini)**

### 1. Clone the Repository

```bash
git clone https://github.com/alirazaaihub/whatsapp_agent.git
cd whatsapp-rag-agent
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Core dependencies:**

```
fastapi
uvicorn
langchain
langchain-community
langchain-chroma
langchain-groq
langchain-google-genai
langgraph
chromadb
pypdf
python-dotenv
requests
```

### 3. Ingest Your PDF

Place your PDF in the project directory and update the `file_path` in `ingest.py`, then run:

```bash
python ingest.py
```

This will create and persist the vector store under `vector_store/`.

---

## Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_gemini_api_key
GROQ_API_KEY=your_groq_api_key
WHATSAPP_TOKEN=your_whatsapp_cloud_api_bearer_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
VERIFY_TOKEN=your_custom_webhook_verify_token
```

> ⚠️ **Never commit `.env` to version control.** Add it to `.gitignore`.

---

## Running the Application

### Start the FastAPI Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Expose Locally via ngrok (for development)

```bash
ngrok http 8000
```

Copy the generated HTTPS URL and configure it as your webhook URL in the [Meta Developer Dashboard](https://developers.facebook.com):

```
Webhook URL:   https://your-ngrok-url.ngrok.io/webhook
Verify Token:  (same value as VERIFY_TOKEN in .env)
```

---

## API Endpoints

### `GET /`
Health check endpoint.

**Response:**
```json
{ "status": "ok" }
```

---

### `GET /webhook`
WhatsApp webhook **verification** endpoint. Called once by Meta when you register the webhook.

**Query Parameters:**

| Parameter | Description |
|---|---|
| `hub.mode` | Must be `subscribe` |
| `hub.verify_token` | Must match your `VERIFY_TOKEN` |
| `hub.challenge` | Echo'd back on success |

---

### `POST /webhook`
Receives **incoming WhatsApp messages**. Triggers the RAG pipeline and sends the answer back.

**Payload:** Standard WhatsApp Cloud API webhook event.

---

## How It Works

### Ingestion Pipeline (`ingest.py`)

1. **PDF Loading** — `PyPDFLoader` reads and parses the PDF page by page
2. **Chunking** — `RecursiveCharacterTextSplitter` splits documents into 500-token chunks with 100-token overlap to preserve context across boundaries
3. **Embedding** — Each chunk is embedded using Google's `gemini-embedding-001` model
4. **Persistence** — Embeddings are stored in a local ChromaDB instance at `vector_store/`

> On subsequent runs, if the vector store already exists, ingestion is skipped — the existing store is loaded directly.

---

### RAG Graph (`graph.py`)

Built with **LangGraph**, the pipeline is defined as a stateful directed graph:

```
[retrieve] ──► [generate] ──► END
```

**State Schema:**
```python
class AgentState(TypedDict):
    question: str   # User's input question
    context:  str   # Retrieved document chunks
    answer:   str   # LLM-generated answer
```

**`retrieve` node** — Queries ChromaDB for the top-4 most semantically similar chunks using cosine similarity over Gemini embeddings. Sets `context = "NO_CONTEXT"` if nothing is found.

**`generate` node** — Passes the retrieved context and question to LLaMA 3.3 70B. The model is strictly instructed to answer only from the provided context. If context is unavailable or irrelevant, it returns a predefined fallback message.

---

### WhatsApp Integration (`main.py`)

- On `GET /webhook`: Handles the one-time verification handshake with Meta
- On `POST /webhook`: Extracts the user's message text and phone number from the webhook payload, calls `get_answer()`, and delivers the response via the WhatsApp Cloud API `messages` endpoint

---

## Limitations & Future Improvements

| Limitation | Suggested Improvement |
|---|---|
| Single static PDF | Support dynamic document uploads via WhatsApp media messages |
| No conversation memory | Add `ConversationBufferMemory` or LangGraph checkpointing for multi-turn chat |
| Hardcoded file path | Accept file path via environment variable or CLI argument |
| No input validation | Add message length limits and type guards on the webhook payload |
| Synchronous LLM call | Implement async LLM invocation for better throughput under load |
| Local vector store only | Migrate to a managed vector DB (e.g., Pinecone, Qdrant) for production |

---

## Author

**Ali** — AI Engineer  
Building production-grade agentic AI systems.

---
📌 [LinkedIn](www.linkedin.com/in/alirazaaihub)
## License

MIT License — free to use, modify, and distribute.
