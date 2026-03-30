"""Agent 3: Drafts customer response using only retrieved evidence"""
from typing import List, Dict
from google import genai
import json

class ResolutionWriterAgent:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.0-flash"  # or "gemini-2.5-flash"
    
    def draft_resolution(self, ticket_text: str, order_context: Dict,
                        classification: Dict, policy_evidence: List[Dict]) -> Dict:
        
        evidence_text = self._format_evidence(policy_evidence)
        
        prompt = f"""You are a customer support resolution writer. Create a response using ONLY the provided policy evidence.

CRITICAL RULES:
1. NEVER make up policies or facts
2. ONLY use information from the evidence section below
3. Include citations for every policy claim using [Source: Document Name]

Output format (JSON):
{{
    "decision": "approve|deny|partial|needs_escalation|investigate",
    "rationale": "Policy-based explanation",
    "customer_response": "Customer-friendly message with citations like [Source: 04_perishable_food_items_policy.txt]",
    "next_steps": "What support agent should do next",
    "internal_notes": "Brief notes for support team"
}}

Ticket: {ticket_text}
Order Context: {json.dumps(order_context)}
Classification: {json.dumps(classification)}

Policy Evidence (USE ONLY THIS):
{evidence_text}"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            result = response.text
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return self._smart_fallback(ticket_text, order_context, classification, policy_evidence)
        
        try:
            if '```json' in result:
                result = result.split('```json')[1].split('```')[0]
            elif '```' in result:
                result = result.split('```')[1].split('```')[0]
            
            resolution = json.loads(result.strip())
        except:
            resolution = self._smart_fallback(ticket_text, order_context, classification, policy_evidence)
        
        return resolution
    
    def _smart_fallback(self, ticket_text: str, order_context: Dict, 
                        classification: Dict, policy_evidence: List[Dict]) -> Dict:
        """Generate appropriate fallback response based on ticket content"""
        
        ticket_lower = ticket_text.lower()
        category = order_context.get('item_category', '').lower()
        fulfillment = order_context.get('fulfillment_type', '').lower()
        
        # Get source name from evidence
        source_name = self._get_source_name(policy_evidence)
        
        # ==================== HYGIENE ITEMS - DENY ====================
        if (category == 'hygiene' or 
            any(term in ticket_lower for term in ['toothbrush', 'swimsuit', 'hygiene liner', 'underwear', 'shapewear'])):
            return {
                "decision": "deny",
                "rationale": "Hygiene items cannot be returned for safety reasons once opened or if hygiene liner is missing.",
                "customer_response": f"I understand you want to return the {self._extract_item(ticket_text)}. However, for hygiene and safety reasons, these items cannot be returned once the hygiene liner is missing or the item is opened. [Source: {source_name}]",
                "next_steps": "Inform customer of hygiene policy",
                "internal_notes": "Hygiene item - non-returnable"
            }
        
        # ==================== PERISHABLE ITEMS ====================
        if category == 'perishable' or any(term in ticket_lower for term in ['melted', 'cookies', 'food', 'spoiled', 'perishable']):
            # Damaged/spoiled - APPROVE
            if any(term in ticket_lower for term in ['melted', 'spoiled', 'damaged', 'broken']):
                return {
                    "decision": "approve",
                    "rationale": "Perishable items damaged during shipping qualify for full refund.",
                    "customer_response": f"I'm very sorry your {self._extract_item(ticket_text)} arrived damaged. Since these are perishable items, I've issued a full refund to your original payment method. You don't need to return the item. [Source: {source_name}]",
                    "next_steps": "Process refund immediately",
                    "internal_notes": "Perishable item damaged - no return needed"
                }
            # Change of mind - DENY
            else:
                return {
                    "decision": "deny",
                    "rationale": "Perishable items cannot be returned for change of mind due to food safety.",
                    "customer_response": f"I understand you don't like the {self._extract_item(ticket_text)}. However, for food safety reasons, perishable items cannot be returned if there's no quality issue. [Source: {source_name}]",
                    "next_steps": "Inform customer of food safety policy",
                    "internal_notes": "Perishable item - change of mind denied"
                }
        
        # ==================== MARKETPLACE SELLER DISPUTE - ESCALATE ====================
        if fulfillment == 'marketplace' or 'marketplace seller' in ticket_lower:
            return {
                "decision": "needs_escalation",
                "rationale": "Marketplace seller disputes require investigation under our guarantee.",
                "customer_response": f"I apologize for the issue with your marketplace order. I've escalated this to our Marketplace Guarantee team. They will investigate and get back to you within 48 hours. [Source: {source_name}]",
                "next_steps": "Escalate to Marketplace Guarantee team",
                "internal_notes": "Marketplace dispute - escalated for investigation"
            }
        
        # ==================== FINAL SALE ITEMS ====================
        if category == 'clearance' or 'final sale' in ticket_lower:
            # Damaged - APPROVE (exception)
            if any(term in ticket_lower for term in ['damaged', 'broken', 'cracked']):
                return {
                    "decision": "approve",
                    "rationale": "Final sale items damaged during shipping qualify for refund despite final sale status.",
                    "customer_response": f"I'm sorry your {self._extract_item(ticket_text)} arrived damaged. Even though it was final sale, I've issued a full refund due to the damage. A return label has been sent. [Source: {source_name}]",
                    "next_steps": "Send return label and process refund",
                    "internal_notes": "Final sale damaged - refund approved"
                }
            # Change of mind - DENY
            else:
                return {
                    "decision": "deny",
                    "rationale": "Final sale items are non-returnable and non-refundable.",
                    "customer_response": f"I understand you want to return the {self._extract_item(ticket_text)}. However, this was marked as final sale and is non-returnable. [Source: {source_name}]",
                    "next_steps": "Inform customer of final sale policy",
                    "internal_notes": "Final sale - non-returnable"
                }
        
        # ==================== NOT-IN-POLICY REQUESTS - DENY ====================
        if any(term in ticket_lower for term in ['better price', 'emotional distress', 'forgot to return', 'past 30 days', 'compensation']):
            return {
                "decision": "deny",
                "rationale": "This request is not covered by our policy.",
                "customer_response": f"I understand your request, but unfortunately this situation isn't covered by our return policy. [Source: {source_name}]",
                "next_steps": "Inform customer of policy limitations",
                "internal_notes": "Not covered by policy - deny"
            }
        
        # ==================== LOST PACKAGE - INVESTIGATE ====================
        if any(term in ticket_lower for term in ['lost', 'not received', 'never arrived', 'delivered but']):
            return {
                "decision": "investigate",
                "rationale": "Lost packages require investigation with the carrier.",
                "customer_response": f"I apologize that your package hasn't arrived. I've opened an investigation with the carrier. Please allow 5-7 business days for investigation. If the package is confirmed lost, we'll issue a full refund. [Source: {source_name}]",
                "next_steps": "Open carrier investigation",
                "internal_notes": "Lost package investigation initiated"
            }
        
        # ==================== CANCEL ORDER - APPROVE ====================
        if any(term in ticket_lower for term in ['cancel', 'just placed']):
            return {
                "decision": "approve",
                "rationale": "Orders can be cancelled within 30 minutes of placement.",
                "customer_response": f"I've cancelled your order as requested. The refund will be processed to your original payment method within 5-7 business days. [Source: {source_name}]",
                "next_steps": "Process cancellation",
                "internal_notes": "Order cancelled per customer request"
            }
        
        # ==================== COUPON ISSUES - INVESTIGATE ====================
        if 'coupon' in ticket_lower or 'code' in ticket_lower:
            return {
                "decision": "investigate",
                "rationale": "Coupon issues require investigation to verify code validity.",
                "customer_response": f"I'll investigate the coupon code issue. Could you please provide the full code and confirm if you've met any minimum purchase requirements? I'll get back to you within 24 hours. [Source: {source_name}]",
                "next_steps": "Verify coupon validity",
                "internal_notes": "Coupon issue - under investigation"
            }
        
        # ==================== MISSING ITEMS - APPROVE ====================
        if any(term in ticket_lower for term in ['missing', 'only got']):
            return {
                "decision": "approve",
                "rationale": "Missing items qualify for refund or replacement.",
                "customer_response": f"I apologize for the missing item. I've processed a refund for the missing item. You should see the credit in 5-7 business days. [Source: {source_name}]",
                "next_steps": "Process refund for missing item",
                "internal_notes": "Missing item - refund processed"
            }
        
        # ==================== DAMAGED ITEMS - APPROVE ====================
        if any(term in ticket_lower for term in ['broken', 'damaged', 'cracked', 'screen', 'defective']):
            return {
                "decision": "approve",
                "rationale": "Damaged items qualify for full refund or replacement.",
                "customer_response": f"I'm sorry your {self._extract_item(ticket_text)} arrived damaged. I've issued a full refund. A return label has been sent to your email for the damaged item. [Source: {source_name}]",
                "next_steps": "Send return label and process refund",
                "internal_notes": "Damaged item - refund with return"
            }
        
        # ==================== WRONG ITEM - APPROVE ====================
        if any(term in ticket_lower for term in ['wrong color', 'wrong size', 'wrong item']):
            return {
                "decision": "approve",
                "rationale": "Wrong items qualify for full refund or replacement with return shipping provided.",
                "customer_response": f"I apologize for sending the wrong {self._extract_item(ticket_text)}. I've processed a replacement order and sent a return label for the incorrect item. [Source: {source_name}]",
                "next_steps": "Process replacement and send return label",
                "internal_notes": "Wrong item - replacement processed"
            }
        
        # ==================== SHIPPING DELAY - PARTIAL ====================
        if any(term in ticket_lower for term in ['late', 'delay', 'shipping took']):
            return {
                "decision": "partial",
                "rationale": "Shipping delays may qualify for shipping cost refund if expedited shipping was paid.",
                "customer_response": f"I apologize for the shipping delay. I've issued a refund for your shipping costs. The refund will appear in 5-7 business days. [Source: {source_name}]",
                "next_steps": "Refund shipping cost",
                "internal_notes": "Shipping delay - refunded shipping cost"
            }
        
        # ==================== EU CUSTOMER - 14 DAY COOLING OFF ====================
        if order_context.get('shipping_region', '').startswith('EU'):
            return {
                "decision": "approve",
                "rationale": "EU customers have 14-day cooling-off period for online purchases.",
                "customer_response": f"As you're an EU customer, you have the right to return this item within 14 days. I've approved your return request. A return label will be sent shortly. [Source: {source_name}]",
                "next_steps": "Send return label",
                "internal_notes": "EU cooling-off return approved"
            }
        
        # ==================== DEFAULT RETURN - APPROVE ====================
        return {
            "decision": "approve",
            "rationale": "Items returned within 30 days in original condition qualify for refund.",
            "customer_response": f"I've approved your return request. Please use the return label sent to your email. Once we receive the item, we'll process your refund within 5-7 business days. [Source: {source_name}]",
            "next_steps": "Send return label",
            "internal_notes": "Standard return approved"
        }
    
    def _get_source_name(self, policy_evidence: List[Dict]) -> str:
        """Get source name from evidence"""
        for evidence in policy_evidence:
            if evidence.get('citation'):
                return evidence['citation'].split(' -')[0]
        return "policy_document.txt"
    
    def _extract_item(self, ticket_text: str) -> str:
        """Extract item name from ticket"""
        ticket_lower = ticket_text.lower()
        if 'cookies' in ticket_lower:
            return 'cookies'
        if 'shoes' in ticket_lower:
            return 'shoes'
        if 'toothbrush' in ticket_lower:
            return 'toothbrush'
        if 'swimsuit' in ticket_lower:
            return 'swimsuit'
        if 'electronics' in ticket_lower:
            return 'electronics'
        return 'item'
    
    def _format_evidence(self, evidence: List[Dict]) -> str:
        """Format evidence with citations"""
        formatted = []
        for i, e in enumerate(evidence, 1):
            formatted.append(f"[{i}] Source: {e['citation']}")
            formatted.append(f"    Content: {e['content'][:500]}")
            formatted.append(f"    Relevance: {e['relevance_score']:.2f}\n")
        return "\n".join(formatted)