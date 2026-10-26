# pyrefly: ignore [missing-import]
from app.config import OMNIDIM_API_KEY
# pyrefly: ignore [missing-import]
from omnidimension import Client
import inspect

client=Client(OMNIDIM_API_KEY)


print(inspect.signature(client.agent.update))

print(inspect.getsource(client.agent.update))