# Valve Handle Specification Extraction Template

Use this template when extracting CAD-relevant dimensions from valve manufacturer documentation.

---

## Document Metadata

```yaml
document_source: ""  # URL, PDF filename, or vendor catalog
valve_manufacturer: ""  # e.g., "Nibco", "Chemtrol", "Spears", "Hayward"
valve_model: ""  # e.g., "T-585-70-LF", "S-620", "F-619-RWS"
document_date: ""  # Date of specification
extracted_by: ""  # Person extracting data
extraction_date: ""  # Date of extraction
confidence_level: ""  # high/medium/low based on doc clarity
```

---

## Critical CAD Dimensions

### 1. Stem (Socket) Geometry

```yaml
stem_shape: ""  # square, hex, round_flat, double_d, splined
stem_across_flats_cm: 0.0  # Primary measurement for square/hex
stem_depth_cm: 0.0  # How deep the socket must engage
stem_tolerance_cm: 0.0  # Print clearance (typically 0.05-0.1cm)

# For round stems with flats (gas valves)
stem_diameter_cm: 0.0  # Full diameter
stem_flat_depth_cm: 0.0  # How much of the round is flattened

# Set screw details
set_screw_diameter_cm: 0.0  # Optional set screw
set_screw_thread_pitch: ""  # e.g., "M4", "#8-32"
set_screw_location: ""  # center, offset, height_from_base
```

### 2. Handle/Lever Geometry

```yaml
lever_length_cm: 0.0  # From center of stem to grip end
lever_thickness_cm: 0.0  # Through-hole grip thickness
lever_width_cm: 0.0  # Width of lever arm
lever_shape: ""  # straight, offset, ergonomic_curve

# Hub/Socket body
hub_diameter_cm: 0.0  # Diameter around socket
hub_height_cm: 0.0  # Total hub height
hub_wall_thickness_cm: 0.0  # Min thickness around socket
```

### 3. Clearances & Fits

```yaml
# Fit type
fit_type: ""  # press_fit, clearance_fit, transition_fit

# Thermal considerations
operating_temp_min_c: 0.0
operating_temp_max_c: 0.0

# Print orientation
recommended_orientation: ""  # vertical_hub, horizontal_lever
```

### 4. Fastening/Hardware

```yaml
mounting_method: ""  # set_screw, threaded_insert, captive_nut, friction
hardware_required: []
# Examples:
# - "M4x12 set screw"
# - "1/4-20 threaded insert"
# - "M5 heat-set insert"
```

---

## Measurement Techniques

### From Catalog/Datasheet

| Field | Where to Look | Common Locations |
|-------|---------------|------------------|
| Stem square | "Operating Nut" or "Stem" section | Dimensional drawings |
| Stem depth | "Stem Travel" or "Depth" | Specifications table |
| Handle length | "Lever Length" or "Dimensions" | Assembly drawing |

### From Physical Valve (if no docs)

```
1. Stem Square: Use calipers across flats (measure in 2 orientations 90° apart)
2. Stem Depth: Insert depth gauge or paperclip, mark, measure
3. Set Screw: Count threads per inch + diameter, or match to thread gauge
4. Hub OD: Measure existing handle OD or estimate from valve body
```

---

## Quick Reference: Common Valve Stem Sizes

| Size | Inch | mm | Typical Application |
|------|------|----|---------------------|
| Small | 1/4" | 6.35 | 1/4"-1/2" ball valves |
| | 5/16" | 7.94 | 1/2"-3/4" ball valves |
| Medium | 3/8" | 9.53 | 3/4"-1" ball valves |
| | 1/2" | 12.7 | 1"-1.5" ball valves |
| | 9/16" | 14.29 | 1.5"-2" ball valves |
| Large | 5/8" | 15.88 | 2"-3" ball/gate valves |
| | 3/4" | 19.05 | 3"-4" gate valves |
| | 1" | 25.4 | 6"+ gate valves |

---

## Nibco Chemtrol Specific Notes

From web search findings:
- Chemtrol valves often use **square operating nuts** per industry standards
- Common sizes: 7mm, 8mm, 9.5mm (3/8"), 12.7mm (1/2"), 15.9mm (5/8")
- T-handle ball valves typically: 3/8" or 1/2" squares
- Check valves (T-104/105/135 series): 5/16" or 3/8" squares

---

## Example Completed Entry

```yaml
# Nibco T-585-70-LF 1" Ball Valve
document_source: "Nibco Catalog B305358PC"
valve_manufacturer: "Nibco"
valve_model: "T-585-70-LF"
document_date: "2023-01"
extracted_by: "Engineering"
extraction_date: "2024-03-16"
confidence_level: "high"

stem_shape: "square"
stem_across_flats_cm: 1.27  # 1/2"
stem_depth_cm: 1.5
stem_tolerance_cm: 0.05

lever_length_cm: 8.0  # Custom, not from spec
lever_thickness_cm: 1.0
lever_width_cm: 2.0

mounting_method: "set_screw"
hardware_required: ["M5x10 set screw"]
```
