# HIVEMIND RAG 
<img width="1919" height="1073" alt="Screenshot 2026-02-19 114519" src="https://github.com/user-attachments/assets/08878ef6-f7a6-478c-ab51-ce7303c8f429" />

A small desktop Retrieval-Augmented Generation (RAG) app built with Tkinter. It ingests PDFs, builds a persistent vector index and knowledge graph, and lets you chat with an LLM while visualizing the concept graph.

## Features
- PDF ingestion and chunking
- Persistent vector store using Chroma DB (on-disk under `Data/chroma`)
- Knowledge graph built with NetworkX and visualized via Matplotlib
- Chat UI with:
  - Per-session conversational memory stored in SQLite (`Data/nexus_history.db`)
  - "New Session" to start a fresh context and graph
  - "View History" to browse past sessions and transcripts

## Requirements
- Python 3.10+
- Tkinter (usually included with standard Python installs)
- Packages (typically installed in a virtual environment):
  - `google-genai` (via `google-genai` / `google-genai[genai]` depending on distribution)
  - `chromadb`
  - `networkx`
  - `PyPDF2`
  - `matplotlib`

Adjust exact package names to match what is installed in your `env/Lib/site-packages` if needed.

## Setup
1. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv env
   env/Scripts/activate  # Windows PowerShell or cmd
   ```

2. Install dependencies, for example:
   ```bash
   pip install chromadb networkx PyPDF2 matplotlib google-genai
   ```

3. Configure your Gemini / Google GenAI API key via one of:
   - Environment variable `GENAI_API_KEY` or `GEMINI_API_KEY`
   - Or a local file `.env.local` next to the Python files, containing a line like:
     ```
     GENAI_API_KEY=your_api_key_here
     ```

## Running the app
From the project root:
```bash
python main.py
```

The UI opens with:
- Left pane: document upload, session controls, and chat
- Right pane: knowledge graph visualization

## Data and persistence
- Vector index: stored under `Data/chroma/` using Chroma's persistent client.
- Chat history: stored in SQLite at `Data/nexus_history.db` via `ChatMemory`.
- Graph: kept in memory in `HiveProcessor.graph` and visualized by `GraphVisualizer`.

## New sessions and history
- **New Session**: clears the chat panel, resets the current session id, and clears the in-memory graph and visualization.
- **View History**: opens a window listing past sessions (id, timestamps, message count) and shows full transcripts when you select one.

## Project structure
- `main.py` – Tkinter UI and wiring of engine and visualizer
- `processor.py` – PDF ingestion, vector store, and knowledge graph logic
- `util.py` – HiveMind LLM wrapper and SQLite-backed `ChatMemory`
- `visualizer.py` – NetworkX + Matplotlib graph visualization
- `Data/` – runtime data (Chroma index, SQLite db)
- `env/` – optional Python virtual environment (ignored by git)
