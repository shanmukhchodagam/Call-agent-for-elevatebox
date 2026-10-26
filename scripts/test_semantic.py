from app.intelligence.semantic import extract_semantic_lead_data


conversation = """
LLM: Hi, I'm calling from ElevateBox. We help businesses build e-commerce websites.
User: Yes.

LLM: Could you tell me a bit about your business?
User: I run a clothing business.

LLM: How many products do you have?
User: Around 500 to 600.

LLM: Do you need a payment gateway?
User: Yes, I need one.

LLM: Do you want customer accounts or guest checkout?
User: Guest checkout. I don't want customers to create accounts.

LLM: When do you want the website ready?
User: In another 2 months.

LLM: What's your budget?
User: 50 to 60 thousand.

LLM: Anything else?
User: No, that's it.
"""


lead = extract_semantic_lead_data(conversation)

print("\n=== STRUCTURED SEMANTIC LEAD ===")
print(lead)