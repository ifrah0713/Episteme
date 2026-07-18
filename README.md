# ⚡ Episteme — STEM Knowledge Assistant

> An intelligent AI-powered STEM knowledge assistant built with RAG (Retrieval-Augmented Generation), featuring multi-modal learning tools and Google OAuth authentication.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)
![LangChain](https://img.shields.io/badge/LangChain-0.x-green)
![Groq](https://img.shields.io/badge/Groq-LLaMA3-orange)

---

## 🚀 Features

| Feature | Description |
|--------|-------------|
| 🧠 **RAG Pipeline** | Retrieves from Wikipedia, ArXiv, PubMed + uploaded PDFs |
| 🔐 **Google OAuth** | Secure login — each user has private chat history |
| 📊 **Diagram Generator** | Auto-generates Mermaid.js diagrams |
| 🧪 **Quiz Mode** | MCQ quiz with scoring and explanations |
| ⚖️ **Compare Mode** | Side-by-side comparison tables |
| 🧒 **ELI5 Mode** | Explains complex topics simply |
| 💻 **Code Explainer** | Analyzes and explains code |
| 📐 **Formula Renderer** | LaTeX math formula rendering |
| 🔬 **ArXiv Search** | Finds verified research paper links |
| 📋 **Session Summary** | Auto-generates PDF session summaries |
| 🟢 **Confidence Meter** | Shows answer confidence level |
| 💡 **Follow-up Questions** | Suggests relevant next questions |
| 📄 **PDF Upload** | Ask questions from uploaded documents |
| 🌙 **Dark/Light Theme** | Toggle between themes |

---

## 🛠️ Tech Stack

```
Frontend     → Streamlit
LLM          → Groq (LLaMA 3.3 70B)
Embeddings   → HuggingFace (all-MiniLM-L6-v2)
Vector DB    → ChromaDB
Framework    → LangChain
Auth         → Google OAuth 2.0
Search       → ArXiv API + DuckDuckGo
PDF Reports  → ReportLab
Database     → SQLite
```

---

## 📁 Project Structure

```
Episteme/
├── app.py              # Main Streamlit app
├── generator.py        # LLM generation + mode detection
├── retriever.py        # Hybrid RAG retrieval
├── ingest.py           # Knowledge base ingestion
├── pdf_loader.py       # PDF processing
├── database.py         # SQLite chat history
├── requirements.txt    # Dependencies
├── .gitignore          # Hidden files
└── README.md           # This file
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/Episteme.git
cd Episteme
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
Create a `.env` file:
```
GROQ_API_KEY=your_groq_api_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
SERPER_API_KEY=your_serper_api_key  # optional
```

### 5. Set up Google OAuth
- Create project on [Google Cloud Console](https://console.cloud.google.com)
- Enable OAuth 2.0
- Download `client_secret.json` to project folder

### 6. Build knowledge base
```bash
python ingest.py
```

### 7. Run the app
```bash
streamlit run app.py
```

---

## 🎯 Special Modes

| Command | Description |
|---------|-------------|
| `Quiz me on PID controller` | Generates 5 MCQ questions |
| `Compare FPGA vs Arduino` | Side-by-side comparison table |
| `ELI5: Quantum computing` | Simple explanation with analogy |
| `Explain this code: [paste]` | Code analysis and bug detection |
| `Draw diagram of PID controller` | Auto-generates flowchart |
| `I need paper: YOLO` | Searches ArXiv for verified links |

---

## 🔒 Privacy & Security

- All API keys stored in `.env` (never committed to GitHub)
- Google OAuth for secure authentication
- Each user has private, isolated chat history
- No data sharing between users

---

## 👩‍💻 Developer

**Ifrah Gohar Khan**
- 📚 BE Avionics Engineering — Institute of Space Technology, Islamabad
- 💼 LinkedIn: [linkedin.com/in/ifrah-gohar](https://linkedin.com/in/ifrah-gohar)
- 🐙 GitHub: [github.com/YOUR_USERNAME](https://github.com/YOUR_USERNAME)

---

## 📄 License

This project is for educational and portfolio purposes.

---

*Built with ❤️ using Streamlit, LangChain, and Groq*
