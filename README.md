<h1 align="center">
  <br>
  <img src="https://raw.githubusercontent.com/yourusername/document-analyzer/main/assets/logo.png" alt="DocuMind AI" width="200">
  <br>
  DocuMind AI
  <br>
</h1>

<h4 align="center">Upload. Analyze. Understand. An advanced AI-powered Document & File Analyzer.</h4>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#demo">Demo</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#installation">Installation</a> •
  <a href="#api-reference">API</a> •
  <a href="#tech-stack">Tech Stack</a>
</p>

![Screenshot](https://raw.githubusercontent.com/yourusername/document-analyzer/main/assets/screenshot.png)

## 🎯 Features

*   **Multi-format Upload:** Supports `PDF`, `DOCX`, `TXT`, and `CSV` files (up to 10MB). Validated securely via magic bytes.
*   **Intelligent Summarization:** Uses map-reduce chunking to summarize large documents that exceed standard context windows. Generates executive summaries, key points, main topics, and document tone.
*   **Structured Data Extraction:** Automatically pulls out named entities, key facts, tables, and lists.
*   **Vibrant RAG Chat:** Ask questions directly to your document. Uses local `sentence-transformers` for completely private embeddings and top-k chunk retrieval.
*   **Modern UI:** A beautiful, responsive, glassmorphism single-page application built with Vanilla JS and CSS.
*   **Production Ready:** Includes Docker & Docker Compose setup, rate-limiting (SlowAPI), CORS, and auto-expiring in-memory sessions.


## 🚀 Demo



---

## ⚙️ How It Works

1.  **Parse & Chunk**: Uploaded documents are parsed natively (e.g., `pdfplumber` for PDFs). Text is cleaned and chunked into overlapping segments.
2.  **Summarize & Extract**: Chunks are processed by the AI sequentially (map-reduce) to build a comprehensive summary and extract structured data.
3.  **Embed & Chat**: Chunks are embedded locally using `all-MiniLM-L6-v2`. User questions are embedded, cosine similarity finds the most relevant chunks, and the AI answers based *only* on that context.

---

## 🛠️ Installation

### Option 1: Docker (Recommended)

The easiest way to get started is using Docker Compose.

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/document-analyzer.git
    cd document-analyzer
    ```
2.  Create a `.env` file and add your AI API key:
    ```env
    API_KEY=your_api_key_here
    ```
3.  Build and run:
    ```bash
    docker-compose up --build
    ```
4.  Open `http://localhost:3000` in your browser. (The API runs on port `8000`).

### Option 2: Local Development

1.  Clone the repository and create a virtual environment:
    ```bash
    git clone https://github.com/yourusername/document-analyzer.git
    cd document-analyzer
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
2.  Install dependencies:
    ```bash
    pip install -r backend/requirements.txt
    ```
    *(Note: `sentence-transformers` downloads caching models, so this might take a minute.)*
3.  Configure your environment in `.env`:
    ```env
    API_KEY=your_api_key_here
    ```
4.  Start the FastAPI server (it serves the frontend statically too!):
    ```bash
    uvicorn backend.main:app --reload --port 8000
    ```
5.  Open `http://localhost:8000` in your browser.

---

## � API Reference

Explore the full interactive documentation at `http://localhost:8000/docs` when the server is running.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/upload` | Upload a file; returns a `doc_id` for the session. |
| `POST` | `/analyze/{doc_id}` | Generates the map-reduce summary (cached). |
| `POST` | `/extract/{doc_id}` | Extracts structured entities and facts. |
| `POST` | `/chat/{doc_id}` | Ask a question; returns RAG answer with source citations. |
| `GET` | `/history/{doc_id}` | View full conversation history. |
| `DELETE` | `/session/{doc_id}` | Manually destroy the session. |

---

## 🧰 Tech Stack

**Backend**
*   [FastAPI](https://fastapi.tiangolo.com/) (Web Framework)
*   [Sentence-Transformers](https://sbert.net/) (Local Embeddings)
*   [PyPDF/pdfplumber](https://github.com/jsvine/pdfplumber), [python-docx](https://python-docx.readthedocs.io/), [pandas](https://pandas.pydata.org/) (Parsing)
*   [SlowAPI](https://slowapi.readthedocs.io/en/latest/) (Rate Limiting)

**Frontend**
*   Vanilla JavaScript, HTML5, CSS3
*   No heavy frameworks, highly optimized.

---

## � Security

*   **File Validation:** Checks magic bytes signatures, not just extensions.
*   **Rate Limiting:** Protects the API endpoints against abuse.
*   **Ephemeral Data:** Sessions and extracted data are destroyed automatically after 1 hour (`SESSION_TTL_HOURS=1`).
*   **API Key Safety:** Keys are loaded strictly from `.env` and never exposed to the client.

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

---

> Built with ❤️ by [Sidzzz.eren]
