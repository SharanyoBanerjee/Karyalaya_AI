"""
Local RAG Ingestion Pipeline for Sovereign AI Workbench.
Ingests plant SOPs and manuals into Chroma vector database.
Strictly offline, file-based vector storage.
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


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """Splits text into paragraphs and manageable text chunks."""
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


def ingest_sops() -> Dict[str, Any]:
    """Ingests all SOP files from workspace/sops/ into Chroma vector store."""
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(name="sovereign_sops")

        sop_files = glob.glob(os.path.join(SOPS_DIR, "*.txt")) + glob.glob(os.path.join(SOPS_DIR, "*.md"))
        if not sop_files:
            return {"status": "warning", "message": f"No SOP files found in {SOPS_DIR}"}

        total_chunks = 0
        documents = []
        metadatas = []
        ids = []

        for file_path in sop_files:
            filename = os.path.basename(file_path)
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            chunks = chunk_text(content)
            for idx, chunk in enumerate(chunks):
                chunk_id = f"{filename}_chunk_{idx}"
                documents.append(chunk)
                metadatas.append({"source": filename, "chunk_index": idx})
                ids.append(chunk_id)
                total_chunks += 1

        if documents:
            # Upsert into Chroma
            collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

        return {
            "status": "success",
            "files_processed": len(sop_files),
            "total_chunks_ingested": total_chunks,
            "vector_store_path": VECTOR_DB_DIR
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    res = ingest_sops()
    print("Ingestion Result:", res)
