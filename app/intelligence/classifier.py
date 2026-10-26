import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class ClassificationResult:
    classification: str  # "HOT", "WARM", "COLD"
    score: int
    reasons: List[str] = field(default_factory=list)
    state: str = "COLD"  # "HOT", "WARM", "COLD"
    next_action: str = "log_and_send_overview"  # "fire_whatsapp_midcall", "capture_barrier_and_schedule_callback", "log_and_send_overview"
    barrier: Optional[str] = None  # e.g. "budget constraint", "brother/partner decides", "timing constraint"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "classification": self.classification,
            "state": self.state,
            "score": self.score,
            "reasons": self.reasons,
            "next_action": self.next_action,
            "barrier": self.barrier,
        }


@dataclass
class ScoringWeights:
    """Configurable scoring weights for lead classification signals."""
    budget_high_threshold: int = 50000
    budget_high_points: int = 25
    budget_mid_threshold: int = 20000
    budget_mid_points: int = 15
    budget_low_points: int = 10

    timeline_urgent_max_months: int = 2
    timeline_urgent_points: int = 25
    timeline_mid_max_months: int = 6
    timeline_mid_points: int = 15
    timeline_long_points: int = 5

    products_high_threshold: int = 500
    products_high_points: int = 20
    products_mid_threshold: int = 50
    products_mid_points: int = 15
    products_low_points: int = 10

    payment_gateway_points: int = 10
    checkout_preference_points: int = 10
    business_type_points: int = 10
    additional_reqs_points: int = 5

    # Indirect Intent Signals (real human expressions)
    indirect_buying_intent_points: int = 25

    hot_threshold: int = 70
    warm_threshold: int = 40


class LeadClassifier:
    """
    Transparent, rule-based lead qualification engine.
    Evaluates both explicit structural data (budget, timeline, products)
    and indirect conversational cues ("send me details", "brother handles this", "budget is not much right now").
    Determines 3 actionable states:
    - HOT  -> Fire WhatsApp before call ends
    - WARM -> Capture the barrier, schedule the callback
    - COLD -> Log it, send overview brochure, move on
    """

    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()

    def classify(
        self,
        lead: Dict[str, Any],
        conversation_text: Optional[str] = None,
    ) -> ClassificationResult:
        score = 0
        reasons: List[str] = []
        barrier: Optional[str] = None

        text_to_search = (conversation_text or "").lower()

        # 0. Check for Indirect Conversational Barriers (WARM signals)
        barrier_patterns = {
            "Decision Maker Barrier (brother/partner/boss decides)": [
                r"brother\s+(?:handles|takes\s*care|decides)",
                r"(?:partner|boss|father|owner)\s+(?:decides|handles)",
                r"need\s+to\s+(?:ask|speak|check\s+with)\s+my\s+(?:brother|partner|boss|team)",
            ],
            "Budget Constraint Barrier (interested but tight funds)": [
                r"budget\s+is\s+not\s+much",
                r"tight\s+on\s+(?:funds|budget|money)",
                r"cannot\s+spend\s+much",
                r"low\s+budget\s+right\s+now",
            ],
            "Timing Barrier (interested but later date)": [
                r"not\s+ready\s+(?:right\s+now|yet)",
                r"busy\s+(?:right\s+now|this\s+week)",
                r"call\s+(?:me\s+)?next\s+(?:month|quarter)",
            ],
        }

        for barrier_desc, patterns in barrier_patterns.items():
            if any(re.search(p, text_to_search) for p in patterns):
                barrier = barrier_desc
                reasons.append(f"Identified customer barrier: {barrier_desc}")
                # Ensure baseline WARM points so it doesn't get discarded as COLD
                score += 20
                break

        # 0. Check for Indirect Buying Intent Cues (HOT signals)
        hot_cues = [
            (r"send\s+(?:me\s+)?(?:the\s+)?details\s*(?:on\s*whatsapp)?", "Customer requested details on WhatsApp"),
            (r"how\s+soon\s+can\s+you\s+start", "Customer asked for immediate start timeline"),
            (r"what\s+(?:is|would\s+be)\s+the\s+cost", "Customer directly inquired about pricing"),
            (r"send\s+quotation|send\s+proposal", "Customer requested quotation/proposal"),
        ]
        for pattern, desc in hot_cues:
            if re.search(pattern, text_to_search):
                score += self.weights.indirect_buying_intent_points
                reasons.append(f"Indirect buying intent signal: '{desc}' (+{self.weights.indirect_buying_intent_points})")
                break

        # 1. Budget Signal
        b_min = lead.get("budget_min")
        b_max = lead.get("budget_max")
        budget_val = b_max or b_min

        if budget_val is not None:
            if budget_val >= self.weights.budget_high_threshold:
                pts = self.weights.budget_high_points
                score += pts
                reasons.append(f"Substantial budget provided: Rs. {budget_val:,} (+{pts})")
            elif budget_val >= self.weights.budget_mid_threshold:
                pts = self.weights.budget_mid_points
                score += pts
                reasons.append(f"Viable budget provided: Rs. {budget_val:,} (+{pts})")
            elif budget_val > 0:
                pts = self.weights.budget_low_points
                score += pts
                reasons.append(f"Modest budget provided: Rs. {budget_val:,} (+{pts})")

        # 2. Timeline Urgency Signal
        timeline = lead.get("timeline_months")
        if timeline is not None:
            if timeline <= self.weights.timeline_urgent_max_months:
                pts = self.weights.timeline_urgent_points
                score += pts
                reasons.append(f"High urgency timeline: {timeline} month(s) (+{pts})")
            elif timeline <= self.weights.timeline_mid_max_months:
                pts = self.weights.timeline_mid_points
                score += pts
                reasons.append(f"Realistic medium-term timeline: {timeline} months (+{pts})")
            else:
                pts = self.weights.timeline_long_points
                score += pts
                reasons.append(f"Long-range timeline: {timeline} months (+{pts})")

        # 3. Product Catalog Scale
        p_min = lead.get("product_count_min")
        p_max = lead.get("product_count_max")
        prod_val = p_max or p_min

        if prod_val is not None:
            if prod_val >= self.weights.products_high_threshold:
                pts = self.weights.products_high_points
                score += pts
                reasons.append(f"Large product catalog: {prod_val}+ products (+{pts})")
            elif prod_val >= self.weights.products_mid_threshold:
                pts = self.weights.products_mid_points
                score += pts
                reasons.append(f"Moderate product catalog: {prod_val} products (+{pts})")
            elif prod_val > 0:
                pts = self.weights.products_low_points
                score += pts
                reasons.append(f"Initial product catalog: {prod_val} products (+{pts})")

        # 4. Feature Requirements (Payment Gateway)
        if lead.get("payment_gateway") is True:
            pts = self.weights.payment_gateway_points
            score += pts
            reasons.append(f"Explicit payment gateway requirement (+{pts})")

        # 5. Checkout Preference
        if lead.get("guest_checkout") is not None or lead.get("customer_accounts") is not None:
            pts = self.weights.checkout_preference_points
            score += pts
            guest = lead.get("guest_checkout")
            acct = lead.get("customer_accounts")
            desc = f"guest_checkout={guest}, customer_accounts={acct}"
            reasons.append(f"Definitive checkout preference specified ({desc}) (+{pts})")

        # 6. Business Type
        if lead.get("business_type"):
            pts = self.weights.business_type_points
            score += pts
            reasons.append(f"Defined business domain: {lead.get('business_type')} (+{pts})")

        # 7. Additional Requirements
        if lead.get("additional_requirements"):
            pts = self.weights.additional_reqs_points
            score += pts
            reasons.append(f"Specific website feature requirements noted (+{pts})")

        # Determine Tier & Actions
        # Priority rule: If an explicit barrier exists, cap at WARM (need callback) unless overwhelming HOT intent
        if score >= self.weights.hot_threshold and not barrier:
            classification = "HOT"
            next_action = "fire_whatsapp_midcall"
        elif barrier or score >= self.weights.warm_threshold:
            classification = "WARM"
            next_action = "capture_barrier_and_schedule_callback"
        else:
            classification = "COLD"
            next_action = "log_and_send_overview"
            if not reasons:
                reasons.append("Minimal qualification signals captured (no budget, timeline, or scope defined)")

        return ClassificationResult(
            classification=classification,
            state=classification,
            score=score,
            reasons=reasons,
            next_action=next_action,
            barrier=barrier,
        )


def classify_lead(
    lead: Dict[str, Any],
    weights: Optional[ScoringWeights] = None,
    conversation_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper function to classify lead and return standardized dictionary."""
    classifier = LeadClassifier(weights=weights)
    return classifier.classify(lead, conversation_text=conversation_text).to_dict()
