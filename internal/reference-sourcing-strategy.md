# Reference Sourcing Strategy

This is a working note for acquiring lawful, reviewable engineering reference artifacts for the part-family library.

It is not a canon doc.
Use it to guide intake choices and future automation.

## Goal

Find efficient, repeatable sources of technical drawings and CAD-adjacent reference material for commodity utility parts.

Prefer sources that already provide:

- dimensioned drawings
- 2D CAD or drawing files
- 3D CAD downloads
- stable product metadata
- clearly named part variants

## Preferred Source Classes

### 1. Official Product Pages With Downloadable Drawings

Best when a product page exposes:

- PDF drawing or specification sheet
- 2D DXF or DWG
- STEP or other 3D CAD
- product dimensions and part numbering

Why this is strong:

- high trust
- stable part identity
- easy to normalize into a spec note

### 2. Official Supplier CAD Libraries

Best when a manufacturer or distributor offers:

- a searchable CAD library
- 2D and 3D file options
- category browsing by part family

Why this is strong:

- good breadth for commodity categories
- often includes dimension tables and drawings
- easier to build a family shortlist quickly

### 3. Supplier-Backed Multi-Vendor CAD Platforms

Useful when:

- the official manufacturer site is weak
- multiple vendors in the same family need to be compared

Use carefully:

- prefer supplier-certified content
- verify that the artifact has enough dimension detail before treating it as strong intake

## Promising Intake Backbones

### McMaster-Carr

Use for:

- broad commodity coverage
- fast category discovery
- 2D/3D download availability on many parts

Best role:

- rapid discovery and comparison
- strong source for standard hardware and utility components

### TraceParts

Use for:

- supplier-backed CAD discovery across many industrial categories
- finding enclosure and electrical-product families

Best role:

- family-level exploration
- cross-vendor category search

### 3D ContentCentral

Use for:

- supplier-certified CAD when the category exists there with drawing support

Best role:

- fallback or comparison source
- additional candidate discovery

### MISUMI

Use for:

- mechanical-component families with strong CAD/download workflows
- parts with configurable dimensions and line drawings

Best role:

- dimension-driven parts
- categories where configurable parametric families are useful

### Enclosure Manufacturers With Direct Drawing Downloads

Promising examples for the enclosure family:

- Hammond Manufacturing
- OKW Enclosures
- Bud Industries
- nVent HOFFMAN
- Polycase

Best role:

- first-pass enclosure and cover intake
- direct PDF and CAD-backed candidate selection

## First Family Recommendation

For `enclosures-and-covers`, start with direct manufacturer sources before multi-vendor platforms.

Reason:

- enclosure makers often expose PDF drawings, DXF, and STEP directly on product pages
- family naming is clearer
- body and lid relationships are easier to track

Recommended first-pass order:

1. Hammond Manufacturing
2. OKW Enclosures
3. Bud Industries
4. Polycase
5. nVent HOFFMAN
6. TraceParts as overflow discovery

## Preferred Artifact Types

Strong:

- dimensioned PDF drawing
- 2D DXF or DWG with matching product page
- STEP plus drawing/spec sheet
- dimension tables with clear part identity

Medium:

- technical product page with dimensions but no downloadable drawing
- exploded assembly sheet with callouts and dimensions

Weak:

- marketing image only
- generic assembly view without dimensions
- plain photo

## Intake Workflow

1. Choose one family.
2. Search direct manufacturer enclosure pages first.
3. Save the strongest 3 candidate artifacts to private intake `raw/`.
4. Derive text, page images, and cropped views into `derived/`.
5. Fill one intake note per artifact.
6. Draft one normalized part-spec per artifact that passes the intake gate.
7. Score the resulting candidates.

## Automation Opportunities

Good candidates for scripts:

- bulk page-to-image conversion for PDFs
- text extraction from PDF tables
- consistent file naming
- generation of intake note skeletons
- extraction of product identifiers from filenames
- local manifest tracking for candidate artifact state
- scorecard assembly from completed notes

## Questions For A Deeper Research Pass

Run a deeper pass only if the first intake round is still inefficient.

Questions:

- which source has the best enclosure-family density with downloadable drawings per category page
- which source exposes the most stable URLs and naming for automation
- which source provides the cleanest PDF drawings vs viewer-only CAD
- which families beyond enclosures have the best direct-download coverage
- whether public APIs or export endpoints exist for lawful metadata retrieval

## Current Recommendation

Do not expand research broadly yet.

Start one bounded enclosure-family intake pass against a small number of official manufacturer libraries.
Only do deeper source research after we learn where the first pass is inefficient.

For that first pass, prefer:

1. Hammond Manufacturing
2. OKW Enclosures
3. Bud Industries
4. Polycase

Use nVent HOFFMAN and multi-vendor CAD platforms as overflow or confirmation sources rather than the starting point.
