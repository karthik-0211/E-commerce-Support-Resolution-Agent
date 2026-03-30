"""Agent 2: Retrieves relevant policy excerpts with citations"""
from typing import List, Dict
from src.ingestion.vector_store import PolicyVectorStore

class PolicyRetrieverAgent:
    def __init__(self, vector_store: PolicyVectorStore):
        self.vector_store = vector_store
    
    def retrieve(self, query: str, metadata_filters: Dict = None, top_k: int = 5) -> List[Dict]:
        enhanced_query = self._construct_query(query, metadata_filters)
        results = self.vector_store.retrieve(enhanced_query, k=top_k)
        
        formatted_results = []
        for chunk, score in results:
            formatted_results.append({
                "content": chunk["content"],
                "citation": self._format_citation(chunk["metadata"]),
                "source": chunk["metadata"].get("source", "Unknown"),
                "section": chunk["metadata"].get("section", "General"),
                "relevance_score": score
            })
        
        return formatted_results
    
    def _construct_query(self, original_query: str, filters: Dict = None) -> str:
        query_parts = [original_query]
        if filters:
            if filters.get("item_category"):
                query_parts.append(f"category: {filters['item_category']}")
            if filters.get("issue_type"):
                query_parts.append(f"policy type: {filters['issue_type']}")
        return " ".join(query_parts)
    
    def _format_citation(self, metadata: Dict) -> str:
        source = metadata.get("source", "Unknown Policy")
        section = metadata.get("section", "")
        chunk_id = metadata.get("chunk_id", 0)
        
        if section:
            return f"{source} - Section: {section} (Chunk {chunk_id})"
        return f"{source} (Chunk {chunk_id})"