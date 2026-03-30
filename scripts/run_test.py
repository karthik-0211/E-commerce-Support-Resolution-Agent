"""Run a single test case"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.orchestration.support_orchestrator import SupportOrchestrator
import os
from dotenv import load_dotenv
import json

load_dotenv()

def main():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set in .env file")
        print("Create .env file with: GOOGLE_API_KEY=your_key_here")
        return
    
    orchestrator = SupportOrchestrator(api_key)
    
    ticket = "My order arrived late and the cookies are melted. I want a full refund and to keep the item."
    
    order_context = {
        "order_date": "2024-03-01",
        "delivery_date": "2024-03-08",
        "item_category": "perishable",
        "fulfillment_type": "first_party",
        "shipping_region": "US-CA",
        "order_status": "delivered"
    }
    
    print("\n" + "="*60)
    print("SUPPORT TICKET")
    print("="*60)
    print(f"Ticket: {ticket}")
    print(f"\nOrder Context: {json.dumps(order_context, indent=2)}")
    
    result = orchestrator.process_ticket(ticket, order_context)
    
    print("\n" + "="*60)
    print("FINAL OUTPUT")
    print("="*60)
    
    print(f"\n1. CLASSIFICATION: {result['classification']['issue_type']}")
    print(f"   Confidence: {result['classification']['confidence']:.2f}")
    
    print(f"\n2. DECISION: {result['resolution']['decision'].upper()}")
    
    print(f"\n3. RATIONALE: {result['resolution']['rationale']}")
    
    print(f"\n4. CITATIONS:\n{result['citation_list']}")
    
    print(f"\n5. CUSTOMER RESPONSE:\n{result['resolution']['customer_response']}")
    
    print(f"\n6. COMPLIANCE: {'✓ PASSED' if result['compliance']['is_compliant'] else '✗ FAILED'}")

if __name__ == "__main__":
    main()