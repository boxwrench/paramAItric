# Private Intake Layout

Use the ignored `private/reference_intake/` tree for raw and derived intake material.

## Expected Layout

```text
private/reference_intake/
  enclosures-and-covers/
    raw/
    derived/
    scratch/
```

## Usage

- `raw/`
  - original reference artifacts
- `derived/`
  - extracted text
  - page images
  - cropped callout views
- `scratch/`
  - temporary notes and one-off preprocessing output

## Rule

Keep only normalized notes in tracked `internal/reference_parts/`.
Keep raw packets and temporary derivatives in ignored `private/reference_intake/`.
