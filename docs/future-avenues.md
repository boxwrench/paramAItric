# Future Avenues

Status: future consideration

## Why this exists

This document captures future-facing directions that are worth keeping in view without treating them as part of the active execution plan.

The main themes here are:

- possible public product wrappers around ParamAItric
- crowdfunding and MakerWorld-style distribution ideas
- longer-term delivery models for configurable part families

None of this is current implementation work. The active source of truth remains the main roadmap and dev log.

## Current framing

ParamAItric may be more commercially useful as the internal engine behind simple maker-facing generator products than as the public product itself.

The current thinking is:

- keep ParamAItric as the internal workflow/generation system
- package simple, useful, customizable products for the Bambu/MakerWorld audience
- learn from existing crowdfunding/generator-style offerings
- avoid assuming the first public offer should be a Fusion add-in

## Product hypothesis

The better public-facing offer is likely:

- a simple customizable printable product
- delivered as files, variants, presets, or a lightweight generator experience
- built on top of validated workflow paths

Not likely the first public offer:

- "AI CAD system"
- general-purpose Fusion add-in
- broad autonomous design tool

## Product distinction

Internal engine:

- ParamAItric
- Fusion-based workflow learning
- staged CAD generation
- verification-heavy workflow contracts

Public product:

- simple generator or configurable design family
- obvious utility for Bambu/MakerWorld users
- easy-to-understand parameters
- repeatable expansion into adjacent item families

## Candidate avenues

Good early candidates:

- custom picture frame / snap-fit frame family
- simple enclosure generator
- bracket / mount generator
- organizer bin / divider family
- display stand family
- sign / nameplate generator

Why these are attractive:

- structured geometry
- low ambiguity
- easy to explain
- likely compatible with staged validated workflows
- easy to expand into a family of related products

## Questions to answer later

### About other creators

- What are successful MakerWorld crowdfunding creators actually delivering?
- Are they shipping:
  - file packs
  - generated variants
  - request-based customization
  - web tools
  - downloadable tools
- How much of the value is the model itself versus the configurability?
- Are they using a visible generator, or are they just delivering curated outputs?
- What do backers appear to respond to most:
  - utility
  - personalization
  - novelty
  - ecosystem/expansion potential

### About technical delivery

- Should the first offer be:
  - pre-generated downloadable pack
  - semi-custom request pipeline
  - true self-serve generator
- What geometry stack would be best for a public generator if Fusion is not the runtime backend?
- Which parts of ParamAItric can be reused directly, and which would need a different implementation for a public generator?
- Would a simple hosted web front end be enough for the first generator product?
- What file formats should be delivered:
  - STL
  - 3MF
  - STEP
  - source parametric format

### About business fit

- Is the crowdfunding product a single generator or a family/system?
- What is the smallest simple product that still feels fundable?
- What is a better headline:
  - generator
  - customizer
  - builder
  - system
- Is the better play one high-clarity product first, then adjacent follow-ons?

## Cheapest viable test

The gating question is not "should we build a generator" — it is "do people want configurable versions of these parts."

### Test before building

Post one well-scoped file pack on MakerWorld (free or low cost). Pick a product lane that maps to a workflow ParamAItric already supports — bracket/mount is the natural first candidate since the spacer workflow generalizes directly.

Include a visible parameter table (hardware sizes, widths, thicknesses) and a clear note: "need different dimensions? request a variant."

What to measure:

- Downloads tell you if the category has interest.
- Variant requests tell you if the generator product has a market. Someone asking "can you make this but 40mm wide" is validating the generator without you building it.
- No requests after meaningful downloads means the pack itself is the product, not the configurability.

This costs an afternoon of Fusion time, not an infrastructure project.

### What makes a file pack work

File packs that sell on MakerWorld and Printables tend to have one of two things:

1. **Obvious utility with real variation** — not "here's 20 brackets" but "here's a bracket system that covers M3-M8 hardware, 5 mounting widths, 3 thicknesses, with and without cable routing." The buyer is paying to skip the CAD work they'd otherwise do themselves.

2. **A visible system behind it** — "this is from a generator, more variants on request" signals that the creator can deliver what the buyer actually needs, not just what's in the pack. The pack is the storefront, the generator is the value.

A generic file pack with no story probably doesn't move. A "configurable bracket system, here are the 20 most common configs, request custom dimensions" is a different pitch — and it's one ParamAItric is specifically built to deliver on.

## Narrowing the questions

The open questions in this doc span market research, technical stack, and business model. Most of them don't need answers yet. The one question that gates the next move:

> Should the first offer be a pre-generated file pack, a request-based pipeline, or a self-serve generator?

Everything else flows from that answer:

- **File pack**: no geometry backend needed for delivery. Generate with Fusion offline, ship STLs/3MF. Lowest investment, tests product-market fit directly.
- **Request pipeline**: needs ParamAItric but not a public frontend. Someone asks for dimensions, you run the workflow, deliver the file. Tests whether customization is the value.
- **Self-serve generator**: needs a non-Fusion geometry stack (CadQuery/build123d) and hosting infrastructure. Only worth building after validating that people want the product.

The geometry stack research (OpenSCAD, CadQuery, build123d) is premature until you've validated demand. Fusion works fine for internal generation at low volume. Defer "what replaces Fusion" until you know people actually want configurable parts.

### Pricing and scale

MakerWorld crowdfunding campaigns are typically small — a few hundred to a few thousand dollars. That changes how much infrastructure investment makes sense for v1. A file pack with 20 bracket variants at $5-10 is a fundamentally different business decision than building a hosted generator. Know the scale before choosing the delivery mechanism.

## Working conclusions so far

- Simplicity is probably a strength, not a weakness.
- The strongest public wrapper is likely a simple configurable product, not CAD software.
- ParamAItric is best treated as the internal engine for discovering and producing validated product families.
- Fusion is likely suitable for internal workflow discovery and low-volume generation, but not as the long-term public backend for a self-serve generator service.
- A true public generator is a known kind of software product, but the geometry backend matters more than the website.
- The cheapest validation path is: post a file pack, watch for variant requests, then decide what to build.
- Bracket/mount is the natural first product lane because it maps directly to workflows already being built.

## Research still needed

### Market research (do first)

- Review current MakerWorld crowdfunding campaigns that look like generators or configurable systems.
- Identify what backers are actually buying — files, customization, ongoing expansions, or tools.
- Compare a few examples against our likely product lanes.

### Technical research (do after market validation)

- Lightweight geometry stacks for public generators: OpenSCAD, CadQuery, build123d.
- Typical architecture for hosted model generators: form/UI, parameter validation, generation job, artifact storage, download delivery.
- Whether request-based generation is a better v1 than instant generation.

## Reminder for later

Do not confuse:

- "ParamAItric works as a live Fusion workflow system"

with:

- "the right public product is a Fusion add-in"

Those may be different things.
