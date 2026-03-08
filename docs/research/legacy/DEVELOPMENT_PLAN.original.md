# ParamAItric Development Plan

ParamAItric will be implemented in three major development passes.

Each pass expands the toolset and capabilities.

---

# PASS 1 — Core Modeling

Goal:
Allow AI to generate simple printable parts reliably.

Tools to implement:

new_design  
create_sketch  
draw_circle  
draw_rectangle  
draw_line  
list_profiles  
extrude_profile  
export_stl

Example use cases:

• spacer  
• bracket  
• simple enclosure  
• cylindrical adapter  

Success criteria:

AI can produce a printable STL from a prompt.

---

# PASS 2 — Workflow Automation

Goal:
Automate repetitive CAD tasks.

Tools:

convert_bodies_to_components  
set_physical_material  
set_appearance  
rename_entities  
list_entities  
export_step  

Example use cases:

• preparing parts for CNC  
• converting design bodies to components  
• batch exporting  

---

# PASS 3 — Creative Modeling

Goal:
Enable exploratory modeling and design brainstorming.

Tools:

draw_spline  
loft_profiles  
revolve_profile  
pattern_features  
combine_bodies  
create_offset_planes  

Example use cases:

• decorative vases  
• organic shapes  
• design exploration  

---

# Operational Modes

The AI operates in three modes.

## Work Mode

Reliable engineering modeling.

Focus:
predictability

Used for:
3D printing parts and mechanical components.

---

## Utility Mode

Workflow automation.

Focus:
organization and export tasks.

Used for:
CNC prep, batch export, cleanup.

---

## Creative Mode

Experimental modeling.

Focus:
exploration and generative designs.

Used for:
decorative objects or brainstorming.