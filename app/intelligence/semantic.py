import json
import logging
import time
from typing import Optional, Dict, Any, List

from app.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)


def empty_semantic_lead() -> Dict[str, Any]:
    """Returns default null structure for semantic lead fields."""
    return {
        "business_type": None,
        "payment_gateway": None,
        "customer_accounts": None,
        "guest_checkout": None,
        "additional_requirements": None,
        "inferred_business_type": None,
    }


def extract_semantic_lead_data(
    conversation: str,
    customer_statements: Optional[List[str]] = None,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """
    Extract semantic lead information from customer conversation using Gemini.
    Strictly separates confirmed customer facts from AI interpretations.
    Includes transient error retries (e.g. 503 spikes).
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not configured. Falling back to empty semantic lead.")
        return empty_semantic_lead()

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as exc:
        logger.error(f"Failed to initialize Gemini client: {exc}")
        return empty_semantic_lead()

    customer_section = ""
    if customer_statements:
        customer_section = "\nCUSTOMER'S DIRECT STATEMENTS:\n" + "\n".join(f"- {s}" for s in customer_statements)

    prompt = f"""
You are a precision lead extraction system for an e-commerce agency.
Analyze the following conversation between an AI sales agent and a customer.

{customer_section}

FULL CONVERSATION TRANSCRIPT:
{conversation}

TASK:
Extract the following fields based STRICTLY on confirmed customer statements:
1. "business_type": (string or null) The type/industry of business the customer runs or is starting.
   CRITICAL GROUNDING RULE:
   - Only extract what the CUSTOMER explicitly stated or confirmed.
   - If the AI agent rephrased, inferred, or guessed an interpretation (for example: the customer says "I ran a closing business" and the AI assumes "so you sell clothing items"), and the customer did NOT explicitly agree to that assumption, business_type MUST BE null.
   - Do NOT turn an AI interpretation into a customer fact.
2. "payment_gateway": (boolean or null) True if customer wants/needs payment gateway integration, False if explicitly rejected, null if not discussed.
3. "customer_accounts": (boolean or null) True if customer wants user accounts/registration, False if explicitly rejected (e.g. wants guest checkout only or no accounts), null if not discussed.
4. "guest_checkout": (boolean or null) True if customer requested/approved guest checkout, False if rejected, null if not discussed.
5. "additional_requirements": (string or null) Special website/product features explicitly requested by customer beyond standard e-commerce features (e.g., custom animations, wholesale pricing, multi-currency). Do NOT put budget, timeline, or product count here. If none mentioned or customer said "no, that's it", return null.
6. "inferred_business_type": (string or null) If the AI or context hinted at a business type that was NOT fully confirmed by the customer, note it here (e.g., "clothing (unconfirmed)"). Otherwise null.

RULES:
- Return ONLY a valid JSON object matching the keys above.
- Use null whenever information is missing or unverified.
- Never invent information.
"""

    model_name = GEMINI_MODEL or "gemini-2.5-flash"

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                },
            )

            raw_text = response.text.strip() if response.text else ""
            if not raw_text:
                logger.warning(f"Gemini ({model_name}) returned empty response.")
                return empty_semantic_lead()

            # Handle possible markdown fencing
            if raw_text.startswith("```"):
                raw_text = raw_text.strip("`")
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:].strip()

            data = json.loads(raw_text)

            # Normalize schema
            result = empty_semantic_lead()
            for key in result.keys():
                if key in data:
                    val = data[key]
                    if val == "" or val == []:
                        val = None
                    result[key] = val

            return result

        except json.JSONDecodeError as exc:
            logger.error(f"Gemini ({model_name}) returned invalid JSON: {exc}.")
            return empty_semantic_lead()
        except Exception as exc:
            err_msg = str(exc)
            if ("503" in err_msg or "UNAVAILABLE" in err_msg or "429" in err_msg) and attempt < max_retries:
                wait_secs = 2.0 * (attempt + 1)
                logger.warning(
                    f"Gemini call attempt {attempt + 1} failed ({err_msg}). Retrying in {wait_secs}s..."
                )
                time.sleep(wait_secs)
                continue
            logger.error(f"Gemini API call failed with model {model_name}: {exc}")
            return empty_semantic_lead()

    return empty_semantic_lead()