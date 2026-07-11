# ParamAItric Quickstart

Get from "I need a replacement part" to a 3D-printable file — no CAD or programming experience needed.

Setup takes about 15 minutes and you only do it once. If anything here confuses you, paste the confusing step into your AI (Claude, ChatGPT, etc.) and ask it to walk you through it — that's a normal way to use this guide, not cheating.

## What you need installed first

1. **Autodesk Fusion 360** (free for personal use) — [autodesk.com/products/fusion-360](https://www.autodesk.com/products/fusion-360/personal)
2. **Python 3.11 or newer** — [python.org/downloads](https://www.python.org/downloads/). On Windows, tick **"Add python.exe to PATH"** during install.
3. **Claude Desktop** (or another MCP-capable AI app) — [claude.ai/download](https://claude.ai/download)
4. **Git** — [git-scm.com/downloads](https://git-scm.com/downloads)

## One-time setup

Open a terminal (Windows: press Start, type `cmd`, press Enter) and run these commands one at a time:

```bash
git clone https://github.com/boxwrench/paramAItric.git
cd paramAItric
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

(On Mac/Linux, the activate line is `source .venv/bin/activate`.)

Then connect the two ends:

```bash
python scripts/install_paramaitric.py --install-addin
python scripts/install_paramaitric.py --write-claude-config
```

The first command makes the add-in appear inside Fusion 360 automatically. The second connects Claude Desktop to ParamAItric (it will ask before writing anything).

Finally, flip the two switches:

1. **In Fusion 360:** Utilities tab → **Scripts and Add-Ins** → **Add-Ins** tab → click **FusionAIBridge** → **Run**. Tick **"Run on Startup"** so you never do this again.
2. **Restart Claude Desktop.**

Something not working? Run `python scripts/install_paramaitric.py --check` to see exactly what's missing and what to do about it. It also tells you whether Fusion is connected, in practice mode because no design is open, or not listening yet.

## Make your first part

With Fusion 360 open, paste this into Claude:

> Call the ParamAItric getting_started tool and explain what I should do next. Then create a simple spacer 40 mm wide, 40 mm deep, and 5 mm thick, and export it as an STL.

Claude will sketch the part in Fusion, verify it, and save the file. **Your STL lands in `Documents\ParamAItric Exports`** unless you ask for the Desktop or Downloads instead.

## Every time after that

1. Open Fusion 360 (the add-in starts by itself if you ticked Run on Startup).
2. Open Claude Desktop.
3. Describe the part you need, in plain language. You don't need to know part names — "something to hold a 20 mm pipe against a wall" works. Claude will help you measure and confirm sizes before building anything.

## Printing the part

Open the exported `.stl` file in your slicer — Cura, PrusaSlicer, Bambu Studio, or whatever came with your printer — and print as usual.

## Tips for good replacement parts

- Measure the original part (or the space it fits) with a ruler; calipers are better if you have them. Millimeters or inches are both fine — Claude converts.
- If your AI app accepts images, photograph the removed part beside a ruler or flat on grid paper. Use bright, even light, keep the camera straight above it, and add a side view if thickness matters. Do not measure near live electrical parts, moving machinery, or hot surfaces.
- A photo can only support rough estimates. Confirm every dimension with a ruler or calipers before Claude builds the part. Claude should ask for the fit-critical measurement first, then request only the other required measurements one at a time.
- For holes and sockets that must fit around something, add about 0.2–0.4 mm of clearance. Claude will suggest this too.
- If a part comes out slightly wrong, just tell Claude what to change ("make the hole 1 mm bigger") and export again. Iterating is normal.

Want the full developer-oriented guide? See [INSTALL.md](INSTALL.md).
