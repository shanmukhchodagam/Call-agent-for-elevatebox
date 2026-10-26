from app.telephony.service import TelephonyService
from app.config import OMNIDIM_AGENT_ID

def main():
    service=TelephonyService()
    response=service.get_agent(OMNIDIM_AGENT_ID)
    print(response)

if __name__=="__main__":
    main()

