# Valve Handle Specification Documentation

This directory contains tools and templates for extracting CAD-relevant dimensions from valve manufacturer documentation.

## Quick Start

1. **Find your valve spec** - Look for:
   - Manufacturer datasheet/catalog
   - Valve nameplate (model number)
   - Physical measurements with calipers

2. **Fill out the spec template** - See `SPEC_EXTRACTION_TEMPLATE.md`

3. **Run the workflow** - Use extracted dimensions with `create_valve_handle`

## Directory Structure

```
valve_specs/
├── README.md                          # This file
├── SPEC_EXTRACTION_TEMPLATE.md        # Template for manual extraction
├── spec_extractor.py                  # Python helper for text extraction
└── nibco_chemtrol/                    # Manufacturer-specific specs
    └── chemtrol_valve_handle_spec.yaml  # Nibco Chemtrol template
```

## Common Valve Stem Sizes (Reference)

| Valve Size | Type | Typical Stem Square | Metric |
|------------|------|---------------------|--------|
| 1/4"-1/2" | Ball | 1/4" - 5/16" | 6.4-7.9mm |
| 1/2"-1" | Ball | 3/8" - 1/2" | 9.5-12.7mm |
| 1"-2" | Ball | 1/2" - 9/16" | 12.7-14.3mm |
| 2"-4" | Gate | 5/8" - 3/4" | 15.9-19.0mm |
| 6"+ | Gate | 1"+ | 25.4mm+ |

## Using the Spec Extractor

```bash
# From text snippet
cat << 'EOF' | python docs/valve_specs/spec_extractor.py
Model T-585-70-LF ball valve features 1/2" square operating nut
with 3/4" stem engagement depth. Set screw: 1/4-20.
EOF

# Output:
# Shape: square
# Across Flats: 1.27 cm
# Stem Depth: 1.90 cm
# Set Screw: 1/4-20
```

## Nibco Chemtrol Specific

Current status: **Awaiting specific valve documentation**

From web search findings:
- Chemtrol valves typically use **square operating nuts**
- Common sizes: 5/16", 3/8", 1/2", 9/16", 5/8" (across flats)
- Verify with specific model datasheet or physical measurement

### Next Steps for Your Nibco Chemtrol Valve

1. **Find the model number** - Check valve nameplate/body
2. **Locate datasheet** - Search nibco.com for model-specific catalog page
3. **Measure if needed**:
   - Stem across-flats (use calipers)
   - Stem engagement depth (depth gauge or paperclip method)
   - Set screw thread size (thread gauge or count threads)
4. **Fill out** `nibco_chemtrol/chemtrol_valve_handle_spec.yaml`
5. **Generate handle** using `create_valve_handle` workflow

## Print Recommendations

| Material | Use Case | Notes |
|----------|----------|-------|
| PLA | Prototyping only | Low temp resistance |
| PETG | General purpose | Good chemical resistance |
| ASA | Outdoor/hot water | UV resistant, higher temp |
| Nylon | High strength | Chemical resistant, flexible |

## Contact for Help

- Nibco Technical: 1-888-446-4226
- Valve spec issues: Create issue in project repo

---

**Sources:**
- [Nibco Industrial Plastic Valves](https://www.nibco.com/nibco-products/valves/industrial-plastic-valves)
- [Chemtrol Valve Guide PDF (Bayport Valve)](https://www.bayportvalve.com/pdffiles/Chemtrol/ChemVlvGuide.pdf)
