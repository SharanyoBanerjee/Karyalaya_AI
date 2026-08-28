"""
Document Search (RAG) Tool for Karyalaya AI.
Queries the local Chroma vector database for grounded SOP & manual information.
Strictly local retrieval, no cloud embeddings.
"""

import os
import chromadb
from typing import Dict, Any, List

VECTOR_DB_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "knowledge_base", "vector_store")
)


def search_knowledge_base(query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Queries Chroma vector DB for documents matching the query.
    Returns matched SOP clauses and relevance scores.
    """
    try:
        if not os.path.exists(VECTOR_DB_DIR):
            return {
                "status": "error",
                "error": f"Vector database directory not found at {VECTOR_DB_DIR}. Run ingest_pipeline.py first."
            }

        client = chromadb.PersistentClient(path=VECTOR_DB_DIR)
        
        try:
            collection = client.get_collection(name="karyalaya_sops")
        except Exception:
            try:
                collection = client.get_collection(name="sovereign_sops")
            except Exception:
                return {
                    "status": "warning",
                    "message": "SOP collection not populated yet. Run ingest_pipeline.py.",
                    "results": []
                }

        count = collection.count()
        if count == 0:
            return {
                "status": "warning",
                "message": "SOP collection is empty.",
                "results": []
            }

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, count)
        )

        matched_docs = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0] if results.get("distances") else []

            for i in range(len(docs)):
                doc_item = {
                    "content": docs[i],
                    "source": metas[i].get("source", "Unknown") if i < len(metas) else "Unknown",
                    "chunk_index": metas[i].get("chunk_index", 0) if i < len(metas) else 0,
                    "distance": distances[i] if i < len(distances) else None
                }
                matched_docs.append(doc_item)

        return {
            "status": "success",
            "query": query,
            "count": len(matched_docs),
            "results": matched_docs
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    res = search_knowledge_base("approval note format pressure testing requirements")
    print("Search Results:", res)
