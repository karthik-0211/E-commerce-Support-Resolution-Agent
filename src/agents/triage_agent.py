"""Agent 1: Classifies and identifies missing information"""
from typing import Dict
from google import genai
import json

class TriageAgent:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        # Use available model from the list
        self.model_name = "gemini-2.0-flash"  # or "gemini-2.5-flash"
    
    def analyze(self, ticket_text: str, order_context: Dict) -> Dict:
        prompt = f"""You are a customer support triage specialist. Analyze the ticket and return JSON only.

Issue types: refund, shipping, payment, promo, fraud, other

Return format:
{{
    "issue_type": "refund|shipping|payment|promo|fraud|other",
    "confidence": 0.0-1.0,
    "missing_fields": [],
    "clarifying_questions": [],
    "needs_human_review": false,
    "key_entities": {{}}
}}

Ticket: {ticket_text}
Order Context: {json.dumps(order_context, indent=2)}"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            result = response.text
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return self._fallback_classification(ticket_text, order_context)
        
        try:
            if '```json' in result:
                result = result.split('```json')[1].split('```')[0]
            elif '```' in result:
                result = result.split('```')[1].split('```')[0]
            
            classification = json.loads(result.strip())
        except:
            classification = self._fallback_classification(ticket_text, order_context)
        
        return classification
    
    def _fallback_classification(self, ticket_text: str, order_context: Dict) -> Dict:
        """Fallback classification when API fails"""
        ticket_lower = ticket_text.lower()
        
        if any(term in ticket_lower for term in ['refund', 'return', 'keep']):
            issue_type = "refund"
            confidence = 0.8
        elif any(term in ticket_lower for term in ['shipping', 'delivered', 'lost', 'package']):
            issue_type = "shipping"
            confidence = 0.8
        elif any(term in ticket_lower for term in ['coupon', 'code', 'promo']):
            issue_type = "promo"
            confidence = 0.8
        else:
            issue_type = "other"
            confidence = 0.5
        
        if order_context.get('item_category') == 'perishable':
            confidence = 0.9
        
        return {
            "issue_type": issue_type,
            "confidence": confidence,
            "missing_fields": [],
            "clarifying_questions": [],
            "needs_human_review": False,
            "key_entities": {}
        }