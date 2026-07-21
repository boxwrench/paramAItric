# Installing ParamAItric

Welcome! ParamAItric connects your AI assistant to Autodesk Fusion 360 so you can generate real, functional mechanical parts just by asking.

> **New to this?** This guide is written for non-developers, so every step is spelled out. If a step confuses you, paste it into your AI (Claude, ChatGPT, Gemini) and ask it to walk you through it. That is a normal way to use this guide, not cheating.

Because we are connecting two different pieces of software (Fusion 360 and an AI), the setup happens in two parts.

This guide describes the current setup as it exists today. It is still a manual, developer-style install:

- you clone the repo locally
- you create a Python virtual environment
- you configure your AI client to launch the MCP server from that clone
- you install and run the Fusion add-in separately

That is workable for early adopters, but it is not yet the final user experience the project is aiming for.

---

## One-command setup

Already cloned the repo? Skip the manual steps below and run the bootstrap script instead — it creates `.venv`, installs ParamAItric, links the Fusion add-in, writes the Claude Desktop config, and prints a final health check.

- **Windows (PowerShell):** `.\scripts\setup.ps1`
- **macOS/Linux (bash):** `./scripts/setup.sh`

Re-running either script is safe. If you have not cloned the repo yet, do the clone step in **Step 1** below first.

---

### Stuck? Ask your AI for help
If you get confused at any point in this guide, copy and paste this prompt into your AI (ChatGPT, Claude, Gemini, etc.):
> *"I am trying to install an open-source tool called ParamAItric. It connects my AI to Fusion 360 using an MCP server. I am reading the installation guide and I am stuck on [insert step here]. I don't have a lot of programming experience. Can you explain exactly what I need to do in simple terms?"*

---

## Prerequisites

Before starting, ensure you have the following installed on your computer:
1. **Autodesk Fusion 360**
2. **Python (version 3.11 or newer)**: [Download here](https://www.python.org/downloads/) (Make sure to check the box that says "Add python.exe to PATH" during installation on Windows).
3. **Git**: [Download here](https://git-scm.com/downloads) (Used to download the code).
4. **An MCP-compatible AI Client**: We recommend **Claude Desktop** or the **Cursor IDE**.

## Before You Start

It helps to know what each piece does:

- the repo clone contains the ParamAItric code
- the Python environment runs the local MCP server
- Claude Desktop or another MCP host starts that server
- the Fusion add-in is the local bridge into Fusion 360

You usually do not start the MCP server manually. Your AI client starts it using the config you provide.

---

## Step 1: Install the Fusion 360 Add-in

First, we need to tell Fusion 360 how to listen for commands from the AI.

1. Open your computer's terminal (Command Prompt on Windows, or Terminal on Mac).
2. Download the ParamAItric code by running:
   ```bash
   git clone https://github.com/boxwrench/paramAItric.git
   ```
   *(Note: replace the URL with the actual repository URL if different).*
3. Move into the downloaded folder and run the setup helper:
   ```bash
   cd paramAItric
   python scripts/install_paramaitric.py
   ```
   This prints a small setup dashboard, the exact Fusion add-in folder to select, and copy/paste
   MCP config snippets for Claude Desktop and Cursor.
   You can also run `python scripts/install_paramaitric.py --check` any time to get a quick
   pass/fail setup summary.
4. Register the add-in with Fusion automatically:
   ```bash
   python scripts/install_paramaitric.py --install-addin
   ```
   This links the add-in into Fusion 360's AddIns folder so it shows up in Fusion by itself —
   no folder picking needed. (Prefer manual? In Fusion: Utilities > Scripts and Add-Ins >
   Add-Ins > green **+** > select the `fusion_addin` folder shown by the setup helper.)
5. Open **Autodesk Fusion 360**, go to the **Utilities** tab, and click **Scripts and Add-Ins**.
6. In the **Add-Ins** tab you should see `FusionAIBridge`. Click on it, and hit the **Run** button at the bottom of the window.
   *(Tip: Check the "Run on Startup" box so you don't have to do this every time).*

    With "Run on Startup", the add-in boots before any design is open, so the bridge starts
    against a mock adapter. It upgrades itself to live Fusion automatically the moment you open
    or create a design — no Stop/Run needed. `GET /health` reports which mode is active
    (`"mode": "live"` or `"mock"`, with a hint while still in mock).

---

## Step 2: Set up the Python Server

Next, we need to prepare the engine that translates the AI's thoughts into Fusion commands.

1. Go back to your terminal in the `paramAItric` folder.
2. Create a "Virtual Environment" (a safe, isolated space for Python to install files):
   ```bash
   python -m venv .venv
   ```
3. Activate the virtual environment:
   * **On Windows:** `.venv\Scripts\activate`
   * **On Mac/Linux:** `source .venv/bin/activate`
   *(You should now see `(.venv)` at the start of your terminal line).*
4. Install the required files:
   ```bash
   pip install -e .
   ```
5. Run the setup helper again. The `Virtualenv` row should now show `OK`.
   ```bash
   python scripts/install_paramaitric.py
   ```

---

## Step 3: Connect your AI Client

Now we connect your AI to the Python server you just set up. ParamAItric is **AI-agnostic**, meaning you can use different models (Claude, GPT-4, Gemini) as long as your client supports the "MCP" protocol.

### Option A: Using Claude Desktop (Easiest)
1. Open Claude Desktop.
2. In the menu bar, go to **File > Settings** (or Claude > Preferences on Mac), and click on **Developer**.
3. Click **Edit Config**. This will open a file called `claude_desktop_config.json`.
4. Paste the Claude Desktop config snippet printed by:
   ```bash
   python scripts/install_paramaitric.py --print claude
   ```

   If you want ParamAItric to merge this entry into the Claude config file for you, run:
   ```bash
   python scripts/install_paramaitric.py --write-claude-config
   ```

It will look like this, but with your real local paths:

```json
{
  "mcpServers": {
    "paramaitric": {
      "command": "C:\\path\\to\\paramAItric\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.mcp_entrypoint"],
      "cwd": "C:\\path\\to\\paramAItric"
    }
  }
}
```
5. Save the file and **restart Claude Desktop**. Look for a little "plug" icon or "MCP" indicator to ensure it connected successfully.

### Option B: Using Cursor IDE (Lets you choose your AI model)
Cursor is a code editor with AI built-in. It allows you to select which AI model you want to use (Anthropic, OpenAI, Google).
1. Open Cursor.
2. Open the Settings (gear icon) and navigate to **Features > MCP**.
3. Click **+ Add New MCP Server**.
4. Set the Type to `command`.
5. Set the Name to `ParamAItric`.
6. Set the Command to the value printed by:
   ```bash
   python scripts/install_paramaitric.py --print cursor
   ```
7. Click Save. A green dot should appear indicating it is connected.

---

## Step 4: Restart and Verify

1. Restart Claude Desktop or Cursor after saving your MCP configuration.
2. Open Fusion 360 and make sure the ParamAItric add-in is running.
3. Ask your AI to run ParamAItric's novice-friendly first-run check.

Example prompt:

> *"Call the ParamAItric getting_started tool and explain what I should do next."*

If that succeeds, your MCP host is correctly launching the local ParamAItric server from this repo clone.

---

## Step 5: Make Your First Part

Everything is connected. Ensure Fusion 360 is open and the add-in is running.
Go to your AI (Claude Desktop or Cursor) and paste this exact prompt:

> *"Call the ParamAItric getting_started tool. If Fusion is ready, create a simple spacer that is 4cm wide, 4cm deep, and 0.5cm thick. Verify the geometry, then export it as an STL file."*

Watch as the AI plans the steps, reaches into Fusion 360, sketches the part, extrudes it, and exports it for you!

By default, exported STL files are saved to **`Documents/ParamAItric Exports`**. You can also ask for your Desktop or Downloads folder. (Other locations are blocked on purpose, so the AI can never write files in unexpected places.)

---

## Printing the part

Open the exported `.stl` file in your slicer (Cura, PrusaSlicer, Bambu Studio, or whatever came with your printer) and print as usual.

---

## Tips for Good Replacement Parts

- Measure the original part (or the space it fits) with a ruler; calipers are better if you have them. Millimeters or inches are both fine, the AI converts.
- If your AI app accepts images, photograph the removed part beside a ruler or flat on grid paper. Use bright, even light, keep the camera straight above it, and add a side view if thickness matters. Do not measure near live electrical parts, moving machinery, or hot surfaces.
- A photo can only support rough estimates. Confirm every dimension with a ruler or calipers before the part is built. The AI should ask for the fit-critical measurement first, then request the other measurements one at a time.
- For holes and sockets that must fit around something, add about 0.2 to 0.4 mm of clearance. The AI will suggest this too.
- If a part comes out slightly wrong, just tell the AI what to change (for example, "make the hole 1 mm bigger") and export again. Iterating is normal.

---

## What Happens In Later Sessions?

After the first setup, you normally do not repeat the install steps.

For a later session, the usual flow is:

1. Open Fusion 360.
2. Make sure the ParamAItric add-in is running.
3. Open or restart Claude Desktop (or your MCP host).
4. Ask for a ParamAItric health check.
5. Start your CAD request.

You do not need to recreate the virtual environment or re-edit the Claude config unless:

- the repo moved to a different folder
- the Python environment was deleted
- you changed machines

## Current Reality vs. Project Direction

Current reality:

- setup is still manual
- the MCP server is launched from a local clone of this repo
- the Fusion add-in must be installed and running locally

Project direction:

- one-click Claude Desktop installation via extension packaging
- less or no manual Python setup for end users
- a simpler first-run health check flow
- less distinction between "repo setup" and "use the product"
