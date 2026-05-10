# risa-form-automation

Automatic horse racing form spreadsheet generator.

## What it does now

- Loads your uploaded workbook and **duplicates the `template` sheet** into `Race 1`, `Race 2`, etc.
- Clears/rebuilds race tabs each run.
- Writes runners in contiguous rows (no skipped lines).
- Fills mapped columns used by your workflow where data is available from parsed input:
  - `A`: horse number
  - `B`: horse name
  - `P`: today's adjusted weight
  - `D/E/I/K` on the analysis row (`row + 1`): last-run rating / declared weight / carried weight / margin
  - `U`: most recent race class
  - `V`: 3yo sex note (e.g. `3yo filly`)
  - `AA/AD`: horse name repeat
  - `AE/AF/AG/AH`: campaign and record fields

## API

### `POST /generate`

Form-data:
- `risa_file`: RISA PDF
- `excel_template`: Excel workbook containing a `template` tab

Returns: `completed_form.xlsx`

## Notes

The parser currently extracts race and runner identity reliably, and scaffolds all downstream horse fields so they can be populated as parsing rules for your exact RISA format are expanded.
