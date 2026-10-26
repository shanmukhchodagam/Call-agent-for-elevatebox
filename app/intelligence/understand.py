import re
from typing import Optional, Tuple, Dict, Any, List

from app.intelligence.semantic import extract_semantic_lead_data
from app.conversation.parser import ConversationParser


def empty_lead() -> Dict[str, Any]:
    """Returns the canonical MVP lead data structure with null defaults."""
    return {
        "business_type": None,
        "product_count_min": None,
        "product_count_max": None,
        "payment_gateway": None,
        "customer_accounts": None,
        "guest_checkout": None,
        "timeline_months": None,
        "budget_min": None,
        "budget_max": None,
        "additional_requirements": None,
    }


# Number word mappings for common English speech
WORD_TO_NUMBER = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100, "thousand": 1000,
}


def _parse_number_word(text: str) -> Optional[int]:
    """Converts simple phrase like 'five hundred' or 'fifty' into integer."""
    text = text.lower().strip()
    if text.isdigit():
        return int(text)

    tokens = text.split()
    total = 0
    current = 0
    for token in tokens:
        if token in WORD_TO_NUMBER:
            val = WORD_TO_NUMBER[token]
            if val == 100:
                current = (current if current else 1) * 100
            elif val == 1000:
                total += (current if current else 1) * 1000
                current = 0
            else:
                current += val
        else:
            return None
    return total + current if (total + current) > 0 else None


def extract_product_count(text: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extracts minimum and maximum product count from conversation text.
    Handles ranges ('500 to 600', 'around 500 to 600'), approximations
    ('around 500', 'about 500 products'), and word numbers ('five hundred').
    """
    # 1. Explicit range with products/items or around/between prefix
    range_patterns = [
        # e.g. "500 to 600 products", "500-600 items", "500 to 600 skus"
        r"(\d+)\s*(?:to|-)\s*(\d+)\s*(?:products?|items?|skus?|articles?)",
        # e.g. "between 500 and 600", "between 500 to 600"
        r"between\s+(\d+)\s*(?:and|to|-)\s*(\d+)",
        # e.g. "around 500 to 600", "about 500-600", "approx 500 to 600", "roughly 500 to 600"
        r"(?:around|about|approximately|approx|roughly)\s+(\d+)\s*(?:to|-)\s*(\d+)",
        # Standalone range without units when context implies count e.g. "Around 500 to 600."
        r"(?:around|about|approximately|approx|roughly)\s+(\d+)\s*(?:to|-)\s*(\d+)",
        # "500 to 600" when not followed by thousand / k / lakhs / rs / rupees
        r"(?<![₹$])\b(\d{1,4})\s*(?:to|-)\s*(\d{1,4})\b(?!\s*(?:thousand|k|lakh|rupee|inr|month|year))",
    ]

    for pattern in range_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            low = int(match.group(1))
            high = int(match.group(2))
            if low <= high:
                return low, high
            return high, low

    # 2. Single product count with qualifiers or units
    single_patterns = [
        r"(?:around|about|approximately|approx|roughly)\s+(\d+)\s*(?:products?|items?|skus?)",
        r"(\d+)\s*(?:products?|items?|skus?)",
        r"(?:around|about|approximately|approx|roughly)\s+(\d{1,4})\b(?!\s*(?:thousand|k|lakh|rupee|inr|month|year))",
    ]

    for pattern in single_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = int(match.group(1))
            return val, val

    # 3. Word numbers e.g. "five hundred products" or "around five hundred"
    word_match = re.search(
        r"(?:around|about|approximately)?\s*(five hundred|one hundred|two hundred|three hundred|a thousand|one thousand)\s*(?:products?|items?)?",
        text,
        re.IGNORECASE,
    )
    if word_match:
        phrase = word_match.group(1).replace("a thousand", "one thousand")
        num = _parse_number_word(phrase)
        if num:
            return num, num

    return None, None


def extract_budget(text: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extracts minimum and maximum budget from conversation text.
    Handles '50 to 60 thousand', '50k - 60k', 'around 50k', '₹50,000 to ₹60,000',
    '1 to 2 lakhs', etc.
    """
    # 1. "X to Y thousand" / "X - Y thousand"
    match_thousand_range = re.search(
        r"(\d+)\s*(?:to|-)\s*(\d+)\s*thousand",
        text,
        re.IGNORECASE,
    )
    if match_thousand_range:
        return (
            int(match_thousand_range.group(1)) * 1000,
            int(match_thousand_range.group(2)) * 1000,
        )

    # 2. "Xk to Yk" / "Xk-Yk" / "X to Y k"
    match_k_range = re.search(
        r"(\d+)\s*k?\s*(?:to|-)\s*(\d+)\s*k\b",
        text,
        re.IGNORECASE,
    )
    if match_k_range:
        return (
            int(match_k_range.group(1)) * 1000,
            int(match_k_range.group(2)) * 1000,
        )

    # 3. "X to Y lakh(s)" / "X-Y lakhs"
    match_lakh_range = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*lakhs?",
        text,
        re.IGNORECASE,
    )
    if match_lakh_range:
        return (
            int(float(match_lakh_range.group(1)) * 100000),
            int(float(match_lakh_range.group(2)) * 100000),
        )

    # 4. Currency symbols or full numbers: "₹50,000 to ₹60,000", "50000 to 60000", "Rs 50000 - 60000"
    match_full_range = re.search(
        r"(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:,\d{3})+|\d{4,7})\s*(?:to|-)\s*(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:,\d{3})+|\d{4,7})",
        text,
        re.IGNORECASE,
    )
    if match_full_range:
        low = int(match_full_range.group(1).replace(",", ""))
        high = int(match_full_range.group(2).replace(",", ""))
        return low, high

    # 5. Single values: "around 50 thousand", "50 thousand"
    match_single_thousand = re.search(
        r"(?:around|about|approx|approximately|budget\s*of)?\s*(\d+)\s*thousand",
        text,
        re.IGNORECASE,
    )
    if match_single_thousand:
        val = int(match_single_thousand.group(1)) * 1000
        return val, val

    # 6. Single value: "around 50k", "50k"
    match_single_k = re.search(
        r"(?:around|about|approx|approximately|budget\s*of)?\s*(\d+)\s*k\b",
        text,
        re.IGNORECASE,
    )
    if match_single_k:
        val = int(match_single_k.group(1)) * 1000
        return val, val

    # 7. Single value lakh: "1 lakh", "around 2 lakhs"
    match_single_lakh = re.search(
        r"(?:around|about|approx|approximately|budget\s*of)?\s*(\d+(?:\.\d+)?)\s*lakhs?",
        text,
        re.IGNORECASE,
    )
    if match_single_lakh:
        val = int(float(match_single_lakh.group(1)) * 100000)
        return val, val

    # 8. Single currency symbol: "₹50,000" or "Rs. 50,000"
    match_single_curr = re.search(
        r"(?:₹|rs\.?|inr)\s*(\d{1,3}(?:,\d{3})+|\d{4,7})\b",
        text,
        re.IGNORECASE,
    )
    if match_single_curr:
        val = int(match_single_curr.group(1).replace(",", ""))
        return val, val

    return None, None


def extract_timeline(text: str) -> Optional[int]:
    """
    Extracts timeline in months from conversation text.
    Handles '2 months', 'in another 2 months', 'within 2 months',
    'two months', '6 weeks' (~1-2 months), etc.
    """
    # 1. Digits followed by months e.g. "2 months", "in another 2 months", "2 to 3 months"
    match_months = re.search(
        r"(?:in\s+(?:another\s+)?)?(\d+)\s*(?:to|-)?\s*\d*\s*months?",
        text,
        re.IGNORECASE,
    )
    if match_months:
        return int(match_months.group(1))

    # 2. Word numbers e.g. "two months", "three months", "one month", "a month"
    match_word_months = re.search(
        r"(?:in\s+(?:another\s+)?)?(one|two|three|four|five|six|seven|eight|nine|ten|a)\s+months?",
        text,
        re.IGNORECASE,
    )
    if match_word_months:
        word = match_word_months.group(1).lower()
        if word == "a":
            return 1
        return WORD_TO_NUMBER.get(word)

    # 3. Weeks to months approximation e.g. "8 weeks" -> 2 months, "4 weeks" -> 1 month
    match_weeks = re.search(
        r"(\d+)\s*weeks?",
        text,
        re.IGNORECASE,
    )
    if match_weeks:
        weeks = int(match_weeks.group(1))
        return max(1, round(weeks / 4.33))

    return None


def extract_lead_data(
    conversation: str,
    customer_statements: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Primary lead extraction pipeline combining deterministic regex extraction
    for numerical fields (products, budget, timeline) and Gemini semantic extraction
    for business features, grounding on confirmed customer statements.
    """
    # If customer statements are not explicitly passed, parse them from conversation
    if customer_statements is None:
        ctx = ConversationParser.parse_raw_transcript(conversation)
        customer_statements = ctx.customer_statements
        customer_text = " ".join(customer_statements)
    else:
        customer_text = " ".join(customer_statements)

    lead = empty_lead()

    # Search customer statements first for deterministic values, then fallback to full conversation
    # 1. Product count
    prod_min, prod_max = extract_product_count(customer_text)
    if prod_min is None:
        prod_min, prod_max = extract_product_count(conversation)
    lead["product_count_min"] = prod_min
    lead["product_count_max"] = prod_max

    # 2. Budget
    b_min, b_max = extract_budget(customer_text)
    if b_min is None:
        b_min, b_max = extract_budget(conversation)
    lead["budget_min"] = b_min
    lead["budget_max"] = b_max

    # 3. Timeline
    timeline = extract_timeline(customer_text)
    if timeline is None:
        timeline = extract_timeline(conversation)
    lead["timeline_months"] = timeline

    # 4. Semantic extraction via Gemini
    semantic_lead = extract_semantic_lead_data(
        conversation=conversation,
        customer_statements=customer_statements,
    )

    # Merge semantic fields
    lead["business_type"] = semantic_lead.get("business_type")
    lead["payment_gateway"] = semantic_lead.get("payment_gateway")
    lead["customer_accounts"] = semantic_lead.get("customer_accounts")
    lead["guest_checkout"] = semantic_lead.get("guest_checkout")
    lead["additional_requirements"] = semantic_lead.get("additional_requirements")

    # Inferred business type if present (not replacing confirmed business_type)
    if semantic_lead.get("inferred_business_type"):
        lead["inferred_business_type"] = semantic_lead.get("inferred_business_type")

    return lead