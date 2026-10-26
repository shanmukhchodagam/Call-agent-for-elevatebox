from app.telephony.service import TelephonyService

service = TelephonyService()

response = service.client.agent.list()

print(response)