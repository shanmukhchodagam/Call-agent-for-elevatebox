# pyrefly: ignore [missing-import]
from omnidimension import Client

from app.config import OMNIDIM_API_KEY
from app.intelligence.understand import extract_lead_data


CALL_ID = 8605274


def main():
    client = Client(OMNIDIM_API_KEY)

    response = client.call.get_call_log(CALL_ID)

    call_data = response["json"]["call_log_data"][0]

    conversation = call_data["call_conversation"]

    lead = extract_lead_data(conversation)

    print("\n=== CALL ===")
    print(f"Call ID: {CALL_ID}")

    print("\n=== TRANSCRIPT ===")
    print(conversation)

    print("\n=== EXTRACTED LEAD ===")
    for key, value in lead.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()