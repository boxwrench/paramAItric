# CAD integration resources

This repo keeps dependency/adaptor configuration, not upstream implementations.
Downloads are local to `.external-resources/` and ignored by Git.

Prepared in this assignment: 59 exact Linux x86_64/Python 3.13 dependency wheels
(about 230 MB) and 16 upstream README/license/architecture reference documents.
The cache's `manifest.json` records SHA-256 and byte count. Upstream commits are
pinned in `upstreams.lock.json`; these reference snapshots are not necessarily
the source commit of an installed release. The runtime is selected separately by
`cad_backends/cadgen/requirements.lock.txt`.

To prepare on another machine using Python with pip installed:

```bash
python scripts/prepare_cad_resources.py --wheels
python scripts/prepare_cad_resources.py --verify-only
```

Without `--wheels`, only pinned references are downloaded and any existing wheels
are indexed. Downloads fail visibly on missing references or packages. Review a
version change deliberately; this script does not follow `latest` refs.

Offline worker installation:

```bash
uv venv .external-resources/cad-env --python 3.13
uv pip install --python .external-resources/cad-env/bin/python \
  --no-index --find-links .external-resources/wheels \
  -r cad_backends/cadgen/requirements.lock.txt
```

This exact offline package installation and unit-cube kernel import were tested.
The Python interpreter, platform libraries, Node for cadgen viewing/compile, and
Playwright's matching browser must be provisioned separately if absent. There are
no mandatory NVIDIA GPU dependencies. See the [integration runbook](../docs/consolidation/integration_plan.md).

FreeCAD and SMLib reference documents are downloaded for evaluation only. No
FreeCAD binary, SMLib build toolchain, large upstream source tree, model weights or
ROCm/CUDA runtime was installed. The existing local-model/Fusion milestone remains
a separate qualification task. Cache files are disposable downloaded resources;
user modeling recipes and accepted outputs are not.
## SolidCraft experimental bridge resources

The separate `solidcraft.lock.json` and `scripts/prepare_solidcraft_resources.py`
pin the official SolidCraft release bundle, CLI hash, license/API references and
optional browser bundle. Downloads/extraction stay in ignored
`.external-resources/solidcraft`; no system installation, upstream source fork
or production dependency. `--verify-only` checks the native evaluation resources;
`--include-web` additionally downloads/verifies the optional UI bundle. An
interrupted `.partial` download is never a verified executable resource.
See [the bounded evaluation](../docs/consolidation/solidcraft_evaluation.md).

The [opt-in bridge](../docs/consolidation/solidcraft_integration.md) checks the
pinned native CLI hash before execution and the independent reader versions at
health/read-back. The optional UI bundle is separate from headless modeling.
