from mcp_server.bridge_client import BridgeClient
import json
client = BridgeClient()
health = client.health()
print('Mode:', health.get('mode'))
print('Status:', health.get('status'))
print()
print('Raw workflow catalog:')
print(json.dumps(health.get('workflow_catalog', []), indent=2))
