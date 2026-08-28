"""
Local RAG Ingestion Pipeline for Karyalaya AI.
Ingests plant SOPs (TXT, MD, PDF) into the local Chroma vector database.
Strictly offline — no network calls, no cloud storage.
"""

import os
import glob
import chromadb
from typing import Dict, Any, List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOPS_DIR = os.path.join(BASE_DIR, "workspace", "sops")
VECTOR_DB_DIR = os.path.join(os.path.dirname(__file__), "vector_store")


def get_chroma_client():
    """Initializes local persistent Chroma DB client."""
    os.makedirs(VECTOR_DB_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=VECTOR_DB_DIR)


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extracts plain text from a PDF using PyMuPDF.
    Falls back to an empty string on any extraction error.
    """
    try:
        import pymupdf  # PyMuPDF >= 1.24
        text_parts = []
        with pymupdf.open(file_path) as doc:
            for page in doc:
                text_parts.append(page.get_text())
        return "\n\n".join(text_parts).strip()
    except Exception as e:
        print(f"[INGEST WARNING] PDF extraction failed for {file_path}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """Splits text into paragraphs and overlapping text chunks for RAG retrieval."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""

    for p in paragraphs:
        if len(current_chunk) + len(p) <= chunk_size:
            current_chunk += ("\n\n" + p) if current_chunk else p
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = p

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [text]


def ingest_sops(sops_dir: str = None) -> Dict[str, Any]:
    """
    Ingests all SOP files from workspace/sops/ into local Chroma vector store.

    Supports: .txt, .md, .pdf
    Safe to call repeatedly — uses upsert so duplicate chunk IDs are updated, not doubled.

    Args:
        sops_dir: Optional override for the SOP directory path. Defaults to workspace/sops/.
    """
    source_dir = sops_dir or SOPS_DIR
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(name="karyalaya_sops")

        txt_files = glob.glob(os.path.join(source_dir, "*.txt"))
        md_files  = glob.glob(os.path.join(source_dir, "*.md"))
        pdf_files = glob.glob(os.path.join(source_dir, "*.pdf"))
        sop_files = txt_files + md_files + pdf_files

        if not sop_files:
            return {
                "status": "warning",
                "message": f"No SOP files (.txt, .md, .pdf) found in {source_dir}"
            }

        total_chunks = 0
        files_processed = 0
        documents = []
        metadatas = []
        ids = []

        for file_path in sop_files:
            filename = os.path.basename(file_path)
            ext = os.path.splitext(filename)[1].lower()

            if ext == ".pdf":
                content = extract_text_from_pdf(file_path)
                if not content:
                    print(f"[INGEST WARNING] Skipping {filename}: empty text after PDF extraction.")
                    continue
            else:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

            chunks = chunk_text(content)
            for idx, chunk in enumerate(chunks):
                # Chunk IDs are deterministic so re-ingestion safely upserts
                chunk_id = f"{filename}_chunk_{idx}"
                documents.append(chunk)
                metadatas.append({"source": filename, "chunk_index": idx})
                ids.append(chunk_id)
                total_chunks += 1

            files_processed += 1
            print(f"[INGEST] {filename} — {len(chunks)} chunks")

        if documents:
            collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

        return {
            "status": "success",
            "files_processed": files_processed,
            "total_chunks_ingested": total_chunks,
            "vector_store_path": VECTOR_DB_DIR
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    res = ingest_sops()
    print("Ingestion Result:", res)
