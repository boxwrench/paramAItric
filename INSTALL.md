# Installing ParamAItric

Welcome! ParamAItric connects your AI assistant to Autodesk Fusion 360 so you can generate real, functional mechanical parts just by asking.

Because we are connecting two different pieces of software (Fusion 360 and an AI), the setup happens in two parts. You don't need to be a programmer to set this up, but you will need to copy and paste a few commands into your computer's terminal.

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

---

## Step 1: Install the Fusion 360 Add-in

First, we need to tell Fusion 360 how to listen for commands from the AI.

1. Open your computer's terminal (Command Prompt on Windows, or Terminal on Mac).
2. Download the ParamAItric code by running:
   ```bash
   git clone https://github.com/boxwrench/paramAItric.git
   ```
   *(Note: replace the URL with the actual repository URL if different).*
3. Open **Autodesk Fusion 360**.
4. In the top ribbon, click on the **Utilities** tab.
5. Click on the **Scripts and Add-Ins** button (it looks like a little gear/scroll icon).
6. In the window that pops up, click the **Add-Ins** tab at the top.
7. Click the green **+** (Plus) button next to "My Add-Ins".
8. Navigate to the `paramAItric` folder you downloaded in step 2, open it, select the folder named `fusion_addin`, and click **Select Folder**.
9. You should now see `FusionAIBridge` in your list of Add-Ins. Click on it, and hit the **Run** button at the bottom of the window. 
   *(Tip: Check the "Run on Startup" box so you don't have to do this every time).*

---

## Step 2: Set up the Python Server

Next, we need to prepare the engine that translates the AI's thoughts into Fusion commands.

1. Go back to your terminal.
2. Navigate into the folder you just downloaded:
   ```bash
   cd paramAItric
   ```
3. Create a "Virtual Environment" (a safe, isolated space for Python to install files):
   ```bash
   python -m venv .venv
   ```
4. Activate the virtual environment:
   * **On Windows:** `.venv\Scripts\activate`
   * **On Mac/Linux:** `source .venv/bin/activate`
   *(You should now see `(.venv)` at the start of your terminal line).*
5. Install the required files:
   ```bash
   pip install -e .
   ```

---

## Step 3: Connect your AI Client

Now we connect your AI to the Python server you just set up. ParamAItric is **AI-agnostic**, meaning you can use different models (Claude, GPT-4, Gemini) as long as your client supports the "MCP" protocol.

### Option A: Using Claude Desktop (Easiest)
1. Open Claude Desktop.
2. In the menu bar, go to **File > Settings** (or Claude > Preferences on Mac), and click on **Developer**.
3. Click **Edit Config**. This will open a file called `claude_desktop_config.json`.
4. Paste the following configuration into the file. **You must replace `C:\\path\\to\\paramAItric` with the actual path on your computer where you downloaded the folder.** (Make sure to use double backslashes `\\` on Windows).

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
*(If you are on a Mac, the command path will look like `/path/to/paramAItric/.venv/bin/python`)*
5. Save the file and **restart Claude Desktop**. Look for a little "plug" icon or "MCP" indicator to ensure it connected successfully.

### Option B: Using Cursor IDE (Lets you choose your AI model)
Cursor is a code editor with AI built-in. It allows you to select which AI model you want to use (Anthropic, OpenAI, Google).
1. Open Cursor.
2. Open the Settings (gear icon) and navigate to **Features > MCP**.
3. Click **+ Add New MCP Server**.
4. Set the Type to `command`.
5. Set the Name to `ParamAItric`.
6. Set the Command to: `C:\path\to\paramAItric\.venv\Scripts\python.exe -m mcp_server.mcp_entrypoint` (Replace with your actual path).
7. Click Save. A green dot should appear indicating it is connected.

---

## Step 4: Make Your First Part!

Everything is connected. Ensure Fusion 360 is open and the add-in is running.
Go to your AI (Claude Desktop or Cursor) and paste this exact prompt:

> *"Check your MCP tools. Use the ParamAItric health check to ensure you can reach Fusion 360. If successful, create a simple spacer that is 4cm wide, 4cm deep, and 0.5cm thick. Verify the geometry, then export it to my Desktop as an STL file."*

Watch as the AI plans the steps, reaches into Fusion 360, sketches the part, extrudes it, and exports it for you!
