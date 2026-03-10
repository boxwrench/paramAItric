> Reference note: this file is a preserved draft and not a canonical project specification.
> Use the repo root docs for the current source of truth: `README.md`, `PROJECT_CONTEXT.md`, `ARCHITECTURE.md`, and `DEVELOPMENT_PLAN.md`.
# Building a Fusion 360 AI assistant with MCP

**You can connect any major AI model to Autodesk Fusion 360 using a three-layer bridge architecture: a Fusion 360 add-in that listens on localhost, an MCP server that translates AI tool calls into bridge commands, and an AI host that drives the whole system.** This guide walks you through every layer, from the first line of add-in code to generating parametric design variations on command. The system supports three operational modes — Work (reliable CAD), Utility (workflow automation), and Creative (generative modeling) — each with distinct safety constraints and tool sets. Fusion 360's Python API is powerful but single-threaded, so the architecture must route every command through a CustomEvent dispatcher on Fusion's main thread. Getting this right is the single most important engineering decision in the entire project.

---

## 1. Architecture: four layers, one strict rule

The system has four distinct layers. Every layer exists because of one constraint: **the Fusion 360 API is not thread-safe**. All API calls must execute on Fusion's main UI thread. No exceptions.

### The full signal path

```
┌─────────────┐     MCP Protocol      ┌─────────────┐    HTTP/TCP on     ┌──────────────────┐   CustomEvent    ┌─────────────┐
│   AI Host   │◄─────(stdio/HTTP)─────►│  MCP Server │◄───localhost────►  │  Fusion 360      │◄──(main thread)──►│  Fusion API │
│ (Claude,    │                        │  (Python)   │    :9876           │  Add-in           │   dispatch       │  Operations │
│  Gemini,    │  Tool discovery,       │             │                    │  (background      │                  │             │
│  ChatGPT)   │  tool calls,           │  Translates │  JSON command/     │   HTTP thread +   │  fireCustomEvent │  Sketches,  │
│             │  results               │  MCP ↔ HTTP │  response          │   event handler)  │  → notify()      │  extrudes,  │
└─────────────┘                        └─────────────┘                    └──────────────────┘                  │  exports    │
                                                                                                                └─────────────┘
```

### Why each layer exists

**Layer 1 — AI Host.** The user-facing application (Claude Desktop, ChatGPT, Gemini CLI, or a custom script). It discovers available tools via MCP, decides which to call based on user prompts, and sends structured tool invocations. You write zero code here — you just configure it to point at your MCP server.

**Layer 2 — MCP Server.** A standalone Python process that speaks the Model Context Protocol. It defines tool schemas (what operations are available, their parameters, descriptions), receives tool calls from the AI host, translates them into HTTP requests to the Fusion bridge, waits for results, and returns them. This is where your tool definitions, input validation, and mode logic live.

**Layer 3 — HTTP Bridge (inside the Fusion Add-in).** A lightweight HTTP or TCP server running on a background thread *inside* the Fusion 360 process. It receives commands from the MCP server on `localhost:9876`, but it cannot touch the Fusion API directly. Instead, it queues commands and fires a `CustomEvent` to wake the main thread.

**Layer 4 — CustomEvent Dispatcher.** The event handler that runs on Fusion's main thread. When the bridge fires an event, this handler picks up the queued command, executes the actual Fusion API calls (create sketch, extrude, export), stores the result, and signals the bridge thread that it's done. The bridge thread then returns the result as an HTTP response.

### Recommended folder structure

This layout separates concerns cleanly and prevents the most common integration problems — dependency conflicts, import errors, and deployment confusion.

```
fusion-ai-assistant/
├── README.md
├── config.json                         # Shared config (port, mode defaults)
│
├── mcp-server/                         # LAYER 2: External Python process
│   ├── pyproject.toml                  # Dependencies: mcp, httpx/requests
│   ├── server.py                       # MCP server entry point (FastMCP)
│   ├── tools/                          # Tool definitions by mode
│   │   ├── __init__.py
│   │   ├── work_tools.py              # Pass 1: Core CAD tools
│   │   ├── utility_tools.py           # Pass 2: Export, BOM, file mgmt
│   │   └── creative_tools.py          # Pass 3: Generative tools
│   ├── bridge_client.py               # HTTP client that talks to Fusion
│   └── schemas.py                     # Shared Pydantic models / schemas
│
├── fusion-addin/                       # LAYER 3+4: Copied to Fusion AddIns dir
│   ├── FusionAIBridge.py              # Main add-in entry (run/stop)
│   ├── FusionAIBridge.manifest        # Required manifest file
│   ├── http_server.py                 # Background HTTP listener
│   ├── command_executor.py            # Fusion API command dispatch
│   └── resources/                     # Icons (16x16, 32x32 PNGs)
│
├── scripts/
│   ├── install_addin.py               # Copies add-in to Fusion's AddIns dir
│   ├── start_mcp.bat                  # Windows: starts MCP server
│   └── start_mcp.sh                   # Mac: starts MCP server
│
└── tests/
    ├── test_bridge.py                 # Test HTTP bridge connection
    └── test_tools.py                  # Test tool schemas and validation
```

**Critical rule**: The add-in folder name, `.py` filename, and `.manifest` filename **must all match exactly** (e.g., `FusionAIBridge/FusionAIBridge.py/FusionAIBridge.manifest`). This is a Fusion 360 requirement.

---

## 2. Step-by-step implementation from zero to working system

### Environment setup

**Python versions matter.** Fusion 360 bundles its own Python **3.9.7** interpreter. Your add-in code runs inside this interpreter — you cannot change it. Your MCP server runs in a separate Python environment (3.10+ recommended) with its own dependencies.

**Install dependencies for the MCP server:**

```bash
# Create a virtual environment for the MCP server
cd fusion-ai-assistant/mcp-server
python -m venv .venv
source .venv/bin/activate       # Mac/Linux
# .venv\Scripts\activate        # Windows

pip install "mcp[cli]"          # Official MCP Python SDK (v1.26+)
pip install httpx               # Async HTTP client for bridge communication
```

**Fusion 360 API access** requires no installation — the `adsk.core`, `adsk.fusion`, and `adsk.cam` modules are built into Fusion's Python. They are available automatically in any script or add-in.

**Fusion 360 API units**: internally, Fusion uses **centimeters for length** and **radians for angles**. A value of `5.0` means 5 cm. Use `ValueInput.createByString("50 mm")` for explicit units, or `ValueInput.createByReal(5.0)` for the internal centimeter value.

### Creating the Fusion 360 add-in from scratch

**Step 1: Create the manifest file.** Save as `fusion-addin/FusionAIBridge.manifest`:

```json
{
    "autodeskProduct": "Fusion360",
    "type": "addin",
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "author": "Your Name",
    "description": {
        "": "AI Bridge — connects Fusion 360 to AI assistants via MCP"
    },
    "version": "1.0.0",
    "runOnStartup": true,
    "supportedOS": "windows|mac"
}
```

Generate a unique GUID for the `id` field (use Python's `uuid.uuid4()` or any online generator). The `runOnStartup` flag means this add-in loads automatically when Fusion starts.

**Step 2: Create the main add-in file.** Save as `fusion-addin/FusionAIBridge.py`:

```python
import adsk.core
import adsk.fusion
import traceback
import threading
import json
import queue
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Global State ──────────────────────────────────────────────
app = None
ui = None
handlers = []
stop_flag = None
http_server = None
custom_event = None

CUSTOM_EVENT_ID = 'FusionAIBridgeEvent'
BRIDGE_PORT = 9876

# Thread-safe command queue: bridge thread puts commands in,
# main thread handler pulls them out
command_queue = queue.Queue()

# Per-request result passing
result_store = {}
result_events = {}

# ── HTTP Server (runs on background thread) ───────────────────
class BridgeRequestHandler(BaseHTTPRequestHandler):
    """Receives commands from the MCP server via HTTP POST."""

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length))

        # Create a unique request ID
        import uuid
        request_id = str(uuid.uuid4())
        body['_request_id'] = request_id

        # Prepare synchronization
        event = threading.Event()
        result_events[request_id] = event

        # Queue command and fire CustomEvent to wake main thread
        command_queue.put(body)
        app.fireCustomEvent(CUSTOM_EVENT_ID, json.dumps({
            'request_id': request_id
        }))

        # Wait for main thread to process (30s timeout)
        event.wait(timeout=30)

        # Retrieve result
        result = result_store.pop(request_id, {
            'success': False,
            'error': 'Timeout waiting for Fusion main thread'
        })
        result_events.pop(request_id, None)

        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok'}).encode())

    def log_message(self, format, *args):
        pass  # Suppress HTTP server logging

# ── CustomEvent Handler (runs on MAIN THREAD — safe for API) ──
class BridgeEventHandler(adsk.core.CustomEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            # Terminate any active command to avoid conflicts
            if ui.activeCommand != 'SelectCommand':
                ui.commandDefinitions.itemById('SelectCommand').execute()

            # Process all queued commands
            while not command_queue.empty():
                cmd = command_queue.get_nowait()
                request_id = cmd.get('_request_id')
                try:
                    result = execute_command(cmd)
                    result_store[request_id] = {
                        'success': True,
                        'data': result
                    }
                except Exception as e:
                    result_store[request_id] = {
                        'success': False,
                        'error': str(e),
                        'traceback': traceback.format_exc()
                    }
                finally:
                    event = result_events.get(request_id)
                    if event:
                        event.set()
        except:
            app.log(f'Bridge handler error: {traceback.format_exc()}')

# ── Command Executor (called from main thread) ────────────────
def execute_command(cmd):
    """Routes commands to the appropriate Fusion API operation."""
    action = cmd.get('action')
    params = cmd.get('params', {})

    if action == 'ping':
        return {'pong': True}

    elif action == 'create_sketch':
        return create_sketch(params)

    elif action == 'create_rectangle':
        return create_rectangle(params)

    elif action == 'extrude':
        return extrude_profile(params)

    elif action == 'fillet_edges':
        return fillet_edges(params)

    elif action == 'export_stl':
        return export_stl(params)

    elif action == 'get_parameters':
        return get_parameters(params)

    elif action == 'set_parameter':
        return set_parameter(params)

    else:
        raise ValueError(f'Unknown action: {action}')

# ── Fusion API Operations ─────────────────────────────────────
def create_sketch(params):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    plane_name = params.get('plane', 'xy')

    plane_map = {
        'xy': root.xYConstructionPlane,
        'xz': root.xZConstructionPlane,
        'yz': root.yZConstructionPlane,
    }
    plane = plane_map.get(plane_name)
    if not plane:
        raise ValueError(f'Invalid plane: {plane_name}. Use xy, xz, or yz.')

    sketch = root.sketches.add(plane)
    sketch.name = params.get('name', sketch.name)
    return {'sketch_name': sketch.name, 'plane': plane_name}

def create_rectangle(params):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    sketch_name = params.get('sketch_name')

    sketch = None
    for s in root.sketches:
        if s.name == sketch_name:
            sketch = s
            break
    if not sketch:
        raise ValueError(f'Sketch not found: {sketch_name}')

    x1, y1 = params.get('x1', 0), params.get('y1', 0)
    x2, y2 = params.get('x2', 5), params.get('y2', 5)

    lines = sketch.sketchCurves.sketchLines
    lines.addTwoPointRectangle(
        adsk.core.Point3D.create(x1, y1, 0),
        adsk.core.Point3D.create(x2, y2, 0)
    )
    return {
        'sketch_name': sketch_name,
        'rectangle': {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
    }

def extrude_profile(params):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    sketch_name = params.get('sketch_name')
    distance_cm = params.get('distance_cm', 1.0)
    operation = params.get('operation', 'new_body')

    sketch = None
    for s in root.sketches:
        if s.name == sketch_name:
            sketch = s
            break
    if not sketch:
        raise ValueError(f'Sketch not found: {sketch_name}')

    profile_idx = params.get('profile_index', 0)
    if sketch.profiles.count <= profile_idx:
        raise ValueError(
            f'Profile index {profile_idx} not found. '
            f'Sketch has {sketch.profiles.count} profiles.'
        )
    profile = sketch.profiles.item(profile_idx)

    op_map = {
        'new_body': adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        'join': adsk.fusion.FeatureOperations.JoinFeatureOperation,
        'cut': adsk.fusion.FeatureOperations.CutFeatureOperation,
        'intersect': adsk.fusion.FeatureOperations.IntersectFeatureOperation,
    }
    feat_op = op_map.get(operation, op_map['new_body'])

    extrudes = root.features.extrudeFeatures
    dist = adsk.core.ValueInput.createByReal(distance_cm)
    extrude = extrudes.addSimple(profile, dist, feat_op)

    return {
        'feature_name': extrude.name,
        'distance_cm': distance_cm,
        'operation': operation,
        'body_count': root.bRepBodies.count
    }

def fillet_edges(params):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    radius_cm = params.get('radius_cm', 0.1)
    body_index = params.get('body_index', 0)

    if root.bRepBodies.count <= body_index:
        raise ValueError(f'Body index {body_index} not found.')

    body = root.bRepBodies.item(body_index)
    edge_collection = adsk.core.ObjectCollection.create()

    edge_indices = params.get('edge_indices', None)
    if edge_indices:
        for idx in edge_indices:
            if idx < body.edges.count:
                edge_collection.add(body.edges.item(idx))
    else:
        for edge in body.edges:
            edge_collection.add(edge)

    fillets = root.features.filletFeatures
    fillet_input = fillets.createInput()
    fillet_input.isRollingBallCorner = True
    fillet_input.edgeSetInputs.addConstantRadiusEdgeSet(
        edge_collection,
        adsk.core.ValueInput.createByReal(radius_cm),
        True
    )
    fillet = fillets.add(fillet_input)
    return {'feature_name': fillet.name, 'radius_cm': radius_cm}

def export_stl(params):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    filepath = params.get('filepath', '')

    if not filepath:
        raise ValueError('filepath is required')

    export_mgr = design.exportManager
    stl_opts = export_mgr.createSTLExportOptions(root, filepath)
    stl_opts.meshRefinement = \
        adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
    export_mgr.execute(stl_opts)
    return {'exported': filepath}

def get_parameters(params):
    design = adsk.fusion.Design.cast(app.activeProduct)
    result = []
    for i in range(design.allParameters.count):
        p = design.allParameters.item(i)
        result.append({
            'name': p.name,
            'value': p.value,
            'expression': p.expression,
            'unit': p.unit
        })
    return {'parameters': result}

def set_parameter(params):
    design = adsk.fusion.Design.cast(app.activeProduct)
    name = params.get('name')
    expression = params.get('expression')

    p = design.allParameters.itemByName(name)
    if not p:
        raise ValueError(f'Parameter not found: {name}')
    p.expression = str(expression)
    return {'name': name, 'new_expression': p.expression, 'value': p.value}

# ── Add-in Lifecycle ──────────────────────────────────────────
def run(context):
    global app, ui, custom_event, stop_flag, http_server
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Register CustomEvent
        custom_event = app.registerCustomEvent(CUSTOM_EVENT_ID)
        handler = BridgeEventHandler()
        custom_event.add(handler)
        handlers.append(handler)

        # Start HTTP server on background thread
        http_server = HTTPServer(('127.0.0.1', BRIDGE_PORT), BridgeRequestHandler)
        stop_flag = threading.Event()
        server_thread = threading.Thread(
            target=http_server.serve_forever,
            daemon=True
        )
        server_thread.start()

        ui.messageBox(f'AI Bridge started on port {BRIDGE_PORT}')
    except:
        if ui:
            ui.messageBox(f'Bridge startup failed:\n{traceback.format_exc()}')

def stop(context):
    global http_server, custom_event
    try:
        if http_server:
            http_server.shutdown()
        if handlers:
            custom_event.remove(handlers[0])
        if stop_flag:
            stop_flag.set()
        app.unregisterCustomEvent(CUSTOM_EVENT_ID)
    except:
        if ui:
            ui.messageBox(f'Bridge shutdown error:\n{traceback.format_exc()}')
```

**Step 3: Install the add-in.** Copy the entire `fusion-addin/` folder to Fusion's AddIns directory:

- **Windows**: `%APPDATA%\Autodesk\Autodesk Fusion\API\AddIns\`
- **Mac**: `~/Library/Application Support/Autodesk/Autodesk Fusion/API/AddIns/`

Or create `scripts/install_addin.py`:

```python
import shutil, os, sys

src = os.path.join(os.path.dirname(__file__), '..', 'fusion-addin')

if sys.platform == 'win32':
    dst = os.path.join(os.environ['APPDATA'],
                       'Autodesk', 'Autodesk Fusion', 'API',
                       'AddIns', 'FusionAIBridge')
else:
    dst = os.path.expanduser(
        '~/Library/Application Support/Autodesk/'
        'Autodesk Fusion/API/AddIns/FusionAIBridge')

if os.path.exists(dst):
    shutil.rmtree(dst)
shutil.copytree(src, dst)
print(f'Installed to: {dst}')
```

Then in Fusion: **Utilities tab → Add-ins (Shift+S) → My Add-ins → FusionAIBridge → Run**.

### Building the MCP server

Save as `mcp-server/server.py`:

```python
from mcp.server.fastmcp import FastMCP
import httpx
import json

BRIDGE_URL = "http://127.0.0.1:9876"

mcp = FastMCP(
    "Fusion360Assistant",
    instructions=(
        "You are a CAD assistant controlling Autodesk Fusion 360. "
        "Use the available tools to create and modify 3D models. "
        "All dimensions are in centimeters unless stated otherwise. "
        "Always create a sketch before extruding."
    ),
)

# ── Bridge Communication ──────────────────────────────────────
def send_to_fusion(action: str, params: dict = None) -> dict:
    """Send a command to the Fusion 360 bridge and return the result."""
    payload = {"action": action, "params": params or {}}
    try:
        response = httpx.post(BRIDGE_URL, json=payload, timeout=35.0)
        return response.json()
    except httpx.ConnectError:
        return {
            "success": False,
            "error": "Cannot connect to Fusion 360. Is the add-in running?"
        }
    except httpx.TimeoutException:
        return {"success": False, "error": "Fusion 360 command timed out."}

# ── WORK MODE TOOLS (Pass 1) ─────────────────────────────────
@mcp.tool()
def ping() -> str:
    """Check if Fusion 360 is connected and responsive."""
    result = send_to_fusion("ping")
    if result.get("success") and result.get("data", {}).get("pong"):
        return "Fusion 360 is connected and ready."
    return f"Connection failed: {result.get('error', 'Unknown error')}"

@mcp.tool()
def create_sketch(plane: str = "xy", name: str = "") -> str:
    """Create a new sketch on a construction plane.

    Args:
        plane: Construction plane — 'xy', 'xz', or 'yz'
        name: Optional name for the sketch
    """
    result = send_to_fusion("create_sketch", {"plane": plane, "name": name})
    if result.get("success"):
        return json.dumps(result["data"])
    return f"Error: {result.get('error')}"

@mcp.tool()
def create_rectangle(
    sketch_name: str,
    x1: float = 0, y1: float = 0,
    x2: float = 5, y2: float = 5
) -> str:
    """Draw a rectangle in an existing sketch.

    Args:
        sketch_name: Name of the target sketch
        x1: Lower-left X coordinate (cm)
        y1: Lower-left Y coordinate (cm)
        x2: Upper-right X coordinate (cm)
        y2: Upper-right Y coordinate (cm)
    """
    result = send_to_fusion("create_rectangle", {
        "sketch_name": sketch_name,
        "x1": x1, "y1": y1, "x2": x2, "y2": y2
    })
    if result.get("success"):
        return json.dumps(result["data"])
    return f"Error: {result.get('error')}"

@mcp.tool()
def extrude(
    sketch_name: str,
    distance_cm: float,
    operation: str = "new_body",
    profile_index: int = 0
) -> str:
    """Extrude a sketch profile into a 3D body.

    Args:
        sketch_name: Name of the sketch containing the profile
        distance_cm: Extrusion distance in centimeters
        operation: 'new_body', 'join', 'cut', or 'intersect'
        profile_index: Index of the profile to extrude (0 for first)
    """
    result = send_to_fusion("extrude", {
        "sketch_name": sketch_name,
        "distance_cm": distance_cm,
        "operation": operation,
        "profile_index": profile_index,
    })
    if result.get("success"):
        return json.dumps(result["data"])
    return f"Error: {result.get('error')}"

@mcp.tool()
def fillet_edges(
    radius_cm: float,
    body_index: int = 0,
    edge_indices: list[int] | None = None
) -> str:
    """Apply a fillet (rounded edge) to edges of a body.

    Args:
        radius_cm: Fillet radius in centimeters
        body_index: Index of the body (0 for first body)
        edge_indices: Specific edge indices to fillet (None = all edges)
    """
    result = send_to_fusion("fillet_edges", {
        "radius_cm": radius_cm,
        "body_index": body_index,
        "edge_indices": edge_indices,
    })
    if result.get("success"):
        return json.dumps(result["data"])
    return f"Error: {result.get('error')}"

@mcp.tool()
def set_parameter(name: str, expression: str) -> str:
    """Modify a design parameter by name.

    Args:
        name: Parameter name (e.g., 'Length', 'd1')
        expression: New value expression (e.g., '50 mm', '2 in')
    """
    result = send_to_fusion("set_parameter", {
        "name": name, "expression": expression
    })
    if result.get("success"):
        return json.dumps(result["data"])
    return f"Error: {result.get('error')}"

@mcp.tool()
def get_parameters() -> str:
    """List all design parameters with their current values."""
    result = send_to_fusion("get_parameters", {})
    if result.get("success"):
        return json.dumps(result["data"], indent=2)
    return f"Error: {result.get('error')}"

@mcp.tool()
def export_stl(filepath: str) -> str:
    """Export the current design as an STL file.

    Args:
        filepath: Full path for the output STL file
    """
    result = send_to_fusion("export_stl", {"filepath": filepath})
    if result.get("success"):
        return json.dumps(result["data"])
    return f"Error: {result.get('error')}"

# ── Entry point ───────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### Connecting to each AI host

**Claude Desktop** (native MCP — easiest path). Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fusion360": {
      "command": "python",
      "args": ["/absolute/path/to/fusion-ai-assistant/mcp-server/server.py"],
      "env": {}
    }
  }
}
```

Config file locations — Windows: `%APPDATA%\Claude\claude_desktop_config.json` / Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`. Restart Claude Desktop after editing. Your Fusion 360 tools appear automatically in the tool menu.

**OpenAI / ChatGPT.** OpenAI's Responses API supports MCP natively but only for **remote HTTP servers**. To use it, run your MCP server with HTTP transport instead of stdio:

```python
# In server.py, change the entry point:
if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
```

Then in your OpenAI API call:

```python
from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-4o",
    tools=[{
        "type": "mcp",
        "server_label": "fusion360",
        "server_url": "http://127.0.0.1:8000/mcp",
        "require_approval": "never",
    }],
    input="Create a 50mm x 30mm x 10mm box",
)
```

For stdio-based local use, use the **OpenAI Agents SDK** which supports stdio MCP servers directly.

**Google Gemini.** The `google-genai` SDK accepts an MCP `ClientSession` as a tool. This is experimental but functional:

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai

client = genai.Client()  # Uses GEMINI_API_KEY env var

async def run():
    params = StdioServerParameters(
        command="python",
        args=["/path/to/mcp-server/server.py"]
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents="Create a mounting bracket 80mm x 40mm x 3mm",
                config=genai.types.GenerateContentConfig(
                    tools=[session],  # Pass MCP session directly
                ),
            )
            print(response.text)

asyncio.run(run())
```

**Provider-agnostic abstraction** libraries like **PydanticAI** and **LangChain MCP Adapters** let you swap providers with a single line change, which is ideal if you want to experiment across all three.

---

## 3. Tool design principles that prevent debugging nightmares

### Map tools to atomic Fusion operations

Each MCP tool should correspond to **one logical Fusion operation**. A tool called `create_bracket` that internally creates a sketch, draws a rectangle, extrudes it, and adds fillets will break in unpredictable ways when any step fails. Instead, expose `create_sketch`, `draw_rectangle`, `extrude`, and `fillet_edges` as separate tools. Let the AI compose them.

This mirrors how Fusion's own timeline works — each feature is an independent, undoable operation.

### Input validation patterns

Validate inputs **in the MCP server** (before sending to Fusion) and **in the add-in** (before calling API). Double validation catches both AI hallucinations and bridge protocol errors.

```python
# In the MCP server tool definition:
@mcp.tool()
def extrude(
    sketch_name: str,
    distance_cm: float,
    operation: str = "new_body",
    profile_index: int = 0
) -> str:
    """Extrude a sketch profile into a 3D body."""
    # MCP-level validation
    if distance_cm <= 0 or distance_cm > 100:
        return "Error: distance_cm must be between 0 and 100 cm"
    if operation not in ("new_body", "join", "cut", "intersect"):
        return f"Error: invalid operation '{operation}'"
    if profile_index < 0:
        return "Error: profile_index must be non-negative"

    result = send_to_fusion("extrude", {
        "sketch_name": sketch_name,
        "distance_cm": distance_cm,
        "operation": operation,
        "profile_index": profile_index,
    })
    # ...
```

In the Fusion add-in `execute_command`, validate again that the sketch exists, the profile index is in range, and the body count matches expectations. Return structured error messages that help the AI self-correct.

### Naming conventions and mode categorization

Use a consistent prefix system that makes tool purpose immediately obvious:

- **Work Mode**: `create_sketch`, `draw_rectangle`, `draw_circle`, `extrude`, `revolve`, `fillet_edges`, `chamfer_edges`, `set_parameter`, `get_parameters`
- **Utility Mode**: `export_stl`, `export_step`, `export_dxf`, `get_bom`, `list_bodies`, `list_components`, `save_document`, `create_component`
- **Creative Mode**: `parametric_sweep`, `generate_pattern`, `random_variation`, `batch_export_variations`

Tool descriptions are critical — the AI reads them to decide which tool to use. Write descriptions as if explaining the tool to a junior engineer: what it does, when to use it, and what constraints apply.

### Return structured results

Always return JSON with consistent structure. Include enough context for the AI to make its next decision:

```json
{
  "success": true,
  "data": {
    "feature_name": "Extrude1",
    "distance_cm": 2.5,
    "operation": "new_body",
    "body_count": 1,
    "sketch_name": "Sketch1"
  }
}
```

On errors, include actionable information:

```json
{
  "success": false,
  "error": "Profile index 2 not found. Sketch 'Sketch1' has 1 profile(s).",
  "suggestion": "Use profile_index=0 for the first profile."
}
```

---

## 4. Three development passes from minimal to generative

### Pass 1 — Minimal reliable CAD (get this working first)

The goal is a system where the AI can create basic 3D geometry reliably. Start with these **eight core tools**:

| Tool | Fusion API Calls | What It Does |
|------|-----------------|--------------|
| `create_sketch` | `sketches.add(plane)` | Creates an empty sketch on XY/XZ/YZ |
| `draw_rectangle` | `sketchLines.addTwoPointRectangle()` | Draws a closed rectangle in a sketch |
| `draw_circle` | `sketchCircles.addByCenterRadius()` | Draws a circle in a sketch |
| `extrude` | `extrudeFeatures.addSimple()` | Extrudes a profile into a 3D body |
| `revolve` | `revolveFeatures.add()` | Revolves a profile around an axis |
| `fillet_edges` | `filletFeatures.add()` | Rounds edges of a body |
| `chamfer_edges` | `chamferFeatures.add()` | Adds angled cuts to edges |
| `set_parameter` | `param.expression = value` | Modifies a named parameter |

**Testing strategy**: Start with `ping` to verify connectivity. Then test the sequence: `create_sketch("xy")` → `draw_rectangle(sketch_name, 0, 0, 5, 3)` → `extrude(sketch_name, 2)`. If this produces a 50mm × 30mm × 20mm box in Fusion, Pass 1 is complete.

Add `revolve` by exposing axis line creation within sketches. The revolve input requires a sketch profile and an axis line — both must exist in the same sketch.

```python
# Add-in side: revolve implementation
def revolve_profile(params):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    sketch_name = params.get('sketch_name')
    angle_degrees = params.get('angle_degrees', 360)
    axis_line_index = params.get('axis_line_index', 0)

    sketch = find_sketch(root, sketch_name)
    profile = sketch.profiles.item(params.get('profile_index', 0))
    axis = sketch.sketchCurves.sketchLines.item(axis_line_index)

    revolves = root.features.revolveFeatures
    rev_input = revolves.createInput(
        profile, axis,
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    import math
    angle = adsk.core.ValueInput.createByReal(
        math.radians(angle_degrees)
    )
    rev_input.setAngleExtent(False, angle)
    rev = revolves.add(rev_input)
    return {'feature_name': rev.name}
```

### Pass 2 — Workflow and manufacturing utilities

Once core geometry works, add automation tools that save real engineering time:

**Export tools**: STEP (`exportManager.createSTEPExportOptions`), STL (per-body or whole component), DXF (via `sketch.saveAsDXF(path)` for individual sketches). Each export format maps to a single API call.

**BOM extraction**: Walk the component tree, count occurrences, aggregate volumes. Return as structured JSON that the AI can format as a table or CSV.

```python
# Add-in side: BOM extraction
def extract_bom(params):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    bom = {}
    for occ in root.allOccurrences:
        comp = occ.component
        name = comp.name
        if name not in bom:
            bom[name] = {
                'name': name,
                'instances': 0,
                'bodies': comp.bRepBodies.count,
                'volume_cm3': sum(
                    b.volume for b in comp.bRepBodies
                ) if comp.bRepBodies.count > 0 else 0
            }
        bom[name]['instances'] += 1
    return {'bom': list(bom.values()), 'total_components': len(bom)}
```

**Component organization**: `create_component`, `rename_component`, `move_body_to_component` — these help the AI structure multi-part assemblies.

**File management**: `save_document`, `save_as`, `open_document`, `list_recent` — useful for batch workflows.

### Pass 3 — Generative and advanced modeling

This pass unlocks the creative potential of AI + CAD. The key tools are:

**Parametric sweep**: Iterate over a range of parameter values, optionally exporting each variant. This combines `set_parameter` + `export_stl` in a loop.

```python
# MCP server side: parametric sweep tool
@mcp.tool()
def parametric_sweep(
    parameter_name: str,
    start: float,
    end: float,
    steps: int,
    export_dir: str = "",
    unit: str = "mm"
) -> str:
    """Generate multiple design variants by sweeping a parameter.

    Args:
        parameter_name: Name of the parameter to vary
        start: Starting value
        end: Ending value
        steps: Number of steps (variants to generate)
        export_dir: Directory to save STL exports (empty = no export)
        unit: Unit for the values ('mm', 'cm', 'in')
    """
    results = []
    for i in range(steps):
        value = start + (end - start) * i / max(steps - 1, 1)
        expr = f"{value} {unit}"
        set_result = send_to_fusion("set_parameter", {
            "name": parameter_name, "expression": expr
        })

        variant = {"step": i, "value": value, "expression": expr}
        if export_dir:
            filepath = f"{export_dir}/{parameter_name}_{value:.1f}{unit}.stl"
            export_result = send_to_fusion("export_stl", {
                "filepath": filepath
            })
            variant["exported"] = filepath
        results.append(variant)

    return json.dumps({"sweep": results, "total_variants": steps})
```

**Pattern generation**: Circular and rectangular array patterns using Fusion's `RectangularPatternFeatures` and `CircularPatternFeatures`. **Topology-inspired geometry**: While Fusion's generative design requires the commercial license, you can approximate it by creating randomized organic forms using splines and lofts, controlled by parameter seeds.

---

## 5. Three modes with distinct safety boundaries

### Work Mode — reliable engineering

Work Mode is the default. Every tool call should be predictable and reversible. Design constraints for Work Mode tools:

- **All inputs must be validated** before execution. Reject out-of-range dimensions (negative lengths, radii larger than the body, etc.).
- **Each operation must be a single timeline entry** so it can be undone with Ctrl+Z.
- **No batch operations** — the AI should call tools one at a time and verify each result before proceeding.
- **Read-before-write** — encourage the AI to call `get_parameters` or `list_bodies` before modifying anything.

Work Mode tools: `create_sketch`, `draw_rectangle`, `draw_circle`, `draw_line`, `draw_arc`, `extrude`, `revolve`, `fillet_edges`, `chamfer_edges`, `set_parameter`, `get_parameters`, `list_bodies`, `list_components`.

### Utility Mode — workflow automation

Utility Mode tools perform batch operations and I/O. They are less dangerous than geometry creation because most are read-only or export-only, but file operations need care.

- **Export tools should never overwrite without confirmation.** Check if the file exists and return a warning.
- **BOM and parameter tools are read-only** — safe by default.
- **File management tools** (save, rename) should include a dry-run option that shows what would happen.

Utility Mode tools: `export_stl`, `export_step`, `export_dxf`, `get_bom`, `save_document`, `create_component`, `rename_component`, `get_document_info`.

### Creative Mode — experimentation allowed

Creative Mode relaxes safety constraints to enable generative exploration. The AI should be able to create many variants quickly, accept failures, and iterate.

- **Batch operations are allowed** — sweeps, multi-variant generation, pattern arrays.
- **Failures are non-fatal** — if one variant fails, log it and continue.
- **Parameter ranges can be wider** — allow extreme values that might produce unusual geometry.
- **Automatic cleanup** — after a creative session, provide a tool to delete all generated bodies/components.

Creative Mode tools: `parametric_sweep`, `generate_pattern`, `random_variation`, `batch_export`, `cleanup_variants`.

### Mode enforcement

The MCP server controls which tools are available. The simplest approach is a mode flag that filters tool visibility:

```python
# In server.py, control tool registration based on mode
import os

CURRENT_MODE = os.environ.get("FUSION_AI_MODE", "work")

if CURRENT_MODE in ("work", "utility", "creative"):
    # Work tools always available
    register_work_tools(mcp)

if CURRENT_MODE in ("utility", "creative"):
    register_utility_tools(mcp)

if CURRENT_MODE == "creative":
    register_creative_tools(mcp)
```

Alternatively, use a `set_mode` tool that dynamically adjusts available operations at runtime, or use MCP's tool annotations to mark tools with `destructiveHint: true` and `readOnlyHint: true`.

---

## 6. Example workflows that exercise each mode

### Work Mode: "Create a mounting bracket with specific dimensions"

The user says: *"Create an L-shaped mounting bracket, 80mm tall, 40mm wide, 3mm thick, with 5mm fillets on the inside corner and two M5 mounting holes."*

The AI's tool call sequence:

1. `create_sketch(plane="xz", name="bracket_profile")` — XZ plane for an L-profile
2. `draw_line(sketch_name="bracket_profile", x1=0, y1=0, x2=4, y2=0)` — bottom leg (40mm = 4cm)
3. `draw_line(...)` — continue drawing the L-shaped profile with 6 more lines (0.3cm thickness)
4. `extrude(sketch_name="bracket_profile", distance_cm=4, operation="new_body")` — 40mm depth
5. `fillet_edges(radius_cm=0.5, body_index=0, edge_indices=[3, 7])` — 5mm inside fillets
6. `create_sketch(plane="xy", name="holes")` — sketch on the flat face
7. `draw_circle(sketch_name="holes", center_x=1, center_y=2, radius_cm=0.25)` — M5 clearance hole
8. `draw_circle(sketch_name="holes", center_x=3, center_y=2, radius_cm=0.25)` — second hole
9. `extrude(sketch_name="holes", distance_cm=0.3, operation="cut")` — cut through

Each step returns confirmation. If the profile doesn't close properly in step 3, the AI gets an error when trying to extrude (no profiles found) and can self-correct.

### Utility Mode: "Export all bodies and generate a BOM"

The user says: *"Export every body as STL, then give me a BOM with volumes."*

1. `list_bodies()` → returns `[{name: "Body1", index: 0}, {name: "Body2", index: 1}]`
2. `export_stl(filepath="C:/exports/Body1.stl", body_index=0)`
3. `export_stl(filepath="C:/exports/Body2.stl", body_index=1)`
4. `get_bom()` → returns structured BOM with component names, instance counts, and volumes in cm³

The AI formats the BOM as a markdown table for the user.

### Creative Mode: "Generate 5 phone stand variations"

The user says: *"Create a phone stand and generate 5 variations by sweeping the back angle from 50° to 80°."*

1. AI creates the base phone stand using Work Mode tools (sketch, extrude, fillet)
2. `set_parameter(name="back_angle", expression="50 deg")` — set initial angle
3. `parametric_sweep(parameter_name="back_angle", start=50, end=80, steps=5, export_dir="C:/exports/phone_stands", unit="deg")`

The sweep tool internally calls `set_parameter` and `export_stl` five times, producing five STL files. The AI reports: *"Generated 5 variants: 50°, 57.5°, 65°, 72.5°, 80°. Files saved to C:/exports/phone_stands/."*

---

## 7. Running everything on your local workstation

### Startup sequence

The system requires three things running simultaneously in the correct order:

1. **Start Fusion 360.** Open a design document (the add-in needs an active product).
2. **Load the add-in.** Shift+S → Add-Ins tab → FusionAIBridge → Run. You should see "AI Bridge started on port 9876".
3. **Start the AI host.** For Claude Desktop, just open it — MCP servers start automatically from config. For programmatic use, run your script.

**Windows startup batch file** (`scripts/start_all.bat`):

```batch
@echo off
echo Starting Fusion 360 AI Assistant...
echo.
echo Step 1: Make sure Fusion 360 is running with the add-in loaded.
echo Step 2: Testing bridge connection...

curl -s http://127.0.0.1:9876/ >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Cannot reach Fusion bridge on port 9876.
    echo Load the FusionAIBridge add-in in Fusion 360 first.
    pause
    exit /b 1
)

echo Bridge is responding!
echo Step 3: Starting MCP server...
cd /d "%~dp0\..\mcp-server"
python server.py
```

### Testing the bridge connection

Before connecting the AI, verify the bridge works with a simple curl or Python test:

```bash
# Health check
curl http://127.0.0.1:9876/

# Send a ping command
curl -X POST http://127.0.0.1:9876/ \
  -H "Content-Type: application/json" \
  -d '{"action": "ping", "params": {}}'
```

Expected response: `{"success": true, "data": {"pong": true}}`

**Python test script** (`tests/test_bridge.py`):

```python
import httpx, json

BRIDGE = "http://127.0.0.1:9876"

def test_ping():
    r = httpx.post(BRIDGE, json={"action": "ping", "params": {}})
    data = r.json()
    assert data["success"] is True
    print("✓ Ping successful")

def test_create_and_extrude():
    # Create sketch
    r = httpx.post(BRIDGE, json={
        "action": "create_sketch",
        "params": {"plane": "xy", "name": "TestSketch"}
    })
    assert r.json()["success"]
    print("✓ Sketch created")

    # Draw rectangle
    r = httpx.post(BRIDGE, json={
        "action": "create_rectangle",
        "params": {"sketch_name": "TestSketch",
                   "x1": 0, "y1": 0, "x2": 3, "y2": 2}
    })
    assert r.json()["success"]
    print("✓ Rectangle drawn")

    # Extrude
    r = httpx.post(BRIDGE, json={
        "action": "extrude",
        "params": {"sketch_name": "TestSketch", "distance_cm": 1.5}
    })
    assert r.json()["success"]
    print("✓ Extrusion complete")

if __name__ == "__main__":
    test_ping()
    test_create_and_extrude()
    print("\nAll tests passed!")
```

### Debugging common issues

**"Cannot connect to Fusion 360"** — The add-in isn't running or port 9876 is blocked. Check Windows Firewall for localhost exceptions. Try a different port in both `config.json` and add-in code.

**"Timeout waiting for main thread"** — Fusion is busy (running another command, rendering, or showing a dialog). The 30-second timeout in the bridge handler may need increasing for heavy operations. Also ensure you call `ui.commandDefinitions.itemById('SelectCommand').execute()` in the event handler to terminate any active command.

**"Profile index not found"** — The sketch geometry doesn't form a closed loop. Verify that your rectangle/circle calls produce closed shapes by listing sketch profiles after drawing.

**Fusion crashes on API call** — Almost always a threading violation. Verify that **no Fusion API call happens outside the CustomEvent handler's `notify()` method**. Use Python's `logging` module (writing to a file) instead of `ui.messageBox()` for debugging in background threads.

**MCP Inspector** is invaluable for debugging. Run `npx @modelcontextprotocol/inspector` and connect to your MCP server to test tool calls interactively without needing the AI host.

---

## 8. Safety, validation, and recovering from failures

### The Fusion timeline is your undo system

Every feature operation (extrude, fillet, chamfer) creates a timeline entry. Fusion's built-in Ctrl+Z undoes the last timeline operation. For programmatic rollback:

```python
# Add-in side: undo the last N operations
def undo_operations(params):
    design = adsk.fusion.Design.cast(app.activeProduct)
    count = params.get('count', 1)
    timeline = design.timeline
    for _ in range(count):
        if timeline.count > 0:
            # Move timeline marker back
            timeline.moveToEnd()
            # Alternatively, delete the last feature:
            last_item = timeline.item(timeline.count - 1)
            last_item.entity.deleteMe()
    return {'undone': count, 'remaining_features': timeline.count}
```

Expose this as an `undo` tool so the AI can recover from mistakes.

### Input validation at every layer

**Layer 1 — MCP server (schema validation).** FastMCP auto-validates types via Python annotations and Pydantic. A `distance_cm: float` parameter rejects strings automatically.

**Layer 2 — MCP server (semantic validation).** Check that values make engineering sense:

```python
def validate_dimension(value_cm: float, name: str, min_cm=0.001, max_cm=100):
    if value_cm < min_cm:
        raise ValueError(
            f"{name} = {value_cm}cm is too small (min: {min_cm}cm / {min_cm*10}mm)"
        )
    if value_cm > max_cm:
        raise ValueError(
            f"{name} = {value_cm}cm is too large (max: {max_cm}cm / {max_cm*10}mm)"
        )
```

**Layer 3 — Add-in (existence validation).** Before operating on a sketch, body, or parameter, verify it exists and return a clear error if not.

### Mode-based safety constraints

```python
# Safety matrix by mode
SAFETY_RULES = {
    "work": {
        "max_extrude_cm": 50,
        "allow_batch": False,
        "allow_delete_body": False,
        "require_confirmation_for": ["cut", "intersect"],
    },
    "utility": {
        "max_extrude_cm": 50,
        "allow_batch": True,
        "allow_delete_body": False,
        "require_confirmation_for": [],
    },
    "creative": {
        "max_extrude_cm": 200,
        "allow_batch": True,
        "allow_delete_body": True,
        "require_confirmation_for": [],
    },
}
```

In Work Mode, destructive operations like `cut` extrusions should return a confirmation prompt. In Creative Mode, anything goes — but wrap batch operations in a try/except that logs failures and continues.

### Graceful failure in the event handler

The CustomEvent handler is the most critical code path. If it throws an unhandled exception, the bridge thread hangs forever waiting on `result_event`. Always wrap the handler body in try/except and ensure the `result_event.set()` fires in a `finally` block:

```python
class BridgeEventHandler(adsk.core.CustomEventHandler):
    def notify(self, args):
        request_id = None
        try:
            # ... process command ...
        except Exception as e:
            if request_id:
                result_store[request_id] = {
                    'success': False,
                    'error': str(e)
                }
        finally:
            if request_id and request_id in result_events:
                result_events[request_id].set()  # Always unblock the bridge
```

This guarantees the HTTP response is always sent, even if the Fusion operation fails catastrophically.

---

## 9. Where to go after the three passes

### Near-term additions (Pass 4)

**Multi-document workflows** open up assembly-level automation. Fusion's API can open documents with `app.documents.open(filepath)`, switch between them, and create joints between components from different files. Add tools like `open_document`, `insert_component`, and `create_joint`.

**Drawing and drafting automation** uses the `adsk.fusion.Drawing` API (added in recent Fusion updates) to generate 2D drawings from 3D models — orthographic views, dimensions, title blocks. This is extremely valuable for manufacturing workflows.

**Sketch constraints** (coincident, tangent, parallel, dimensional) make sketches fully parametric. Expose `sketch.geometricConstraints.addCoincident()` and `sketch.dimensionConstraints.addDistanceDimension()` as tools. This is the difference between fragile sketches and robust parametric ones.

### Medium-term capabilities (Pass 5)

**Simulation integration** through `adsk.cam` and the simulation workspace API. Create stress analysis studies, set boundary conditions, run simulations, and extract results. The AI could iterate: design → simulate → modify parameters → re-simulate.

**CAM toolpath generation** is powerful for CNC workflows. Tools for creating setups, selecting operations (2D contour, 3D adaptive, drilling), setting feeds/speeds, generating toolpaths, and post-processing G-code. The `adsk.cam` module provides `CAM.generateAllToolpaths()` and post-processing via `PostProcessInput`.

**Version control for designs** using Fusion's built-in versioning (`document.save("description")` creates a version) or external Git-based tracking of exported STEP files. The AI could tag versions with descriptions of what changed.

### Long-term vision

**Cloud collaboration** via Autodesk Platform Services (APS, formerly Forge). The APS REST API enables cloud-based file management, viewer embedding, and team collaboration. Your MCP server could expose tools for sharing designs, managing access, and triggering cloud-based operations.

**Multi-agent workflows** where one AI agent handles design, another handles manufacturing prep, and a third handles documentation. MCP's architecture naturally supports this — each agent connects to the same MCP server but uses different tool subsets.

**Custom machine learning** trained on your organization's design patterns. Feed parameter distributions and feature sequences from successful designs into a model that can suggest starting points for new projects. The MCP tool layer makes it straightforward to collect this training data.

---

## Conclusion

The architecture works because it respects Fusion 360's single-threaded constraint while giving AI models full access to its capabilities. The three-layer bridge (add-in → HTTP → MCP → AI) adds complexity but provides clean separation of concerns: the add-in handles thread safety and API access, the MCP server handles tool schemas and validation, and the AI host handles reasoning and composition.

**Start with Pass 1.** Get `create_sketch` → `draw_rectangle` → `extrude` working end-to-end. That single chain validates every layer of the architecture. Once you see a box appear in Fusion from an AI prompt, every subsequent tool is incremental.

The three-mode system (Work/Utility/Creative) isn't just organizational — it's a safety architecture. Work Mode's strict validation prevents the AI from destroying hours of CAD work with a hallucinated parameter. Creative Mode's relaxed constraints let the AI explore design spaces that would take a human days to iterate through. Build both, and you get the best of reliability and experimentation.

The existing open-source ecosystem is rich. Projects like **faust-machines/fusion360-mcp-server** (80 tools, PyPI package), **AuraFriday/Fusion-360-MCP-Server** (Autodesk App Store listing), and **zkbkb/fusion-mcp** (44 professional tools) demonstrate that this architecture is production-viable. Study their source code for patterns beyond what this guide covers — especially their approaches to error recovery, tool composition, and CAM integration.
