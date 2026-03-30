"""Main orchestrator that coordinates all agents"""
from typing import Dict, List
from src.ingestion.vector_store import PolicyVectorStore
from src.agents.triage_agent import TriageAgent
from src.agents.policy_retriever import PolicyRetrieverAgent
from src.agents.resolution_writer import ResolutionWriterAgent
from src.agents.compliance_agent import ComplianceAgent

class SupportOrchestrator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.vector_store = PolicyVectorStore()
        self.triage_agent = TriageAgent(api_key)
        self.policy_retriever = PolicyRetrieverAgent(self.vector_store)
        self.resolution_writer = ResolutionWriterAgent(api_key)
        self.compliance_agent = ComplianceAgent(api_key)
        
        try:
            if self.vector_store.load_index():
                print("✓ Vector store loaded")
            else:
                print("⚠ Vector store not found. Run ingestion first.")
        except:
            print("⚠ Vector store not found. Run ingestion first.")
    
    def process_ticket(self, ticket_text: str, order_context: Dict) -> Dict:
        print("\n" + "="*60)
        print("PROCESSING TICKET")
        print("="*60)
        
        # Step 1: Triage
        print("\n[1/4] Triaging ticket...")
        classification = self.triage_agent.analyze(ticket_text, order_context)
        print(f"✓ Issue: {classification['issue_type']} ({classification['confidence']:.2f})")
        
        if classification.get('clarifying_questions'):
            return {
                "status": "needs_clarification",
                "classification": classification,
                "clarifying_questions": classification['clarifying_questions']
            }
        
        # Step 2: Retrieve policies
        print("\n[2/4] Retrieving policies...")
        query = f"{classification['issue_type']} {ticket_text[:200]}"
        policy_evidence = self.policy_retriever.retrieve(query, top_k=5)
        print(f"✓ Retrieved {len(policy_evidence)} policy chunks")
        
        if len(policy_evidence) == 0:
            return {
                "status": "needs_escalation",
                "reason": "No relevant policy found",
                "classification": classification
            }
        
        # Step 3: Write resolution
        print("\n[3/4] Drafting resolution...")
        resolution = self.resolution_writer.draft_resolution(
            ticket_text, order_context, classification, policy_evidence
        )
        print(f"✓ Decision: {resolution.get('decision', 'unknown')}")
        
        # Step 4: Compliance check
        print("\n[4/4] Running compliance checks...")
        compliance = self.compliance_agent.validate(resolution, policy_evidence, ticket_text)
        
        if compliance['is_compliant']:
            print("✓ Compliance PASSED")
        else:
            print(f"⚠ Compliance FAILED - {len(compliance['issues'])} issues")
            for issue in compliance['issues']:
                print(f"  - {issue}")
            
            if compliance.get('needs_rewrite', False):
                print("  → Triggering rewrite...")
        
        # Compile final output
        output = {
            "status": "completed",
            "classification": classification,
            "resolution": resolution,
            "compliance": compliance,
            "citations": [e['citation'] for e in policy_evidence],
            "citation_list": self._format_citations(policy_evidence)
        }
        
        return output
    
    def _format_citations(self, evidence: List[Dict]) -> str:
        """Format citations for final output"""
        citations = []
        for e in evidence:
            citations.append(f"- {e['citation']} (score: {e['relevance_score']:.2f})")
        return "\n".join(citations)