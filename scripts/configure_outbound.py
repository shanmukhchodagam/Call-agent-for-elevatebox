from app.telephony.service import TelephonyService
from app.config import OMNIDIM_AGENT_ID
service = TelephonyService()

response = service.make_outgoing(OMNIDIM_AGENT_ID)


print(response)