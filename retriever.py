# ============================================================
# Episteme — Retriever (retriever.py)
# Purpose: Smart hybrid search — Local + PDF + Wikipedia + ArXiv
# ============================================================

import time
import requests
import wikipedia
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

# ─── Load Environment Variables ───────────────────────────────
load_dotenv()

# ─── Constants ────────────────────────────────────────────────
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHROMA_DIR      = "./chroma_db"
TOP_K           = 6
ARXIV_BASE_URL  = "http://export.arxiv.org/api/query"

# ─── Research Keywords ────────────────────────────────────────
RESEARCH_KEYWORDS = [
    "latest", "recent", "research", "paper", "study",
    "algorithm", "novel", "state of art", "method",
    "proposed", "survey", "review", "2024", "2025", "2026",
    "advancement", "new approach", "compare", "performance",
    "implementation", "architecture", "framework", "model",
    "technique", "approach", "analysis", "evaluation",
]

# ─── Vague Words ──────────────────────────────────────────────
VAGUE_WORDS = [
    "it", "this", "that", "they", "them",
    "its", "these", "those", "he", "she",
    "what", "are", "the", "for", "how",
    "yeh", "woh", "iska", "uska", "isne",
]


# ─── Check If Research Query ──────────────────────────────────
def is_research_query(query: str) -> bool:
    """Detect if query needs research papers."""
    query_lower = query.lower()
    return any(kw in query_lower for kw in RESEARCH_KEYWORDS)


# ─── Check If Query Is Vague ──────────────────────────────────
def is_vague_query(query: str) -> bool:
    """Detect if query is vague and needs chat history."""
    words       = query.lower().split()
    vague_count = sum(1 for w in words if w in VAGUE_WORDS)
    return vague_count >= len(words) * 0.5


# ─── Extract Better Search Query ──────────────────────────────
def extract_search_query(query: str, chat_history: list = []) -> str:
    """Extract meaningful query — use history if vague."""
    if is_vague_query(query) and chat_history:
        for msg in reversed(chat_history):
            if msg["role"] == "user" and not is_vague_query(msg["content"]):
                print(f"  🔄 Vague query — using context: '{msg['content'][:50]}'")
                return msg["content"]
    return query


# ─── Load Vectorstore ─────────────────────────────────────────
def load_vectorstore():
    """Load existing ChromaDB vectorstore."""
    embeddings  = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vectorstore = Chroma(
        persist_directory  = CHROMA_DIR,
        embedding_function = embeddings,
    )
    return vectorstore


# ─── Local ChromaDB Search ────────────────────────────────────
def retrieve(query: str) -> list:
    """Search local vectorstore — all chunks."""
    try:
        vectorstore = load_vectorstore()
        retriever   = vectorstore.as_retriever(
            search_type   = "similarity",
            search_kwargs = {"k": TOP_K},
        )
        docs = retriever.invoke(query)
        return docs
    except Exception as e:
        print(f"  ❌ Local DB search failed: {e}")
        return []


# ─── PDF Specific Search ──────────────────────────────────────
def retrieve_pdf_chunks(query: str) -> list:
    """Search specifically in uploaded PDF chunks."""
    try:
        embeddings  = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        vectorstore = Chroma(
            persist_directory  = CHROMA_DIR,
            embedding_function = embeddings,
        )
        results = vectorstore.similarity_search(
            query  = query,
            k      = 6,
            filter = {"type": "pdf"},
        )
        if results:
            print(f"  📄 PDF chunks retrieved: {len(results)}")
        else:
            print(f"  📄 No PDF chunks found")
        return results
    except Exception as e:
        print(f"  ⚠️ PDF search failed: {e}")
        return []


# ─── Live Wikipedia Search ────────────────────────────────────
def search_wikipedia_live(query: str) -> list:
    """Search Wikipedia in real-time."""
    docs = []
    try:
        wikipedia.set_lang("en")
        wikipedia.set_rate_limiting(True)
        results = wikipedia.search(query, results=2)

        for title in results:
            try:
                page    = wikipedia.page(title, auto_suggest=False)
                content = page.content[:2000]
                doc = Document(
                    page_content = content,
                    metadata     = {
                        "source" : page.url,
                        "title"  : page.title,
                        "type"   : "wikipedia_live",
                    },
                )
                docs.append(doc)
            except Exception:
                continue

    except Exception as e:
        print(f"  ⚠️ Wikipedia live search failed: {e}")

    return docs


# ─── Live ArXiv Search ────────────────────────────────────────
def search_arxiv_live(query: str, max_results: int = 3) -> list:
    """Search ArXiv in real-time — research queries only."""
    docs = []
    try:
        params = {
            "search_query" : f"all:{query}",
            "start"        : 0,
            "max_results"  : max_results,
        }
        response = requests.get(
            ARXIV_BASE_URL,
            params  = params,
            timeout = 10,
        )
        content   = response.text
        summaries = []
        titles    = []

        parts = content.split("<entry>")
        for part in parts[1:]:
            try:
                title   = part.split("<title>")[1].split("</title>")[0].strip()
                summary = part.split("<summary>")[1].split("</summary>")[0].strip()
                titles.append(title)
                summaries.append(summary)
            except Exception:
                continue

        for i, summary in enumerate(summaries[:max_results]):
            title = titles[i] if i < len(titles) else f"ArXiv Paper {i+1}"
            doc = Document(
                page_content = summary,
                metadata     = {
                    "source" : f"https://arxiv.org/search/?query={query}",
                    "title"  : title,
                    "type"   : "arxiv_live",
                },
            )
            docs.append(doc)

    except Exception as e:
        print(f"  ⚠️ ArXiv live search failed: {e}")

    return docs


# ─── Smart Hybrid Retrieve ────────────────────────────────────
def hybrid_retrieve(
    query         : str,
    chat_history  : list = [],
    uploaded_pdfs : list = [],
) -> dict:
    """
    Smart retrieval:
    PDFs uploaded → PDF chunks first
    General       → Local DB + Wikipedia
    Research      → Local DB + Wikipedia + ArXiv
    """
    search_query = extract_search_query(query, chat_history)

    # Step 1: PDF search — if PDFs uploaded
    pdf_docs = []
    if uploaded_pdfs:
        print(f"  📄 PDFs uploaded — searching PDF chunks...")
        pdf_docs = retrieve_pdf_chunks(search_query)

    # Step 2: Local DB
    print(f"  🔍 Searching local DB...")
    local_docs = retrieve(search_query)

    # Step 3: Wikipedia
    wiki_docs = search_wikipedia_live(search_query)

    # Step 4: ArXiv if research
    arxiv_docs = []
    if is_research_query(query):
        print("  🔬 Research query — searching ArXiv...")
        arxiv_docs = search_arxiv_live(search_query)
    else:
        print("  📚 General query — Wikipedia + Local DB")

    # Combine — PDF first
    all_docs = pdf_docs + local_docs + wiki_docs + arxiv_docs

    # Remove duplicates
    seen   = set()
    unique = []
    for doc in all_docs:
        key = doc.page_content[:100]
        if key not in seen:
            seen.add(key)
            unique.append(doc)

    return {
        "local"        : local_docs,
        "pdf"          : pdf_docs,
        "wiki"         : wiki_docs,
        "arxiv"        : arxiv_docs,
        "all"          : unique,
        "is_research"  : is_research_query(query),
        "search_query" : search_query,
    }


# ─── Test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n=== Episteme Retriever Test ===\n")

    print("--- Test 1: General ---")
    r = hybrid_retrieve("How does PID controller work?")
    print(f"Total: {len(r['all'])} | PDF: {len(r['pdf'])} | "
          f"Wiki: {len(r['wiki'])} | ArXiv: {len(r['arxiv'])}\n")

    print("--- Test 2: With PDF ---")
    r = hybrid_retrieve("social media guidelines", uploaded_pdfs=["test.pdf"])
    print(f"Total: {len(r['all'])} | PDF: {len(r['pdf'])} | "
          f"Wiki: {len(r['wiki'])} | ArXiv: {len(r['arxiv'])}")