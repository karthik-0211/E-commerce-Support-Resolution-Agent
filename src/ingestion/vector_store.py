"""Vector database setup and retrieval"""
import os
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple

class PolicyVectorStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.embeddings_dir = os.path.join(persist_directory, "embeddings")
        os.makedirs(self.embeddings_dir, exist_ok=True)
        
        print("Loading embeddings model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.chunks = []
        self.embeddings = None
    
    def create_index(self, chunks: List[Dict]):
        """Create vector index"""
        if not chunks:
            print("No chunks to index")
            return
        
        print(f"\nCreating vector index with {len(chunks)} chunks...")
        self.chunks = chunks
        
        # Create embeddings
        texts = [chunk["content"] for chunk in chunks]
        print("  Generating embeddings...")
        self.embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Save chunks and embeddings
        with open(os.path.join(self.embeddings_dir, "chunks.pkl"), 'wb') as f:
            pickle.dump(self.chunks, f)
        
        np.save(os.path.join(self.embeddings_dir, "embeddings.npy"), self.embeddings)
        
        print(f"✓ Created index with {len(self.chunks)} vectors")
    
    def load_index(self):
        """Load existing index"""
        chunks_path = os.path.join(self.embeddings_dir, "chunks.pkl")
        embeddings_path = os.path.join(self.embeddings_dir, "embeddings.npy")
        
        if not os.path.exists(chunks_path) or not os.path.exists(embeddings_path):
            return False
        
        with open(chunks_path, 'rb') as f:
            self.chunks = pickle.load(f)
        
        self.embeddings = np.load(embeddings_path)
        print(f"✓ Loaded index with {len(self.chunks)} vectors")
        return True
    
    def retrieve(self, query: str, k: int = 5, score_threshold: float = 0.3) -> List[Tuple[Dict, float]]:
        """Retrieve relevant policy chunks"""
        if self.embeddings is None:
            if not self.load_index():
                return []
        
        # Encode query
        query_embedding = self.model.encode([query])[0]
        
        # Compute cosine similarity
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:k]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= score_threshold:
                results.append((self.chunks[idx], score))
        
        if not results:
            print(f"Warning: No results above threshold {score_threshold} for query: {query[:100]}")
        
        return results