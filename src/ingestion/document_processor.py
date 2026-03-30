"""Document processing and chunking strategy"""
import os
from typing import List, Dict

class PolicyDocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def load_policies(self, policies_dir: str) -> List[Dict]:
        """Load all policy documents from directory"""
        documents = []
        
        if not os.path.exists(policies_dir):
            print(f"Directory not found: {policies_dir}")
            return documents
        
        for filename in sorted(os.listdir(policies_dir)):
            if filename.endswith('.txt'):
                filepath = os.path.join(policies_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if not content.strip():
                        continue
                    
                    doc = {
                        "content": content,
                        "metadata": {
                            "source": filename,
                            "doc_type": "policy",
                            "section": self._extract_section_title(content),
                            "word_count": len(content.split())
                        }
                    }
                    documents.append(doc)
                    print(f"  ✓ Loaded: {filename} ({len(content.split()):,} words)")
                    
                except Exception as e:
                    print(f"  ✗ Error loading {filename}: {e}")
        
        return documents
    
    def _extract_section_title(self, content: str) -> str:
        lines = content.split('\n')
        for line in lines[:20]:
            if line.startswith('#') or line.startswith('##'):
                return line.strip('# ').strip()
        return "General Policy"
    
    def chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        """Split documents into chunks with metadata preservation"""
        chunked_docs = []
        
        for doc in documents:
            content = doc["content"]
            metadata = doc["metadata"]
            
            # Simple chunking by paragraphs
            paragraphs = content.split('\n\n')
            current_chunk = ""
            chunks = []
            
            for para in paragraphs:
                if len(current_chunk) + len(para) < self.chunk_size:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para + "\n\n"
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            for i, chunk_content in enumerate(chunks):
                chunked_docs.append({
                    "content": chunk_content,
                    "metadata": {
                        **metadata,
                        "chunk_id": i,
                        "total_chunks": len(chunks),
                        "chunk_size": len(chunk_content)
                    }
                })
            
            print(f"  Chunked {metadata['source']}: {len(chunks)} chunks")
        
        if chunked_docs:
            avg_size = sum(len(c["content"]) for c in chunked_docs) / len(chunked_docs)
            print(f"\n✓ Created {len(chunked_docs)} chunks (avg {avg_size:.0f} chars)")
        
        return chunked_docs