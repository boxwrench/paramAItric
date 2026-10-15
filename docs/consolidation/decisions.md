# Consolidation decisions

1. **Baseline from master; preserve integration ref.** Tree inspection found goals
   work on both histories; master has later fixes/planning. Do not merge by commit
   count. See [baseline](baseline.md).
2. **One narrow part protocol.** Start/apply/read-back/export and explicit capability
   sets support the plate proof. Retain the existing operation vocabulary, adding
   finite XY placement only for a real centered bore. No framework migrations.
3. **Keep default MCP/Fusion stable; explicitly select the product slice.** The neutral
   Fusion adapter reuses gated primitives. The next authorized batch connected the
   open plate through the existing guided tools via explicit environment settings.
   It does not rewrite the bridge or advertise a nonexistent HTTP cadgen profile.
4. **Use cadgen's published public build123d namespace and thin native exporters.**
   The fixed worker uses `bd.Box`, `bd.Cylinder`, `bd.export_step`, `bd.export_stl`,
   and cold `bd.import_step`. Direct native export/read-back avoids launching a
   persistent build daemon outside worker limits. Decorated cadgen models and its
   public `read_scene`/`read_step` APIs remain supported integration options, but
   their cache/daemon behavior is not part of this isolated proof. No private cadgen
   symbols are imported and no upstream exporter/cache implementation is copied.
5. **Keep viewer outside geometry acceptance.** Invoke published `cadgen viewer`
   and snapshot commands. No embedded frontend. Snapshot tessellation can look
   polygonal while analytic STEP circles are exact; visuals are diagnostic.
6. **Recipe editability first.** Retain source and parameters with version/provenance
   records. Native feature history is a different claim, motivating future FreeCAD.
7. **Fixed source, bounded process.** No generated Python input. Resource limits
   plus controlled parameters suffice for this prototype; an OS sandbox would be
   required for a future untrusted program surface. Do not claim subprocess equals
   security sandbox.
8. **Freeze runtime; download resources separately.** Use cadgen 0.7.14 from the
   installed skill and the 59-package lock. Newer upstream main was reviewed as
   reference only. Ignored wheel/reference cache has hashes; no source vendoring.
9. **Retain FreeCAD/SMLib research without expanding the release.** No placeholder
   adapter directories, empty implementations, SMLib dependency, CUDA dependency
   or GPU port. Model inference remains independent of CPU CAD execution.
10. **Fix test isolation, not production routing.** Two pre-existing profile tests
    needed an owned mock bridge; injecting the existing fixture preserves profile
    endpoint activation semantics and avoids an implicit live bridge requirement.
11. **One guided dispatcher and request-local cancellation.** MCP now calls the
    server's existing validated build dispatcher rather than duplicating routing.
    The open runtime retains accepted revisions in owned output folders, rejects
    unsupported work and concurrent transactions, and passes cancellation into the
    bounded worker. Default Fusion uses the existing path without the open guard.


## SolidCraft integration follow-up — 2026-10-14

- **Reuse the native engine rather than emulate its feature system.** Two reviewed
  command plans now execute behind the same five tools; the plate-only operation
  protocol remains the OCCT/Fusion reference. No generic IR or extra agent surface.
- **Reuse acceptance, specialize execution.** The native runtime inherits the
  existing transaction/cancellation lock and atomic publisher. Native save/reopen,
  parameter/sketch health and independent STEP/STL read-back are adapter duties.
- **Native editability is qualified narrowly.** The two generated families retain
  native history and parameter relationships. The existing OCCT path still promises
  a recipe, not feature history. Importing externally edited native documents needs
  a separate explicit revalidation contract; updating hashes alone is insufficient.
- **Cancellation belongs to the application.** Terminate disposable process groups
  and discard failed staging; do not trust upstream's observed ineffective MCP
  cancellation. Checkpoint recovery never authorizes continuing a failed request.
- **Freeze competing modeling expansion.** Keep Fusion default and the OCCT plate
  reference. Next qualify upstream UI/target hardware, then decide on primary
  adoption. [Integration contract](solidcraft_integration.md).


## External native-edit contract — 2026-10-14

- Preserve accepted files; give the editor a separate parent-bound copy. Accept IDs,
  not arbitrary filesystem imports. Snapshot and verify only that prepared copy.
- Declare intended dimensions; preserve all others. Compare complete authored
  native history to the parent regenerated through SolidCraft's own supported
  parameter interface. Do not infer recipe identity from shape similarity.
- Preserve submitted bytes, native definitions, parent/source hashes and policy
  evidence as four additional immutable artifacts. Reuse the existing transaction,
  cancellation/process limits, independent OCCT gate and atomic publisher.
- Keep automated headless editor evidence distinct from human/desktop qualification.
  External revalidation passes; default promotion remains blocked on the latter.
- MCP hosts must send an actual cancellation notification. Local client awaiter
  cancellation alone does not cancel server work in the pinned SDK.
