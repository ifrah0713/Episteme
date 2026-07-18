# ============================================================
# Episteme — Knowledge Base Builder (ingest.py)
# Purpose: Load STEM documents and store in vector database
# Sources: Wikipedia + ArXiv + PubMed
# ============================================================

import time
import requests
import wikipedia
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# ─── Load Environment Variables ───────────────────────────────
load_dotenv()

# ─── Constants ────────────────────────────────────────────────
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE      = 1000
CHUNK_OVERLAP   = 100
CHROMA_DIR      = "./chroma_db"
ARXIV_BASE_URL  = "http://export.arxiv.org/api/query"
PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
PUBMED_MAX_DOCS = 3
ARXIV_MAX_DOCS  = 3
WIKI_RETRIES    = 3
WIKI_RETRY_WAIT = 2  # seconds

STEM_TOPICS = [
    # ── Science ───────────────────────────────────────────────
    "Quantum mechanics",
    "Thermodynamics",
    "Electromagnetism",
    "Optics physics",
    "Nuclear physics",
    "Fluid mechanics",
    "Solid state physics",
    "Astrophysics",
    "Nanotechnology",
    "Photonics",
    # ── Technology ────────────────────────────────────────────
    "Artificial intelligence",
    "Machine learning",
    "Deep learning",
    "Computer vision",
    "Internet of Things",
    "Robotics",
    "Blockchain technology",
    "Cloud computing",
    "Edge computing",
    "Natural language processing",
    "Data science",
    "Augmented reality",
    "Autonomous systems",
    "3D printing",
    # ── Electrical Engineering ─────────────────────────────────
    "Electrical engineering",
    "Power engineering",
    "Electric motor",
    "Transformer",
    "Circuit theory",
    "Digital electronics",
    "Analog electronics",
    "Microelectronics",
    "Semiconductor",
    "VLSI",
    "Power electronics",
    "High voltage",
    "Electric vehicle",
    # ── Electronics Engineering ────────────────────────────────
    "Electronic engineering",
    "Microcontroller",
    "Embedded system",
    "Signal processing",
    "Digital signal processing",
    "Printed circuit board",
    "Sensor",
    "FPGA",
    "Radio frequency",
    "Antenna",
    # ── Mechanical Engineering ─────────────────────────────────
    "Mechanical engineering",
    "Heat transfer",
    "Fluid dynamics",
    "Statics",
    "Dynamics",
    "Machine design",
    "Manufacturing",
    "Materials science",
    "Tribology",
    "Finite element method",
    "Computer-aided design",
    "HVAC",
    "Turbomachinery",
    # ── Civil Engineering ──────────────────────────────────────
    "Civil engineering",
    "Structural engineering",
    "Geotechnical engineering",
    "Transportation engineering",
    "Environmental engineering",
    "Water resources",
    "Construction management",
    "Earthquake engineering",
    "Bridge",
    "Urban planning",
    # ── Avionics ──────────────────────────────────────────────
    "Avionics",
    "Flight management system",
    "Inertial navigation system",
    "Autopilot",
    "Aircraft communication",
    "Radar",
    "Electronic warfare",
    "Automatic test equipment",
    "Aircraft instruments",
    "Glass cockpit",
    # ── Aerospace Engineering ──────────────────────────────────
    "Aerospace engineering",
    "Aircraft design",
    "Flight control",
    "Navigation system",
    "Satellite communication",
    "Unmanned aerial vehicle",
    "Propulsion",
    "Aerodynamics",
    "Rocket engine",
    "Spacecraft",
    "Orbital mechanics",
    "Space exploration",
    "Hypersonic",
    # ── Instrumentation ───────────────────────────────────────
    "Instrumentation",
    "Measurement",
    "Pressure sensor",
    "Temperature sensor",
    "Flow measurement",
    "Strain gauge",
    "Accelerometer",
    "Gyroscope",
    "Transducer",
    "Calibration",
    "Data acquisition",
    # ── Control Systems ───────────────────────────────────────
    "Control system",
    "PID controller",
    "State space",
    "Transfer function",
    "Feedback control",
    "Optimal control",
    "Adaptive control",
    "Robust control",
    "Model predictive control",
    "Nonlinear control",
    # ── Quadcopters & Drones ──────────────────────────────────
    "Quadcopter",
    "Drone",
    "Multirotor",
    "FPV drone",
    "Swarm robotics",
    "Obstacle avoidance",
    # ── Industrial Automation ──────────────────────────────────
    "Industrial automation",
    "Factory automation",
    "Industrial robot",
    "CNC",
    "Machine vision",
    "Predictive maintenance",
    "Industry 4.0",
    "Digital twin",
    # ── SCADA Systems ─────────────────────────────────────────
    "SCADA",
    "Industrial control system",
    "Remote terminal unit",
    "Process control",
    "Distributed control system",
    "Human machine interface",
    # ── PLCs ──────────────────────────────────────────────────
    "Programmable logic controller",
    "Ladder logic",
    "Fieldbus",
    "Modbus",
    "Profibus",
    # ── Communication Systems ──────────────────────────────────
    "Communication systems",
    "Wireless communication",
    "5G",
    "Optical fiber",
    "OFDM",
    "MIMO",
    "Software-defined radio",
    "Cognitive radio",
    "Digital communication",
    "LoRa",
    "Zigbee",
    "Bluetooth",
    # ── Computer Engineering ───────────────────────────────────
    "Computer engineering",
    "Operating system",
    "Computer architecture",
    "Computer network",
    "Database",
    "Software engineering",
    "Compiler",
    "Parallel computing",
    "Quantum computing",
    # ── Chemical Engineering ───────────────────────────────────
    "Chemical engineering",
    "Process engineering",
    "Petrochemical",
    "Polymer",
    "Biomedical engineering",
    # ── Cybersecurity ──────────────────────────────────────────
    "Cybersecurity",
    "Network security",
    "Cryptography",
    "Penetration testing",
    "Information security",
    "Malware",
    "Digital forensics",
    # ── Mathematics ───────────────────────────────────────────
    "Linear algebra",
    "Calculus",
    "Probability",
    "Differential equation",
    "Discrete mathematics",
    "Numerical analysis",
    "Graph theory",
    "Fourier analysis",
    "Laplace transform",
    "Complex analysis",
]


# ─── Initialize Embeddings ────────────────────────────────────
def load_embeddings():
    """Load HuggingFace sentence transformer model."""
    print("Loading embedding model...")
    model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    print("Embedding model loaded ✅")
    return model


# ─── Initialize Text Splitter ─────────────────────────────────
def get_text_splitter():
    """Return configured text splitter."""
    return RecursiveCharacterTextSplitter(
        chunk_size    = CHUNK_SIZE,
        chunk_overlap = CHUNK_OVERLAP,
        separators    = ["\n\n", "\n", ".", " "],
    )


# ─── Load Wikipedia Documents ─────────────────────────────────
def load_wikipedia_docs(topics: list) -> list:
    """Fetch Wikipedia articles with retry logic."""
    docs = []
    wikipedia.set_lang("en")

    for topic in topics:
        for attempt in range(WIKI_RETRIES):
            try:
                print(f"  Fetching Wikipedia: {topic}...")
                page    = wikipedia.page(topic, auto_suggest=False)
                content = page.content[:3000]

                doc = Document(
                    page_content = content,
                    metadata     = {
                        "source" : page.url,
                        "title"  : page.title,
                        "type"   : "wikipedia",
                    },
                )
                docs.append(doc)
                print(f"  ✅ Done: {topic}")
                break  # success — move to next topic

            except Exception as e:
                if attempt < WIKI_RETRIES - 1:
                    print(f"  ⚠️ Retry {attempt + 1}: {topic}")
                    time.sleep(WIKI_RETRY_WAIT)
                else:
                    print(f"  ❌ Failed: {topic} — {e}")

    return docs


# ─── Load ArXiv Documents ─────────────────────────────────────
def load_arxiv_docs(topics: list) -> list:
    """Fetch free research papers from ArXiv API."""
    docs = []

    for topic in topics:
        try:
            print(f"  Fetching ArXiv: {topic}...")
            params = {
                "search_query" : f"ti:{topic}",  # title search — more accurate
                "start"        : 0,
                "max_results"  : ARXIV_MAX_DOCS,
            }
            response = requests.get(
                ARXIV_BASE_URL,
                params  = params,
                timeout = 10,
            )
            content   = response.text
            summaries = []
            parts     = content.split("<summary>")
            for part in parts[1:]:
                summary = part.split("</summary>")[0].strip()
                summaries.append(summary)

            if summaries:
                combined  = f"ArXiv papers on {topic}:\n\n"
                combined += "\n\n".join(summaries[:ARXIV_MAX_DOCS])
                doc = Document(
                    page_content = combined[:3000],
                    metadata     = {
                        "source" : f"https://arxiv.org/search/?query={topic}",
                        "title"  : f"ArXiv: {topic}",
                        "type"   : "arxiv",
                    },
                )
                docs.append(doc)
                print(f"  ✅ Done ArXiv: {topic}")
            else:
                print(f"  ❌ No ArXiv results: {topic}")

            time.sleep(0.5)

        except Exception as e:
            print(f"  ❌ Failed ArXiv: {topic} — {e}")

    return docs


# ─── Load PubMed Documents ────────────────────────────────────
def load_pubmed_docs(topics: list) -> list:
    """Fetch engineering/science abstracts from PubMed API."""
    docs = []

    for topic in topics:
        try:
            print(f"  Fetching PubMed: {topic}...")
            search_params = {
                "db"      : "pubmed",
                "term"    : topic,
                "retmax"  : PUBMED_MAX_DOCS,
                "retmode" : "json",
            }
            search_res = requests.get(
                f"{PUBMED_BASE_URL}esearch.fcgi",
                params  = search_params,
                timeout = 10,
            )
            ids = search_res.json()["esearchresult"]["idlist"]

            if not ids:
                print(f"  ❌ No PubMed results: {topic}")
                continue

            fetch_params = {
                "db"      : "pubmed",
                "id"      : ",".join(ids),
                "rettype" : "abstract",
                "retmode" : "text",
            }
            fetch_res = requests.get(
                f"{PUBMED_BASE_URL}efetch.fcgi",
                params  = fetch_params,
                timeout = 10,
            )
            content = fetch_res.text[:3000]
            doc = Document(
                page_content = content,
                metadata     = {
                    "source" : f"https://pubmed.ncbi.nlm.nih.gov/?term={topic}",
                    "title"  : f"PubMed: {topic}",
                    "type"   : "pubmed",
                },
            )
            docs.append(doc)
            print(f"  ✅ Done PubMed: {topic}")

        except Exception as e:
            print(f"  ❌ Failed PubMed: {topic} — {e}")

    return docs


# ─── Build Vector Store ───────────────────────────────────────
def build_vectorstore(docs: list, embeddings) -> Chroma:
    """Split documents into chunks and store in ChromaDB."""
    splitter = get_text_splitter()
    chunks   = splitter.split_documents(docs)
    print(f"\nChunks created: {len(chunks)} ✅")

    print("Storing in ChromaDB...")
    vectorstore = Chroma.from_documents(
        documents         = chunks,
        embedding         = embeddings,
        persist_directory = CHROMA_DIR,
    )
    print("Knowledge base saved ✅")
    return vectorstore


# ─── Main ─────────────────────────────────────────────────────
def main():
    print("\n=== Episteme — STEM Knowledge Base Builder ===\n")

    embeddings = load_embeddings()

    print("\n--- Wikipedia ---")
    wiki_docs = load_wikipedia_docs(STEM_TOPICS)

    print("\n--- ArXiv Research Papers ---")
    arxiv_docs = load_arxiv_docs(STEM_TOPICS)

    print("\n--- PubMed Engineering Papers ---")
    pubmed_docs = load_pubmed_docs(STEM_TOPICS)

    all_docs = wiki_docs + arxiv_docs + pubmed_docs
    print(f"\nTotal documents loaded : {len(all_docs)}")
    print(f"  Wikipedia            : {len(wiki_docs)}")
    print(f"  ArXiv                : {len(arxiv_docs)}")
    print(f"  PubMed               : {len(pubmed_docs)}")

    if all_docs:
        build_vectorstore(all_docs, embeddings)
        print("\n=== Knowledge Base Ready! ===\n")
    else:
        print("\nNo documents loaded. Check internet connection.")


if __name__ == "__main__":
    main()