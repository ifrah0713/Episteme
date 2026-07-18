# ============================================================
# Episteme — PDF Loader (pdf_loader.py)
# Purpose: Load and process uploaded PDF files into ChromaDB
# ============================================================

import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# ─── Constants ────────────────────────────────────────────────
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE      = 1000
CHUNK_OVERLAP   = 100
CHROMA_DIR      = "./chroma_db"


# ─── Load Embeddings ──────────────────────────────────────────
def get_embeddings():
    """Load HuggingFace embedding model."""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


# ─── Delete Existing PDF Chunks ───────────────────────────────
def delete_pdf_chunks(filename: str):
    """Delete existing chunks for a PDF before re-adding."""
    try:
        embeddings  = get_embeddings()
        vectorstore = Chroma(
            persist_directory  = CHROMA_DIR,
            embedding_function = embeddings,
        )
        results = vectorstore.get(
            where = {"filename": filename}
        )
        if results["ids"]:
            vectorstore.delete(ids=results["ids"])
            print(f"  Deleted {len(results['ids'])} old chunks for {filename}")
    except Exception as e:
        print(f"  No existing chunks to delete: {e}")


# ─── Process Uploaded PDF ─────────────────────────────────────
def process_pdf(uploaded_file) -> dict:
    """
    Process a Streamlit uploaded PDF file.
    Save → Load → Split → Store in ChromaDB.
    """
    try:
        # Step 1: Delete old chunks for this PDF
        delete_pdf_chunks(uploaded_file.name)

        # Step 2: Save to temp file
        with tempfile.NamedTemporaryFile(
            delete = False,
            suffix = ".pdf",
        ) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        # Step 3: Load all pages
        loader = PyPDFLoader(tmp_path)
        pages  = loader.load()

        # Step 4: Add metadata to each page
        for page in pages:
            page.metadata["source"]   = uploaded_file.name
            page.metadata["filename"] = uploaded_file.name
            page.metadata["type"]     = "pdf"
            page.metadata["title"]    = uploaded_file.name.replace(".pdf", "")

        # Step 5: Split into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size    = CHUNK_SIZE,
            chunk_overlap = CHUNK_OVERLAP,
            separators    = ["\n\n", "\n", ".", " "],
        )
        chunks = splitter.split_documents(pages)

        # Step 6: Store in ChromaDB
        embeddings  = get_embeddings()
        vectorstore = Chroma(
            persist_directory  = CHROMA_DIR,
            embedding_function = embeddings,
        )
        vectorstore.add_documents(chunks)

        # Step 7: Cleanup temp file
        os.unlink(tmp_path)

        return {
            "success"  : True,
            "pages"    : len(pages),
            "chunks"   : len(chunks),
            "filename" : uploaded_file.name,
        }

    except Exception as e:
        return {
            "success" : False,
            "error"   : str(e),
        }
    