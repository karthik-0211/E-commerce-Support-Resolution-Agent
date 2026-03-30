# scripts/evaluate.py
"""Evaluation script for 20 test cases"""
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.orchestration.support_orchestrator import SupportOrchestrator
import os
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

def evaluate():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set")
        return
    
    orchestrator = SupportOrchestrator(api_key)
    
    # Load test tickets
    with open('data/test_tickets.json', 'r') as f:
        test_cases = json.load(f)
    
    results = []
    citation_coverage = []
    unsupported_claims = []
    correct_escalations = 0
    
    print("\n" + "="*80)
    print("EVALUATING 20 TEST CASES")
    print("="*80)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] Testing {test['id']}...")
        
        try:
            output = orchestrator.process_ticket(test['ticket'], test['order_context'])
            
            # Metrics
            has_citations = len(output.get('citations', [])) > 0
            citation_coverage.append(1 if has_citations else 0)
            
            # Check for unsupported claims
            has_unsupported = output.get('compliance', {}).get('hallucination_score', 0) > 0.1
            unsupported_claims.append(1 if has_unsupported else 0)
            
            # Check escalation correctness
            expected = test['expected_outcome']
            actual = output.get('resolution', {}).get('decision', 'unknown')
            
            if expected in ['escalate_guarantee', 'approve_14_day', 'approve_CA_law']:
                expected_escalation = True
            else:
                expected_escalation = False
            
            actual_escalation = (actual == 'needs_escalation')
            
            if expected_escalation == actual_escalation:
                correct_escalations += 1
            
            results.append({
                'id': test['id'],
                'expected': expected,
                'actual': actual,
                'citations': has_citations,
                'unsupported': has_unsupported,
                'compliant': output.get('compliance', {}).get('is_compliant', False)
            })
            
            print(f"  ✓ Decision: {actual} | Citations: {has_citations} | Compliant: {output.get('compliance', {}).get('is_compliant', False)}")
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            results.append({
                'id': test['id'],
                'error': str(e)
            })
    
    # Calculate metrics
    total_tests = len([r for r in results if 'error' not in r])
    citation_rate = sum(citation_coverage) / total_tests if total_tests > 0 else 0
    unsupported_rate = sum(unsupported_claims) / total_tests if total_tests > 0 else 0
    escalation_rate = correct_escalations / total_tests if total_tests > 0 else 0
    
    # Display results
    print("\n" + "="*80)
    print("EVALUATION RESULTS")
    print("="*80)
    
    print("\n📊 METRICS:")
    print(f"  Citation Coverage Rate: {citation_rate:.1%}")
    print(f"  Unsupported Claim Rate: {unsupported_rate:.1%}")
    print(f"  Correct Escalation Rate: {escalation_rate:.1%}")
    
    print("\n📋 DETAILED RESULTS:")
    table_data = [[r['id'], r.get('expected', 'N/A'), r.get('actual', 'ERROR'), 
                   '✓' if r.get('citations') else '✗', 
                   '✓' if not r.get('unsupported') else '✗']
                  for r in results if 'error' not in r]
    print(tabulate(table_data, headers=['ID', 'Expected', 'Actual', 'Citations', 'No Hallucination']))
    
    # Example runs (3 specific cases)
    print("\n" + "="*80)
    print("EXAMPLE RUN 1: Exception Case (Melted Cookies)")
    print("="*80)
    exception_case = next(t for t in test_cases if t['id'] == 'EXC_001')
    output1 = orchestrator.process_ticket(exception_case['ticket'], exception_case['order_context'])
    print("\nCustomer Response:")
    print(output1.get('resolution', {}).get('customer_response', 'N/A')[:500])
    
    print("\n" + "="*80)
    print("EXAMPLE RUN 2: Conflict Case (Marketplace Seller Dispute)")
    print("="*80)
    conflict_case = next(t for t in test_cases if t['id'] == 'CON_001')
    output2 = orchestrator.process_ticket(conflict_case['ticket'], conflict_case['order_context'])
    print("\nDecision:", output2.get('resolution', {}).get('decision'))
    print("\nCitations:")
    print(output2.get('citation_list', 'N/A'))
    
    print("\n" + "="*80)
    print("EXAMPLE RUN 3: Not-in-Policy (Price Match After Purchase)")
    print("="*80)
    nip_case = next(t for t in test_cases if t['id'] == 'NIP_001')
    output3 = orchestrator.process_ticket(nip_case['ticket'], nip_case['order_context'])
    print("\nRationale:")
    print(output3.get('resolution', {}).get('rationale', 'N/A'))

if __name__ == "__main__":
    evaluate()