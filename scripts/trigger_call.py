from app.config import OMNIDIM_AGENT_ID
from app.telephony.service import TelephonyService


def main():
    service = TelephonyService()

    response = service.dispatch_call(
        agent_id=int(OMNIDIM_AGENT_ID),
        to_number="+919381758441",
    )

    print(response)


if __name__ == "__main__":
    main()