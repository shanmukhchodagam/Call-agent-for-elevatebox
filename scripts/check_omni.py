# pyrefly: ignore [missing-import]
from omnidimension import Client

from app.config import OMNIDIM_API_KEY


client = Client(OMNIDIM_API_KEY)

agents = client.agent.list()

print("OmniDimension API connection successful.")
print("Agents:")
print(agents)