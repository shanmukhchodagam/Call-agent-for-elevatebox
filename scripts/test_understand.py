from app.intelligence.understand import extract_lead_data


conversation = """
LLM: Hi, I'm calling from ElevateBox. We help businesses build e-commerce websites.
User: Yes.
LLM: Could you tell me a bit about your business?
User: I ran a clothing business.
LLM: About how many different products do you have?
User: Around 500 to 600.
LLM: Do you need payment gateways?
User: Yeah, I want the payment gateway.
LLM: Do you want customer accounts or guest checkout?
User: Guest checkout, no customer accounts.
LLM: When do you want the website ready?
User: In another 2 months.
LLM: What is your budget?
User: 50 to 60 thousand.
"""

lead = extract_lead_data(conversation)

print(lead)