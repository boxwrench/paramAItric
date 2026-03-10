## Strut Channel Bracket (McMaster 33125T421)

- **Material Context:** Steel
- **Print Context:** High infill PETG or ABS.

### Dimensions
- **Width:** 3.5 inches
- **Height:** 4.125 inches
- **Depth:** 1.625 inches
- **Thickness:** 0.25 inches
- **Holes:** 4x 9/16" diameter holes (two on horizontal face, two on vertical face).
- **Notable Features:** The vertical leg tapers inward from the base to the top edge. The inner and outer corners feature a bend radius rather than a sharp 90-degree corner.

### Why this is a good test:
- Tests multi-plane coordinate mapping (XY for cross-section, XZ for taper cut, YZ for vertical holes).
- Tests boolean CSG logic (cutting tapers with triangles).
- Requires understanding that bent sheet metal must be modeled from its cross-section, not its face footprint.