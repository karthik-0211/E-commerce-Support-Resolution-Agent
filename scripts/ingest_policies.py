"""Run once to ingest all policy documents"""
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.ingestion.document_processor import PolicyDocumentProcessor
from src.ingestion.vector_store import PolicyVectorStore

def main():
    print("="*60)
    print("INGESTING POLICY DOCUMENTS")
    print("="*60)
    
    policies_dir = "data/policies"
    if not os.path.exists(policies_dir):
        print(f"❌ Policy directory not found: {policies_dir}")
        return
    
    policy_files = [f for f in os.listdir(policies_dir) if f.endswith('.txt')]
    if not policy_files:
        print(f"❌ No policy files found")
        return
    
    print(f"Found {len(policy_files)} policy files")
    
    processor = PolicyDocumentProcessor(chunk_size=1000, chunk_overlap=200)
    documents = processor.load_policies(policies_dir)
    
    if len(documents) == 0:
        print("❌ No documents loaded")
        return
    
    total_words = sum(doc["metadata"]["word_count"] for doc in documents)
    print(f"\n✓ Loaded {len(documents)} documents")
    print(f"  Total words: {total_words:,}")
    
    chunked_docs = processor.chunk_documents(documents)
    
    vector_store = PolicyVectorStore()
    vector_store.create_index(chunked_docs)
    
    print("\n✅ Ingestion complete!")
    print(f"  Chunks: {len(chunked_docs)}")
    print(f"  Vector store: chroma_db/")

if __name__ == "__main__":
    main()