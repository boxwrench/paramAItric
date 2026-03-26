from mcp_server.bridge_client import BridgeClient
client = BridgeClient()
try:
    health = client.health()
    print('Fusion 360 Bridge: CONNECTED')
    workflows = health.get("workflow_catalog", [])
    print(f'Workflows available: {[w.get("id") for w in workflows]}')
except Exception as e:
    print(f'Fusion 360 Bridge: NOT REACHABLE - {e}')
