# Fusion 360 Thread API, Feature APIs, Tinkercad Shape Generators, and Heat‑Set Insert Dimensions (2025‑2026)

## Executive summary

This report consolidates current information (through early 2026) on four areas relevant to parametric CAD tooling: (1) the current Fusion 360 Thread API, especially `ThreadInfo.create` versus `ThreadFeatures.createThreadInfo`, modeled threads and STL export behavior, thread XML libraries, and multi‑thread gotchas; (2) which Fusion 360 geometric features are reliably scriptable via the Python API versus UI‑only or fragile functionality; (3) how the legacy Tinkercad JavaScript shape‑generator system structured parameters and CSG operations, and how those ideas can inform a modern parametric part catalog; and (4) reference dimensions and recommended bores for heat‑set inserts from common brands (CNC Kitchen, Ruthex, McMaster and similar), with pragmatic boss and depth guidance for M2–M8.


## 1. Fusion 360 Thread API (2025–2026 state)

### 1.1 `ThreadInfo.create` vs `ThreadFeatures.createThreadInfo`

Autodesk’s current API documentation exposes a static `ThreadInfo.create` method on the `ThreadInfo` class that returns a `ThreadInfo` object representing a specific thread type and size.[^1][^2]
The documented Python signature (translating from the help table) is effectively:

```python
threadInfo = adsk.fusion.ThreadInfo.create(
    isTapered: bool,
    isInternal: bool,
    threadType: str,
    threadDesignation: str,
    threadClass: str,
    isRightHanded: bool,
)
```

The arguments map as:

- `isTapered`: whether the thread is tapered (`True`) or straight (`False); tapered threads are only supported for tapped holes, not external thread features.
- `isInternal`: `True` for internal threads (holes), `False` for external; ignored when used with tapped holes, which are always internal.[^1]
- `threadType`: the thread family name from the XML libraries (for example, `"ISO Metric profile"`, or a custom type name).[^121][^1]
- `threadDesignation`: full designation string for that family, such as `"M5x0.8"`; Fusion parses nominal size and pitch from this.[^121][^1]
- `threadClass`: tolerance/class string (for example, `"6H"`); ignored for tapered threads.[^1]
- `isRightHanded`: `True` for right‑hand, `False` for left‑hand.[^1]

In contrast, the older `ThreadFeatures.createThreadInfo` method on the `ThreadFeatures` collection is explicitly marked **retired** in the current online API reference.[^3]
The retired method has the simpler signature:

```python
threadInfo = threadFeatures.createThreadInfo(
    isInternal: bool,
    threadType: str,
    threadDesignation: str,
    threadClass: str,
)
```

The retirement notice instructs callers to use the newer alternative described in the remarks—this is consistent with Autodesk moving functionality onto the static `ThreadInfo.create` factory while expanding parameters (tapered vs straight, handedness).[^3][^1]
However, many official and community code samples published up through 2024 still use `threadFeatures.createThreadInfo` together with `threadFeatures.threadDataQuery`, and these samples continue to work in current builds.[^4][^5][^6]

**Practical implication:** for new code, use `ThreadInfo.create` plus `ThreadDataQuery` to derive the `threadType`, `threadDesignation`, and `threadClass` strings, but expect that older `createThreadInfo` calls will continue to function for some time even though they are formally retired.[^5][^3][^1]


### 1.2 Creating threads via API: current canonical pattern

Autodesk’s “Thread Feature API Sample” shows the canonical 2024–2025 pattern to create a parametric thread feature programmatically:[^5][^6]

1. Create solid geometry (for example, a cylinder by sketch + extrude).
2. Get the `ThreadFeatures` collection from a component: `threadFeatures = rootComp.features.threadFeatures`.[^5]
3. Obtain a `ThreadDataQuery` object: `threadDataQuery = threadFeatures.threadDataQuery` (noting this property is also marked “retired” but still used in samples).[^6][^5]
4. Enumerate valid thread types, sizes, designations and classes using `allThreadTypes`, `allSizes`, `allDesignations`, and `allClasses` on `ThreadDataQuery`.[^4][^5][^6]
5. Construct a `ThreadInfo` using either the older `threadFeatures.createThreadInfo` or the newer `ThreadInfo.create` given the selected type / designation / class.[^5][^1]
6. Build an `ObjectCollection` of cylindrical faces to thread (for example, `sideFace = extrude.sideFaces.item(0)` and `faces.add(sideFace)`).[^5]
7. Create a `ThreadFeatureInput` with `threadFeatures.createInput(faces, threadInfo)` and set properties like `isFullLength` and `threadLength`.[^5]
8. Call `threadFeatures.add(threadInput)` to create the feature in the timeline.[^5]

This pattern is stable and matches how other feature APIs work (create an “input” object, populate it, then call `add`).[^7][^5]


### 1.3 Modeled vs cosmetic threads and STL/3MF export

Fusion’s thread command distinguishes between “cosmetic” and “modeled” threads via the **Modeled** checkbox in the UI.[^8][^9][^10]
Cosmetic threads store only metadata and an image decal, not body geometry, so they do not appear in STL/3MF exports or 3D prints.[^11][^8]
When **Modeled** is checked, Fusion creates full helical geometry; this is what users must enable for 3D printed threads or for boolean operations with other solids.[^9][^12][^8]

Multiple user tutorials and forum threads confirm that if a thread feature’s modeled flag is off, the exported mesh will appear smooth even though the design shows a thread marker.[^12][^11][^8]
Conversely, when modeled threads are enabled, STL exports include the detailed helical surface—at the cost of larger file sizes and heavier downstream processing in slicers.[^9][^12]

There are, however, some edge‑case limitations and bugs:

- Fusion currently does **not** support modeled tapered threads; Autodesk staff explicitly state that tapered threads are available only as cosmetic or for tapped holes, not as modeled solids.[^13]
- Forum reports show cases where modeled threads on complex or intersecting geometry cause thread creation or export to fail or silently downgrade to cosmetic, especially when threads intersect each other or other features.[^14][^13]
- Threads imported via custom XML profiles work with the modeled flag as long as the XML geometry is valid, but invalid combinations (for example, extreme pitches or diameters) will cause the `add` call to fail with an “invalid parameters” error, falling back to a plain cylinder in some scripts.[^15][^4]

Because the modeled flag is not directly exposed on `ThreadFeatureInput` in the public docs (it is driven by the thread feature itself), scripts creating threads typically accept Fusion’s default cosmetic state, and users manually enable modeled threads when preparing parts for print.[^10][^5]
For a fully automated 3D‑print toolchain, a wrapper should explicitly set the modeled property on the resulting `ThreadFeature` if and when Autodesk exposes it consistently in the API.


### 1.4 Multiple threads on the same body and intersecting threads

The Fusion UI and tutorials demonstrate creating internal and external threads on mating parts (for example, a threaded rod and a nut), and creating both internal and external modeled threads on separate components that assemble together.[^16][^12][^9]
These workflows behave well for 3D printing as long as nominal dimensions and clearances are chosen appropriately.[^12][^9]

More complex cases involve multiple distinct thread features on **the same** body, such as two intersecting threaded ports or internal and external threads with different pitches on a manifold.
At this point Autodesk’s geometric kernel becomes more fragile:

- An Autodesk forum thread documents that when attempting to create two intersecting modeled thread features on the same body, the second thread often fails with an “incorrect geometry” error if the thread volumes intersect, even when those intersections would be physically valid in a machined part.[^14]
- Users report that leaving threads cosmetic (unmodeled) allows both annotations to exist, but export then lacks real thread geometry, making the solution unusable for 3D printing or boolean operations.[^14]

In practice this means:

- Multiple non‑intersecting threads on different cylindrical faces of a body (for example, co‑axial internal and external threads separated by a shoulder) generally work when modeled.[^9][^12]
- Multiple intersecting modeled threads on the same body remain unreliable and may require custom geometry (coil + sweep) or splitting the body into separate components that are combined later via Boolean operations.[^17][^16]

A robust automation layer should detect when two thread features’ modeled volumes would intersect and either fall back to cosmetic threads or generate custom coil‑based geometry instead of relying on the stock thread feature.


### 1.5 Thread XML database (ThreadData) and gotchas

Fusion’s standard thread library is implemented as a set of XML files under a **ThreadData** directory inside the per‑version installation folders.[^18][^19][^20]
On Windows, multiple Autodesk and community docs give this general pattern (with a version‑specific hash):

```text
C:\Users\\<USERNAME>\\AppData\\Local\\Autodesk\\webdeploy\\production\\<version ID>\\
    Fusion\\Server\\Fusion\\Configuration\\ThreadData
```


On macOS, a similar hierarchy exists under the user Library with `Webdeploy` and a `ThreadData` folder, though the full path is longer due to application bundling.[^21][^19][^15]

Autodesk’s “Custom Threads in Fusion 360” guidance and multiple community tutorials emphasize several gotchas when modifying these XML files:[^22][^15][^21]

- **Per‑update version directories.** Each Fusion update typically creates a new `webdeploy/production/<version ID>` directory, so custom XML files placed directly in `ThreadData` are not automatically copied forward; after an update they appear to “disappear” until manually copied to the new folder.[^23][^24][^19]
- **ThreadKeeper workaround.** The community ThreadKeeper add‑in works by keeping canonical copies of custom XML files in its own folder and restoring them into Fusion’s `ThreadData` directory every time Fusion starts, avoiding manual copying after updates.[^25][^26][^20]
- **XML schema sensitivity.** Minor mistakes in the XML (for example, duplicate `<Name>` entries, malformed `<ThreadSize>` structures, inconsistent units and diameters, or missing `ThreadDesignation` strings) cause the entire file’s contents to be skipped without a clear error in the UI.[^27][^28][^15]
- **Limited access via API.** The `ThreadDataQuery` API is read‑only and assumes the XML follows Autodesk’s schema; while it can list types, sizes, designations, and classes, it cannot modify or validate XML definitions, and it is itself marked “retired” even though the current thread sample still relies on it.[^6][^5]

For a tool that depends on custom or extended thread series, it is safest to:

- Maintain XML sources in version control and generate Fusion‑compatible files via a script (for example, as in the FusionThreads and CustomThreads projects) rather than editing XML inline.[^28][^27]
- Install and depend on ThreadKeeper or a similar mechanism to ensure custom thread definitions survive Fusion updates.[^20][^25]
- Use `ThreadDataQuery` only to discover **valid** combinations already known to be in the XML; do not assume that arbitrary programmatic combinations of size/pitch/class will be accepted.[^4][^6]


### 1.6 What the UI exposes that the API does not

The stock Fusion UI for threads allows users to:

- Choose from all installed standard and custom types, designations, and thread classes.[^8][^12][^9]
- Toggle **Modeled** vs cosmetic threads per feature.[^10][^8][^9]
- Apply threads to both cylindrical faces and tapped holes, including tapered thread standards for pipe threads (cosmetic only).[^15][^8][^9]

The public API, as of early 2026, is more limited:

- There is no documented, direct property on `ThreadFeatureInput` or `ThreadFeature` to set the modeled flag; scripts must either rely on the global preference or manipulate the feature via undocumented low‑level command inputs.[^10][^5]
- Not all hole/tap options from the Hole command (for example, advanced countersink/taper options) are exposed with the same richness in the API as they are in the UI.[^29][^10]
- Advanced repair behaviors (for example, automatic healing when changing thread standards in the UI) are not surfaced; the API instead exposes lower‑level feature definitions that may fail when inconsistent parameters are set.[^29][^5]


## 2. Fusion 360 built‑in features with usable Python APIs

This section inventories several Fusion feature types you are considering wrapping directly—coil/helix, patterns, mirror, loft, sweep, and sheet metal—and summarizes their state in the Python API: whether they support `createInput`/`add` creation, and how reliable they are for automation.

### 2.1 Overall feature creation pattern

Fusion’s API follows a consistent “input object + add” pattern for most parametric features: from a component’s `features` collection you access a specific feature collection (for example, `extrudeFeatures`, `loftFeatures`), call `createInput(…)` with required arguments, set additional properties on the returned `*FeatureInput`, then call `add(input)` to create the feature.[^30][^31][^7]
This pattern is documented for extrude, revolve, sweep, loft, shell, rectangular and circular patterns, and many others, and is widely used in official tutorials and community examples.[^32][^33][^34][^35][^36][^37][^7][^30]


### 2.2 Coil / helix features (thread‑like geometry)

Fusion’s UI exposes a **Coil** command that can generate helical geometry with circular, square, or triangular cross‑sections, and is commonly used for custom thread forms, springs, and multi‑start threads.[^38][^39][^17]
However, the corresponding `CoilFeatures` API is currently **read‑only** for creation:

- An Autodesk API forum thread from mid‑2024 confirms that there is no public `CoilFeatures.createInput` / `add` method to programmatically create new coil features equivalent to the UI tool.[^40]
- The suggested workaround from advanced users is to invoke the underlying UI command via an undocumented **TextCommand** interface, which effectively replays command‑line text through Fusion’s command system.[^40]
- Autodesk does not document TextCommand usage and explicitly warns that such workarounds are unsupported and subject to breakage across updates.[^41][^40]

Because of this, coil‑based automation is fragile: any wrapper relying on TextCommand or on recording/playback of command inputs can break with UI changes, and it is difficult to parameterize reliably for external consumption.
For robust library functionality (for example, a general multi‑start thread generator), it is safer to build helical path curves and sweep a profile along them using the well‑supported **Sweep** API (see below), rather than relying on Coil.


### 2.3 Pattern features (linear/rectangular and circular)

Pattern features are among the more mature and consistently supported parts of the Fusion API.
The typical pattern is:

- From `rootComp.features.rectangularPatternFeatures`, call `createInput(inputEntities, directionOne, quantityOne, distanceOne, PatternDistanceType)` to define pattern entities, direction, count and spacing, then optionally configure a second direction with `setDirectionTwo` before calling `add`.[^34]
- From `rootComp.features.circularPatternFeatures`, call `createInput(inputEntities, axis, quantity, totalAngle)`, configure options (pattern type, compute options), then call `add`.[^33][^30]

The Autodesk sample code and community posts show rectangular and circular patterns being used on bodies, faces, or features, and they behave reliably provided the **inputEntities collection is homogeneous** (all bodies, all faces, or all features); attempts to mix entity types in one pattern input throw runtime errors (“inputEntities should be of a single type”).[^42][^34]

Pattern features are thus excellent candidates to wrap directly: both linear/rectangular and circular have stable `createInput` and `add` methods, and their underlying geometry kernels are mature.


### 2.4 Mirror features

Mirror features are also directly creatable via the API:

- `mirrorFeatures = rootComp.features.mirrorFeatures` obtains the collection.[^43][^42]
- `mirrorInput = mirrorFeatures.createInput(inputEntities, mirrorPlane)` defines what to mirror (bodies, faces, or features) and across which plane.[^44][^43][^42]
- `mirrorFeature = mirrorFeatures.add(mirrorInput)` creates the feature in the timeline.[^44][^43][^42]

Community examples show mirror features applied to bodies and surfaces without special workarounds, as long as `inputEntities` contains items of a single type and the mirror plane is a valid construction plane or planar face.[^43][^42]
One limitation users run into is that certain options visible in the UI—such as changing the feature operation from **New Body** to **Join**—are not yet exposed as mutable properties on `MirrorFeatureInput`; attempts to set an `operations` property in Python fail because it is not a defined member.[^44]

Despite some missing convenience properties, mirror features are stable, and their API surface is sufficient for wrapping straightforwardly.


### 2.5 Loft features (including guide rails)

The **Loft** API follows the standard pattern and is reasonably robust:[^36][^45][^37]

- Get `loftFeats = rootComp.features.loftFeatures`.
- Create input: `loftInput = loftFeats.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)`.[^37][^36]
- Use `loftInput.loftSections.add(profileOrPath)` to add at least two sections (profiles or paths).[^36][^37]
- Configure properties on the input: `isSolid`, `isClosed`, `isTangentEdgesMerged`, `startLoftEdgeAlignment`, `endLoftEdgeAlignment`, and, where needed, guide rails and centerline options.[^46][^37]
- Call `loftFeats.add(loftInput)` to create the feature.[^37][^36]

The official Loft Feature API sample shows multi‑section lofts with control over tangency and edge alignment, but not guide rails in the basic snippet.[^37]
Forum posts and supplementary samples mention using guide rails by adding additional path objects to the `loftInput` where rails are required and by adjusting edge alignment conditions to satisfy Fusion’s requirement that rails touch all sections.[^45][^46]

From a robustness standpoint, loft features are prone to failure when the loft would self‑intersect or when guide rails do not connect to every profile, just as in the UI; scripts must be prepared to catch runtime errors and either adjust geometry or fall back to simpler operations.[^45][^46]
Still, the API coverage is mature enough that lofts are viable to wrap, especially when constrained to well‑behaved profile/rail configurations.


### 2.6 Sweep features with guide rails and multiple rails

Autodesk’s documentation for `SweepFeatures.createInput` explicitly describes creating simple sweeps with just a profile and a path and then notes that additional samples demonstrate sweeps with a guide rail and with two rails.[^47][^35][^32]
The standard creation flow is:

- `sweeps = rootComp.features.sweepFeatures`.
- `sweepInput = sweeps.createInput(profile, path, FeatureOperations.NewBodyFeatureOperation)` defines the base sweep.[^35][^32]
- Properties on `SweepFeatureInput` allow configuring orientation, distance, and the presence of guide rails; Autodesk’s samples titled “Sweep with guide rail Feature API Sample” and “Two Rail Sweep Feature API Sample” demonstrate these advanced cases.[^32][^47]
- `sweeps.add(sweepInput)` creates the feature.[^47]

Community tutorials on parametric modeling with Fusion’s API use sweep extensively and confirm that it works reliably when driven from sketches or constructed paths, making it a good foundation for helical threads, springs, tubes, and cable harnesses.[^35]

Given the lack of a robust Coil API, Sweep is the primary officially supported way to generate complex helical or rail‑controlled geometry from scripts.


### 2.7 Sheet metal features

Fusion’s sheet metal environment exposes features like **Flange**, **Contour Flange**, **Bend**, and rules (thickness, K‑factor, bend radii) in the UI, and most of these behave well for manual modeling.[^48][^49][^50][^51]
The public API does expose sheet metal–specific feature collections (`sheetMetalFeatures`, `flangeFeatures`, etc.), but there are several limitations and gaps:

- Community questions from 2018 onward ask how to access sheet metal rules (thickness, K‑factor) programmatically; at that time there was no documented way to read rule parameters directly from the API, forcing workarounds such as projecting cross‑sections and measuring thickness.[^52]
- More recent posts (2024) show users struggling to activate `sheetMetalFeatures` or automate bending operations, indicating that the API coverage for certain sheet metal commands remains incomplete or poorly documented.[^53]
- A separate 2026 feature request explicitly asks Autodesk to expose “Convert to Sheet Metal” through the API, implying that this critical UI command is still not scriptable and that developers must instead approximate flat patterns via surface modeling and custom algorithms.[^54]

Once a design is already in sheet metal form, common operations like extrudes, patterns, and mirrors continue to function through the standard solid modeling API, but the dedicated sheet metal behaviors (automatic reliefs, rule changes, conversion from solids) are not yet first‑class script targets.[^49][^48][^54]
Thus sheet metal can be **partially** wrapped—especially for reading geometry and perhaps creating simple flanges—but a fully automated sheet metal design pipeline will still require manual steps or non‑public workarounds.


### 2.8 Other robust feature APIs worth wrapping

Beyond the specific features you listed, several other Fusion APIs are mature and could be exposed directly without writing custom geometry math:

- **ExtrudeFeatures**: well‑documented `createInput` and, since recent updates, an `addSimple` helper for basic extrusions; widely used in Autodesk’s own API guides.[^55][^31][^7][^29]
- **RevolveFeatures**: standard `createInput` + `add` pattern and straightforward angle specification.[^7]
- **ShellFeatures**: `shellFeatures.createInput(inputEntities, isTangentChain)` plus `add` to create shell operations from faces and bodies.[^56]
- **ExtendFeatures** (surface modeling): `extendFeatures.createInput(edges, distance, extendType, isChainingEnabled)` + `add` to extend open surface edges; API is clearly documented and stable.[^57]
- **MoveFeatures**: used with `moveFeatures.createInput(bodies, transform)` to reposition bodies; commonly used in parametric modeling examples.[^35]

These provide a broad base for parametric operations that combine well with patterns, mirrors, lofts, and sweeps.


## 3. Tinkercad community shape generators

### 3.1 Historical JS API structure

Tinkercad’s legacy **Shape Generators** allowed users to define parametric solids in JavaScript using a small geometry and tessellation library provided by Autodesk.
While the public authoring interface has since been removed for new generators, historical resources and surviving examples provide insight into the API’s structure.[^58][^59][^60]

An example from Blascarr’s article on the Tinkercad API shows the general pattern:[^59]

```javascript
var Mesh3D   = Core.Mesh3D;
var Tess     = Core.Tess;
var Solid    = Core.Solid;
var Vector2D = Core.Vector2D;
var Vector3D = Core.Vector3D;

var Generator = {
  parameters: function(callback) {
    var params = [
      { id: "r1", type: "number", defaultValue: 10, label: "Radius 1" },
      { id: "r2", type: "number", defaultValue: 20, label: "Radius 2" },
      // more params...
    ];
    callback(params);
  },

  // create the mesh from parameter values
  create: function(params, callback) {
    // build 2D profile path using Vector2D
    var path = new Core.Path2D();
    // ... path.lineTo() etc.

    // extrude path into a 3D Solid and mesh
    var solid   = Solid.extrude([path], 20);
    var mesh    = solid.mesh;
    var result  = Solid.make(mesh);
    callback(result);
  }
};

function shapeGenerator() {
  return Generator;
}
```

Key characteristics are:

- A top‑level `shapeGenerator()` function returning a generator object.
- A `parameters(callback)` method that asynchronously returns an array of parameter definitions (IDs, types, labels, defaults, and possibly min/max constraints).[^59]
- A `create(params, callback)` method that receives current parameter values and uses CSG operations on `Solid` and path/mesh helpers to construct geometry, returning a manifold solid through the callback.[^60][^59]

Tinkercad internally converted this generator into UI controls (sliders, numeric fields, etc.) bound to the `params` object, enabling interactive updates as users changed values.[^61][^58]


### 3.2 Parameter patterns seen in community generators

Although the underlying JS authoring path has been deprecated for new content, the platform still exposes many community **Code** shape generators (for example, gear, Voronoi, text, circular arrays) that illustrate how parameters were structured.[^62][^63][^61]
Videos and documentation show common practices:

- **Discrete choices via numerical or textual params** (for example, gear module, number of teeth, pressure angle, hub options) mapped to dropdowns or radio buttons.[^63]
- **Numeric sliders** constrained by min/max ranges for counts and dimensions (for example, number of array copies, offset distances, teeth count).[^63]
- **Grouping of parameters** into logical sections—size, layout, holes, fillets—similar to JSCAD’s `getParameterDefinitions` arrays.[^64][^65]

The parametric model is conceptually close to OpenJSCAD/JSCAD’s parameter definition system, where a `getParameterDefinitions()` function returns an array of parameter descriptors (name, type, initial value, caption), and `main(params)` constructs geometry accordingly.[^65][^66][^64]
This parallel suggests a mature design pattern for parameter metadata that your own catalog can adopt: a simple JSON schema describing type, label, default, bounds, and grouping, decoupled from the geometry engine.


### 3.3 CSG composition patterns

The Blascarr example and similar resources show that Tinkercad’s shapes relied on a small set of CSG and primitive operations:[^58][^60][^59]

- **2D profile construction** using path operations over points (`Path2D`, `Vector2D`), followed by extrusion to 3D solids via `Solid.extrude`.
- **Basic primitives** (boxes, cylinders, spheres) provided by the Core library, combined through boolean operations (union, difference, intersection) to create more complex shapes.
- **Transformations** (translate, rotate, scale) applied to primitives before boolean combination to build enclosures, brackets, gears, and decorative forms.

This closely matches the sort of constructive solid geometry you would implement in a modern parametric library on top of a kernel such as Open Cascade (via Fusion), OpenJSCAD, or a custom mesh Boolean engine.


### 3.4 Adapting Tinkercad concepts into a new parametric part catalog

Based on these patterns, a modern parametric catalog can borrow several ideas from Tinkercad generators:

1. **Parameter metadata schema.** Define a schema similar to Tinkercad/JSCAD:
   - `id` (stable identifier), `label`, `type` (`float`, `int`, `choice`, `bool`, etc.), `default`, `min`, `max`, and optional `group` or `section`.
   - This schema can be serialized in JSON or a small DSL and is independent of the CAD backend.

2. **Declarative → procedural mapping.** For each catalog part (gear, enclosure, insert boss), implement a function (for example, `build(params)`) that consumes parameter values and calls into your CAD backend or CSG library to construct the part, mirroring Tinkercad’s `create(params, callback)`.

3. **Common “recipes” identified from community usage.** The prominence of gear generators, arrays, text, Voronoi surfaces, and simple enclosures among Tinkercad’s community generators indicates the kinds of reusable parts users most often need.[^67][^61][^63]
   For your catalog, prime candidates include:
   - Metric and imperial gear families (spur, rack) with teeth count, module, pressure angle.
   - Threaded bosses and mating nuts (integrated with your heat‑set insert data).
   - Parametric electronics enclosures (board size, standoff height, wall thickness, fillets, vent patterns).
   - Mounting patterns (VESA, 2020 extrusion brackets, servo mounts) described by hole spacing and sizes.

4. **Separation of UI from geometry.** Just as Tinkercad generated UI controls from parameter definitions, your tool can generate sliders, dropdowns, or text fields automatically from the schema while leaving the geometry logic as a backend concern.

5. **CSG as the core abstraction.** Keep catalog definitions in terms of semantic solids and booleans (for example, “outer box minus inner box = enclosure shell”) rather than low‑level mesh edits; this makes them portable between backends (Fusion API, OpenJSCAD, etc.).[^65][^59]

These patterns maintain the spirit of Tinkercad’s shape generators while operating in a more modern and controllable environment.


## 4. Heat‑set insert dimensions (M2–M8)

### 4.1 Source data from CNC Kitchen, Ruthex, and others

CNC Kitchen’s branded heat‑set inserts (sold via KB‑3D) provide a clear mapping from thread size and insert length to **recommended hole diameters** in 3D‑printed plastic, covering metric threads from M1.6 up to M10.[^68]
The KB‑3D product page lists the following metric sizes and recommended printed hole diameters (excerpted here for M1.6–M10):[^68]

- M1.6 × 2.5 mm insert → 2.2 mm hole.
- M2 × 3 mm → 3.2 mm hole.
- M2.5 × 4 mm → 4.0 mm hole.
- M3 × 3 mm → 4.0 mm hole.
- M3 × 4 mm → 4.4 mm hole.
- M3 × 5.7 mm → 4.0 mm hole.
- M4 × 4 mm → 5.6 mm hole.
- M4 × 8.1 mm → 5.6 mm hole.
- M5 × 5.8 mm → 6.4 mm hole.
- M5 × 9.5 mm → 6.4 mm hole.
- M6 × 12.7 mm → 8.0 mm hole.
- M8 × 12.7 mm → 9.7 mm hole.
- M10 × 12.7 mm → 12.0 mm hole.

Ruthex’s technical data for individual sizes (for example, their M3, M4, and M8 inserts) provide **insert body dimensions** but not explicit recommended hole diameters:[^69][^70][^71]

- M3 × 5.7 (Ruthex): D1 = 4.6 mm, D2 = 3.9 mm, D3 = 4.0 mm, L = 5.7 mm, minimum wall thickness W(min) = 1.6 mm.[^70]
- M4 × 8.1 (Ruthex): D1 = 6.3 mm, D2 = 5.5 mm, D3 = 5.6 mm, L = 8.1 mm, W(min) = 2.1 mm.[^69]
- M8 × 12.7 (Ruthex): D1 = 10.1 mm, D2 = 9.5 mm, D3 = 9.6 mm, L = 12.7 mm, W(min) = 4.5 mm.[^71]

Comparing these with CNC Kitchen’s recommended holes suggests the following interpretation:

- D1 ≈ maximum external diameter of the knurled body.
- D3 ≈ recommended pilot hole for thermoplastics (close to but slightly smaller than D1).
- W(min) = recommended **minimum wall thickness** around the insert.[^70][^71][^69]

CNC Kitchen’s own testing article reports using 4.0 mm holes for Ruthex’s M3 inserts and 4.0–4.1 mm holes for cheap eBay inserts, indicating that a **slight interference** (pilot diameter ≈ 0.5–0.7 mm smaller than maximum OD) is desirable for strong pull‑out performance in FDM plastics.[^72]

Other vendors like Adafruit provide only basic OD and length data (for example, an M3 × 4 mm insert with 4.2 mm outer diameter and 4.0 mm length) and leave hole sizing to the designer.[^73]
McMaster‑Carr’s catalog likewise lists hole diameters for its metric heat‑set inserts, but the online table is large; the important point is that their recommended drill sizes follow the same pattern: hole diameters are slightly smaller than the insert OD to ensure a press fit when heated.[^74]


### 4.2 Design guidelines for bosses and hole depth

Beyond raw insert and hole diameters, several practical installation guidelines emerge from CNC Kitchen’s tests and community practice:

- **Hole interference:** For small sizes (M2–M4), pilot holes about 0.4–0.7 mm smaller than the insert’s maximum OD yield good pull‑out strength without excessive stress; this is consistent with CNC Kitchen’s M3 Ruthex recommendations (4.0 mm hole vs ~4.6 mm OD).[^72][^68]
- **Wall thickness:** Ruthex’s W(min) values of roughly 1.6 mm (M3), 2.1 mm (M4), and 4.5 mm (M8) translate to roughly 0.8–1.2 mm of plastic wall thickness per side, which aligns with common 3D‑printing guidelines (at least 3–4 perimeters around a hole).[^71][^72][^69][^70]
- **Hole depth:** Installers often make the hole **deeper than the insert**—for example, 1.5× the insert length—to provide space for melted plastic and avoid bulging at the base; a popular rule of thumb is to add 3–4 mm of extra depth for small inserts.[^75]
- **Material dependence:** Brittle materials (PLA) tend to crack if walls are too thin or interference is too high, while tougher materials (PETG, ABS, Nylon) tolerate more interference; CNC Kitchen’s tests emphasize tuning hole sizes per material and printer calibration.[^72]

A parametric boss generator should therefore treat vendor values as **starting points** and allow configurable offsets for hole diameter and wall thickness per material profile.


### 4.3 Consolidated reference table (M2–M8)

The following table consolidates data for common M2–M8 heat‑set inserts, primarily from CNC Kitchen’s KB‑3D listing and Ruthex’s dimension tables, and adds **engineering design suggestions** for boss OD and hole depth based on the guidelines above.[^75][^68][^69][^70][^71][^72]

Values marked “(suggested)” are not direct vendor data but reasonable defaults for FDM prints with 0.4 mm nozzles and 3–4 perimeters; these should be exposed as parameters in your tool rather than treated as fixed standards.

| Thread size | Example brand & size | Insert max OD (approx) | Recommended bore in print (vendor) | Suggested boss OD (cylindrical) | Typical insert length L | Suggested hole depth in print |
|------------|----------------------|-------------------------|-------------------------------------|----------------------------------|-------------------------|-------------------------------|
| M2 × 3 | CNC Kitchen, M2 × 3 | ≈ 3.6–3.8 mm (estimated from series) | 3.2 mm hole[^68] | 6.0–6.5 mm (≈ bore + 2.5–3 mm) (suggested) | 3.0 mm[^68] | 5–6 mm (≈ 1.7–2× L) (suggested)[^75] |
| M2.5 × 4 | CNC Kitchen, M2.5 × 4 | ≈ 4.2–4.4 mm (estimated) | 4.0 mm hole[^68] | 7.0–7.5 mm (suggested) | 4.0 mm[^68] | 6–8 mm (suggested)[^75] |
| M3 × 3 | CNC Kitchen, M3 × 3 | ≈ 4.3–4.5 mm (estimated) | 4.0 mm hole[^68] | 7.5–8.0 mm (suggested) | 3.0 mm[^68] | 5–6 mm (suggested)[^75] |
| M3 × 4 | CNC Kitchen, M3 × 4 | ≈ 4.7–4.9 mm (estimated) | 4.4 mm hole[^68] | 8.0–8.5 mm (suggested) | 4.0 mm[^68] | 6–8 mm (suggested)[^75] |
| M3 × 5.7 | Ruthex M3 × 5.7 | D1 = 4.6 mm[^70] | 4.0 mm hole (CNC Kitchen)[^68] | ≥ 7.5–8.0 mm (gives ~1.7 mm wall/side) (suggested) | 5.7 mm[^70] | 8–10 mm (≈ 1.4–1.8× L) (suggested)[^72][^75] |
| M4 × 4 | CNC Kitchen M4 × 4 / Ruthex M4 short | D1 ≈ 6.3 mm (Ruthex M4 × 8.1)[^69] | 5.6 mm hole[^68] | 9–10 mm (suggested) | 4.0 mm[^68] | 6–8 mm (suggested)[^75] |
| M4 × 8.1 | Ruthex M4 × 8.1 | D1 = 6.3 mm[^69] | 5.6 mm hole (CNC Kitchen)[^68] | ≥ 9.5–10 mm (≈ 1.7 mm wall/side) (suggested) | 8.1 mm[^69] | 12–14 mm (≈ 1.5–1.7× L) (suggested)[^72][^75] |
| M5 × 5.8 | CNC Kitchen M5 × 5.8 | ≈ 7.2–7.4 mm (estimated) | 6.4 mm hole[^68] | 10–11 mm (suggested) | 5.8 mm[^68] | 9–11 mm (suggested)[^75] |
| M5 × 9.5 | CNC Kitchen M5 × 9.5 | ≈ 7.2–7.4 mm (estimated) | 6.4 mm hole[^68] | 10–11 mm (suggested) | 9.5 mm[^68] | 14–16 mm (≈ 1.5–1.7× L) (suggested)[^75] |
| M6 × 12.7 | CNC Kitchen M6 × 12.7 | ≈ 9.0–9.2 mm (estimated) | 8.0 mm hole[^68] | 12–13 mm (suggested) | 12.7 mm[^68] | 18–20 mm (≈ 1.4–1.6× L) (suggested)[^75] |
| M8 × 12.7 | Ruthex M8 × 12.7 | D1 = 10.1 mm[^71] | 9.7 mm hole (CNC Kitchen)[^68] | ≥ 14–15 mm (≈ 2.1–2.5 mm wall/side) (suggested) | 12.7 mm[^71] | 18–22 mm (≈ 1.4–1.7× L) (suggested)[^72][^75] |

Notes:

- “Insert max OD” is either D1 from Ruthex or an approximate value inferred from the relationship between hole and OD for other sizes; it primarily informs how much interference the bore should provide.[^68][^69][^70][^71]
- Boss OD suggestions aim to keep wall thickness in the range indicated by Ruthex’s W(min) and CNC Kitchen’s tests (roughly 1.5–2.0 mm per side for smaller inserts, more for larger ones).[^69][^70][^71][^72]
- For thin plates or very small bosses, eccentricity and print tolerance may dominate; the tool should therefore expose boss OD and hole depth as explicit parameters rather than baking in these defaults.


### 4.4 Brand‑specific nuances and tolerances

Different insert brands and series vary slightly in OD, knurl pattern, and recommended holes even for the same nominal thread size:[^74][^73][^72]

- **CNC Kitchen / Ruthex** inserts tend to favor relatively tight bores in printed plastic (for example, 4.0 mm for M3) with robust opposing knurl patterns and published minimum wall thickness values, tuned specifically for 3D‑printed parts.[^70][^71][^68][^72][^69]
- **Cheap generic inserts** (for example, eBay, AliExpress) often have looser tolerances and may benefit from slightly larger bores (for example, 4.1–4.3 mm for M3) to avoid splitting PLA parts; CNC Kitchen’s comparison article notes having to adjust hole sizes specifically for cheap inserts versus Ruthex ones.[^75][^72]
- **McMaster‑Carr** and some industrial vendors provide detailed drill and hole diameter recommendations aimed at injection‑molded plastics; their recommended holes may be tighter than is practical for FDM prints because injection molding produces much more precise and consistent holes.[^74]

In a parametric design tool, it is therefore useful to:

- Allow the **insert series** to be selected (for example, “CNC Kitchen short M3”, “McMaster straight metric M3, 5 mm”) and have brand‑specific baseline hole diameters loaded from a data table.
- Apply **material‑ and printer‑specific offsets** to those baselines (for example, PLA profiles with +0.1–0.2 mm hole enlargement, Nylon profiles with nominal diameters) to account for shrinkage and flow.
- Expose **interference** (insert OD minus hole diameter) as a first‑class derived parameter, making it easy to warn users when interference becomes too low or too high for a given material.


## 5. Implications for your tooling

Given the above:

- For threads, prefer `ThreadInfo.create` and `ThreadDataQuery` in new Fusion‑based tools, with a clear abstraction over modeled vs cosmetic threads and fallback strategies for intersecting cases.
- For geometry operations, treat patterns, mirror, loft, and sweep (including guide rails) as primary building blocks; regard Coil and certain sheet metal commands as UI‑only and avoid depending on them for critical automation.
- For a parametric catalog, adopt a Tinkercad‑style parameter schema and CSG composition model, decoupling part definitions from any single CAD backend.
- For heat‑set inserts, maintain a vendor‑annotated table of dimensions and recommended holes similar to the table above, but always present boss OD, bore, and depth as adjustable parameters tied to material profiles rather than immovable constants.

---

## References

1. [Fusion Help | ThreadInfo.create Method](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ThreadInfo_create.htm) - ThreadInfo.create Method

2. [Fusion Help | ThreadInfo.create Method | Autodesk](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-C034DCCE-3B19-4C48-8327-A74AC6E5F58F) - This method creates a new ThreadInfo object that can be used to create a thread or tapped-hole featu...

3. [Fusion Help | ThreadFeatures.createThreadInfo Method](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ThreadFeatures_createThreadInfo.htm) - ThreadFeatures.createThreadInfo Method

4. [what is the way to change the thread paramters like pitch using the API script?](https://stackoverflow.com/questions/79158047/what-is-the-way-to-change-the-thread-paramters-like-pitch-using-the-api-script) - I think i wasnt very clear in my question, sorry for that. I want to automate the bolt generation pr...

5. [Thread Feature API Sample](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ThreadFeatureSample_Sample.htm) - Thread Feature API Sample Sample

6. [ThreadFeatures.threadDataQuery Property](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ThreadFeatures_threadDataQuery.htm) - This is a read only property whose value is a ThreadDataQuery. Samples. Name, Description. Thread Fe...

7. [Getting Started with Fusion's API - Autodesk product documentation](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/BasicConcepts_UM.htm) - The Fusion API is an object oriented API exposed through a set of objects. Many of these objects hav...

8. [THREAD TOOL Tutorial - Autodesk Fusion 360 Tool Tutorial](https://www.youtube.com/watch?v=eWGCv48ylEQ) - In today’s video, we’re going to talk about how to use the thread tool in Autodesk Fusion 360 to add...

9. [How to Create Internal and External Threads in Fusion 360! - YouTube](https://www.youtube.com/watch?v=dSS3SWLIuZk) - Follow my Instagram: @bedadevelopment for more content and 3D prints! Link to Forum Post: ...

10. [Intermediate Solid Features in Fusion 360](https://dozuki.umd.edu/Guide/Intermediate+Solid+Features+in+Fusion+360/284) - This guide covers a few of the more advanced solid features in Fusion 360

11. [Thread missing in STL export : r/Fusion360 - Reddit](https://www.reddit.com/r/Fusion360/comments/gujegt/thread_missing_in_stl_export/) - You'll need to check the 'Modeled' option in the Thread dialog box. If you don't select this, Fusion...

12. [3D Printed Threads - Model Them in Fusion 360 | Practical Prints #2](https://www.youtube.com/watch?v=aGWrFeu8Hv0) - Learn how to create 3D Printable threads in Fusion 360. I'll show you how to add clearances based on...

13. [Modeled Threads are not being exported - Autodesk Forums](https://forums.autodesk.com/t5/fusion-support-forum/modeled-threads-are-not-being-exported/td-p/12447094) - Fusion today does not support modeled tapered threads. Modeled option is only available for non-tape...

14. [Intersecting modeled threads in fusion 360 - Autodesk Community](https://forums.autodesk.com/t5/fusion-support-forum/intersecting-modeled-threads-in-fusion-360/td-p/10976756) - Hello, I've been trying to make intersecting modeled threads for 3d printing in Fusion 360, it's a p...

15. [Creating custom threads in Fusion 360 for macOS](https://www.youtube.com/watch?v=Ni36gX-1iAc) - Fusion 360 Article - Creating Custom Threads: https://knowledge.autodesk.com/support/fusion-360/lear...

16. [How to Create Threads | Fusion 360 Tutorial 14](https://www.youtube.com/watch?v=ec2h1HvT_NM) - In this tutorial, we show you how to make threads using two different methods. The first method uses...

17. [Custom threads in Fusion360 (multi start thread, custom profile)](https://www.youtube.com/watch?v=nwsPWjqPz6M) - Designing threads in Fusion360 is very easy until we need only standard single start threads. But if...

18. [Location of Standard Thread Files - Autodesk Forums](https://forums.autodesk.com/t5/fusion-support-forum/location-of-standard-thread-files/td-p/8334098) - Solved: Previously I had inserted a custom thread XML file into the threaddata directory of Fusion. ...

19. [How to add Custom Threads to Fusion 360! - YouTube](https://www.youtube.com/watch?v=VPDngPAvFnQ) - ... thread configurations to Fusion 360. Path: C:\Users\[USER]\AppData\Local\Autodesk\webdeploy\prod...

20. [ThreadKeeper | Fusion - Autodesk App Store](https://apps.autodesk.com/FUSION/en/Detail/HelpDoc?appId=1725038115223093226&appLang=en&os=Mac) - ThreadKeeper is an add-in that restores custom thread definitions every time they are removed (i.e. ...

21. [How to Create Custom Threads in Fusion 360 for Corcelain ...](https://www.perry.qa/blog/corcelain-thread-in-fusion) - To add custom threads for Corcelain extensions in Fusion 360, copy the XML below and place it in the...

22. [How to Create Custom Threads in Fusion 360 - YouTube](https://www.youtube.com/watch?v=fnzqt2QBTEE) - To create custom threads in Fusion 360, you'll need ... XML document and save it within the program'...

23. [Solved: Current location of thread Data - Autodesk Community](https://forums.autodesk.com/t5/fusion-design-validate-document/current-location-of-thread-data/td-p/10446744) - The threaddata folder often gets moved when Fusion receives an update. It's a real pain to do it man...

24. [Thread data directory - where is it nowadays? - Autodesk Forums](https://forums.autodesk.com/t5/fusion-design-validate-document/thread-data-directory-where-is-it-nowadays/td-p/9480310) - It used to be (for Windows): %localappdata%\Autodesk\webdeploy\Production\<version ID>\Fusion\Server...

25. [ThreadKeeper is an Autodesk® Fusion 360™ add-in that ... - GitHub](https://github.com/thomasa88/ThreadKeeper) - ThreadKeeper is an Autodesk Fusion add-in that restores custom thread definitions every time they ar...

26. [ThreadKeeper | Fusion - Autodesk App Store](https://apps.autodesk.com/FUSION/en/Detail/HelpDoc?appId=1725038115223093226&appLang=en&os=Win64) - ThreadKeeper is an add-in that restores custom thread definitions every time they are removed (ie wh...

27. [GitHub - andypugh/FusionThreads: Tool and data to create custom threads for Fusion 360](https://github.com/andypugh/FusionThreads) - Tool and data to create custom threads for Fusion 360 - andypugh/FusionThreads

28. [Fusion 360 Thread Profiles for 3D-Printed Threads](https://github.com/BalzGuenat/CustomThreads) - Fusion 360 Thread Profiles for 3D-Printed Threads. Contribute to BalzGuenat/CustomThreads developmen...

29. [Fusion Help | Get Physical Properties API Sample | Autodesk](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/GetPhysicalProperties_Sample.htm) - Get Physical Properties API Sample Sample

30. [Fusion 360 API: Feature Creation](https://www.youtube.com/watch?v=RV5bEgG81v4) - This video quickly demonstrates the feature creation process by accessing the correct collections an...

31. [Fusion API: Add Simple Extrude Feature and Add by Input](https://blog.autodesk.io/fusion-api-add-simple-extrude-feature-and-add-by-input/) - In the past, when creating the extrude feature, we will need to create an ExtrudeInput firstly, then...

32. [Fusion Help | SweepFeatures.createInput Method | Autodesk](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/SweepFeatures_createInput.htm) - SweepFeatures.createInput Method

33. [Fusion 360 API: Input Objects](https://www.youtube.com/watch?v=ps1hmrBj3dI) - Building off the Feature Creation video, this video demonstrates the use of input objects to create ...

34. [Add Rectangular Pattern Feature to Component - Forums, Autodesk](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/add-rectangular-pattern-feature-to-component/td-p/11355874) - Hi, I've pasted a code example below that creates a Rectangular Pattern Feature and adds it to a new...

35. [Parametric Modeling With Fusion 360 API : 7 Steps](https://www.instructables.com/Parametric-Modeling-With-Fusion-360-API/) - Parametric Modeling With Fusion 360 API: Who This Guide Is For: This guide assumes you have some pro...

36. [Lofting two lofts through API - Autodesk Forums](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/lofting-two-lofts-through-api/td-p/7882811) - Here's part of the code I have so far for the lofting. # Create input loftFeats = rootComp.features....

37. [Fusion Help | Loft Feature API Sample | Autodesk](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-a03e26b4-4a3c-11e6-a2e4-3417ebd41e19) - Create loft feature input loftFeats = rootComp.features.loftFeatures loftInput = loftFeats.createInp...

38. [FUSION 360 How to use the COIL tool | All coil options explained](https://www.youtube.com/watch?v=stc73_GKvps) - How to use the COIL Feature in Autodesk Fusion 360 (for Complete Beginners) Learn how to create diff...

39. [How to create coil in Fusion 360 - YouTube](https://www.youtube.com/watch?v=cIAzElIRptk) - Add a comment... 10:53. Go to channel Learn Everything About Design · How To Make Any Tapered Coil i...

40. [Creating a Coil similar to coil feature? - Autodesk Forums](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/creating-a-coil-similar-to-coil-feature/td-p/12826499) - I am trying to create a coil programically, but it seems for whatever reason the CoilFeature does no...

41. [[PDF] Getting Started with the Fusion 360 API - Autodesk](https://static.au-uw2-prd.autodesk.com/Class_Handout_SD468474.pdf) - This class will cover a basic overview of the Fusion 360 API and how to get started. We will introdu...

42. [Error "inputEntities should be of a single type" even though there is ...](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/error-quot-inputentities-should-be-of-a-single-type-quot-even/td-p/12738005) - Solved: Hi, I'm trying to mirror a component in a script but I get the error "RuntimeError: 3 : inpu...

43. [Solved: Mirroring a surface - Autodesk Forums](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/mirroring-a-surface/td-p/10309658) - mirrorInput = mirrorFeatures.createInput(inputEntites, hullComponent.xYConstructionPlane) mirrorFeat...

44. [How to create a mirror feature with a Join Operation?](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/how-to-create-a-mirror-feature-with-a-join-operation/td-p/12723568) - I would like to mirror a body, it works fine except that the operation by default is set to New Feat...

45. [Loft issue "the selected rail does not touch all of the profiles" (Fusion ...](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/loft-issue-quot-the-selected-rail-does-not-touch-all-of-the/td-p/9352664) - I am working on a parametric design using the fusion API, and I'm having an issue with the loft func...

46. [Solved: Howto grafully handle creating a loft that would intersect itself](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/howto-grafully-handle-creating-a-loft-that-would-intersect/td-p/9233881) - I found one fix that I will investigate more and that is setting the "setDirectionEndCondition" for ...

47. [Fusion Help | SweepFeatures.add Method](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/SweepFeatures_add.htm) - SweepFeatures.add Method

48. [QUICK TIP: Sheet Metal Contour Flanges - Fusion Blog - Autodesk](https://www.autodesk.com/products/fusion-360/blog/quick-tip-sheet-metal-contour-flange/) - Create sheet metal flanges using sketch contours, and see how Fusion 360 can automatically miter fla...

49. [FUSION 360- How to create sheet metal parts- what is a ... - YouTube](https://www.youtube.com/watch?v=LVnO-LCQFZw) - How to use the Sheet Metal Features in Autodesk Fusion 360 (for Complete Beginners) Learn how to cre...

50. [Sheet Metal Rules in Autodesk Fusion 360 - YouTube](https://www.youtube.com/watch?v=LXOAsfJbgSE) - Sheet Metal Rules | Autodesk Fusion 360 | Tutorial (Intermediate) In this episode, we'll be looking ...

51. [Learn Essential Sheet Metal Basics in Autodesk Fusion](https://www.autodesk.com/products/fusion-360/blog/learn-sheet-metal-basics-autodesk-fusion/) - This video tutorial covers key functionalities, such as creating sheet metal components, applying ru...

52. [Access sheet metal rules from API? - Autodesk Forums](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/access-sheet-metal-rules-from-api/td-p/8006475) - Solved: Is it possible to access the parameters that make up the sheet metal rules from within the A...

53. [Solved: python sheetmetalfeatures & bending - Autodesk Community](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/python-sheetmetalfeatures-amp-bending/td-p/13046782) - I am producing tank vessel drawings in python but I am unable to activate the SheetMetalFeeatures, s...

54. [Requesting "Convert to sheetmetal" be open to the API](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/requesting-quot-convert-to-sheetmetal-quot-be-open-to-the-api/td-p/14004048) - Solved: I have a manufacturing add in that I would like to automate converting items to sheet metal....

55. [Fusion 360 API: 用简易法与定义法创建拉伸特征](https://blog.csdn.net/autodeskinventorapi/article/details/54744483) - 文章浏览阅读1.5k次。此文翻译自我近期在全球博客上撰写的文章。原文地址：http://adndevblog.typepad.com/manufacturing/2017/01/fusion-api-...

56. [Fusion Help | ShellFeatures.createInput Method](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ShellFeatures_createInput.htm) - ShellFeatures.createInput Method

57. [ExtendFeatures.createInput Method](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExtendFeatures_createInput.htm) - createInput Method. Parent Object: ExtendFeatures. Defined in namespace "adsk::fusion" and the heade...

58. [Overview : 8 Steps - Instructables](https://www.instructables.com/Overview-6/) - In the first activity, we will use a Tinkercad Shape Generator to create a shape that already exists...

59. [API Tinkercad](https://www.blascarr.com/?p=969) - API Tinkercad. Diseño paramétrico usando la API de Tinkercad para desarrollar unas piezas para los a...

60. [Good tool/program for programmatically creating objects? : r/cad](https://www.reddit.com/r/cad/comments/7kyobw/good_toolprogram_for_programmatically_creating/) - I've been trying to use Tinkercad's Shape Generator tool where you write Javascript to generate an o...

61. [[PDF] Basic 3D Design - RobotLAB](https://www.robotlab.com/hubfs/Education.Robotlab.com/Engineering%20Design%20with%203D%20printing/3D%20Printer%20Tinker%20Cad.pdf) - Tinkercad shape generator. • We're going to use this as a doormat. • Insert it in front of your door...

62. [Tinkercad Tutorial - Lesson 33 - Shape Generators - YouTube](https://www.youtube.com/watch?v=6-6sPmm8QUE) - In this tutorial, we will be discussing about Shape Generators in Tinkercad #tinkercad ... Meet the ...

63. [13. New TinkerCAD - Shape Generators - YouTube](https://www.youtube.com/watch?v=NxMZZE9xCOY) - 15. New TinkerCAD - SVG Files. jumekubo4edu · 3.3K views ; Modify Existing STL files easily using Ti...

64. [# OpenJSCAD](https://coshape.io/documentation/main_file/openjscad.html) - Generative design tools for custom manufacturing

65. [Tutorial: Using Parameters](https://jscad.app/docs/tutorial-03_usingParameters.html)

66. [Tutorial: Using Parameters - Documentation](https://openjscad.xyz/docs/tutorial-03_usingParameters.html)

67. [View all Shape Generators ?](https://www.hubs.com/talk/t/view-all-shape-generators/2263/) - In Tinkercad, is there any way to view more ( or pref. ALL ) of the community Shape Generators on th...

68. [CNCKitchen Lead & Cadmium Free Heat Set Inserts - KB-3D Store](https://kb-3d.com/store/inserts-fasteners-adhesives/927-cnckitchen-lead-cadmium-free-heat-set-inserts-multiple-sizes-metric.html) - CNC Kitchen offers these premium heat set inserts machined from a lead and cadmium free brass alloy....

69. [ruthex Threaded Inserts M4 (50 pieces), M4x8.1 - 3DJake](https://www.3djake.com/ruthex/threaded-inserts-m4-50-pieces) - The set consists of 50 inserts with M4 internal thread and a length of 8.1 mm. Technical specificati...

70. [ruthex Threaded Insert M3 (100 pieces) - M3x5.7 - 3DJake](https://www.3djake.com/ruthex/threaded-insert-m3-100-pieces) - The set consists of 100 inserts with M3 internal thread and a length of 5.7 mm. Technical specificat...

71. [ruthex Threaded Inserts M8 (20 pieces) - 3DJake International](https://www.3djake.com/ruthex/threaded-inserts-m8-20-pieces) - The set consists of 20 inserts with M8 internal thread and a length of 12.7 mm. Technical specificat...

72. [Threaded Inserts for 3D Prints - Cheap VS Expensive - CNC Kitchen](https://www.cnckitchen.com/blog/threaded-inserts-for-3d-prints-cheap-vs-expensive) - The cheap ones sell for a good 3 bucks for 100 which makes them 3 cents each. The Ruthex ones cost 8...

73. [Brass Heat-Set Inserts for Plastic - M3 x 4mm - 50 pack - Adafruit](https://www.adafruit.com/product/4255) - Wanna improve the connection strength between your project's 3D-printed parts, and also have nice cl...

74. [Heat-Set Inserts - McMaster-Carr](https://www.mcmaster.com/products/heat-set-inserts/) - Choose from our selection of heat-set inserts, including threaded inserts, nuts, and more. Same and ...

75. [How big should I make the hole for these heat-set threaded inserts?](https://www.reddit.com/r/3Dprinting/comments/ytqly9/how_big_should_i_make_the_hole_for_these_heatset/) - Base on the m3 is about 4.3 so 4.5 is a good size depending on how small your holes actually print. ...

121. [Drive parameters from sheet metal rules : r/Fusion360 - Reddit](https://www.reddit.com/r/Fusion360/comments/18vc9nv/drive_parameters_from_sheet_metal_rules/) - I'm trying to drive feature parameters from sheet metal rules. Specifically thickness. I created a u...

