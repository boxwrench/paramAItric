# Consolidation decisions

1. **Baseline from master; preserve integration ref.** Tree inspection found goals
   work on both histories; master has later fixes/planning. Do not merge by commit
   count. See [baseline](baseline.md).
2. **One narrow part protocol.** Start/apply/read-back/export and explicit capability
   sets support the plate proof. Retain the existing operation vocabulary, adding
   finite XY placement only for a real centered bore. No framework migrations.
3. **Keep public MCP/Fusion stable during proof.** The neutral adapter path is internal.
   It reuses existing gated Fusion primitives; it does not rewrite the bridge or
   advertise an unimplemented runtime profile.
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
