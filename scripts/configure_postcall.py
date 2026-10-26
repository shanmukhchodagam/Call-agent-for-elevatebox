from app.config import OMNIDIM_AGENT_ID
from app.telephony.service import TelephonyService

def main():
    service=TelephonyService()
    response=service.configure_extraction(OMNIDIM_AGENT_ID)
    print(response)

if __name__=="__main__":
    main()