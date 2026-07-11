# NIBCO CADmep Package Analysis

**Source:** `NIBCO- CADmep - Complete Package`
**Date Reviewed:** 2024-03-16
**Package Type:** Autodesk Fabrication CADmep BIM Content

---

## What This Package Contains

This is **BIM/CAD content** for Autodesk Fabrication (CADmep) - NOT dimensional specification sheets.

- **ITM files:** Binary compressed CAD components for system modeling
- **Excel files:** Product catalog listings (model numbers, sizes, materials)
- **PNG files:** Preview images of valve components
- **IES files:** Estimating data

---

## Valves Found in Package

### Ball Valves (Popular Models)

| Model Series | Material | Handle Type | Sizes Found |
|--------------|----------|-------------|-------------|
| **T-585-70** | Bronze | Lever | 1/4" - 2" |
| **T-585HP-66-LF** | Bronze | Lever | 1/4" - 1" |
| **T-580-70** | Bronze | Lever | 1/4" - 2" |
| **T-590-Y** | Bronze | Lever | 1/4" - 2" |
| **S-580-70** | Bronze | Lever | 1/4" - 2" |
| **S-585-70** | Bronze | Lever | 1/4" - 2" |
| **PC-585HP-66-LF** | Plastic | Lever | 1/2" - 1" |
| **G-590-Y** | Bronze | Gear Operator | 2"+ |

### Chemtrol Valves (PVC/CPVC)

Located in: `NIBCO-Ball Valves/Imperial Content/Mechanical/Equipment/Valves/Nibco/Chemtrol/`

| Model | Type | Material |
|-------|------|----------|
| F45BC-E | Ball Check Valve | PVC |
| F45BC-V | Ball Check Valve | PVC |
| F45TB-E | Ball Valve | PVC |
| F45TB-V | Ball Valve | PVC |
| F51BC-E | Ball Check Valve | PVC |
| F51BC-V | Ball Check Valve | PVC |
| F51TB-E | Ball Valve | PVC |
| F51TB-V | Ball Valve | PVC |
| 4660-S | Ball Valve Cup | PVC |
| 4660-T | Ball Valve | PVC |
| 4770 | Ball Valve | PVC |
| A45CC-V | Ball Valve | PVC |

---

## What's MISSING (Critical for Handle Design)

This CADmep package does **NOT** contain:

- ❌ Valve stem square dimensions (across-flats)
- ❌ Stem engagement depth specifications
- ❌ Set screw sizes
- ❌ Handle mounting specifications
- ❌ Dimensional drawings

---

## What You Need

To get the actual stem dimensions for 3D printing handles:

### Option 1: Physical Measurement (Recommended)
```
Tools needed: Calipers, depth gauge or paperclip

1. Measure ACROSS-FLATS of valve stem (square dimension)
   → Typical Nibco ball valves: 3/8" (9.5mm) or 1/2" (12.7mm)

2. Measure stem engagement depth
   → Typical: 15-20mm

3. Check for set screw
   → Common: M4 or M5 thread
```

### Option 2: NIBCO Technical Documentation
- Contact NIBCO Technical Services: **1-888-446-4226**
- Request datasheet for specific model (e.g., "T-585-70")
- Ask for "stem square dimension" and "operating nut size"

### Option 3: Online Resources
- NIBCO website product pages often have spec sheets
- Search: "Nibco [model number] datasheet PDF"

---

## Common NIBCO Ball Valve Stem Sizes (Industry Standard)

Based on typical ball valve specifications:

| Valve Size | Typical Stem Square | Metric |
|------------|---------------------|--------|
| 1/4" - 1/2" | 5/16" | 7.9mm |
| 3/4" - 1" | 3/8" | 9.5mm |
| 1-1/4" - 2" | 1/2" | 12.7mm |

**Note:** Always verify with your specific valve!

---

## Next Steps

1. **Identify your specific valve model** from the list above
2. **Measure the stem** with calipers OR contact NIBCO for specs
3. **Fill out** `chemtrol_valve_handle_spec.yaml` with actual dimensions
4. **Generate handle** using the `create_valve_handle` workflow

---

## Files of Interest in Package

```
NIBCO-Ball Valves.xlsx          - Product catalog (no dimensions)
NIBCO-Ball Valves/              - ITM CAD files (binary, not readable)
NIBCO-Gate Valves/              - Gate valve CAD files
NIBCO-Butterfly Valves/         - Butterfly valve CAD files
NIBCO-Check Valves/             - Check valve CAD files
```

---

## Key Finding

The CADmep package is designed for **system modeling** (pipe routing, clash detection, estimating), not for **product manufacturing specifications**. The valve stem dimensions needed for 3D printed handle design must be obtained from:

1. Physical measurement of your valve
2. NIBCO technical datasheet for your specific model
3. NIBCO technical support
