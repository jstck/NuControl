# NuControl

A browser-based configuration editor for the [NuEVI](https://berglundaudio.com/) wind controller (EWI-style MIDI instrument by Berglund Audio).

## Usage

Open `config.html` in a browser — no server, build step, or installation required.

## Features

- **Load / Save** configuration files in three formats:
  - `.json` — human-readable config with name, comment, and timestamp
  - `.mid` — standard type-0 MIDI file containing a NuEVI sysex dump
  - `.syx` — raw sysex payload (205 bytes), loadable directly from the instrument or librarian software
- **Version gating** — items introduced in a later firmware version than the loaded config are hidden automatically; loading a file with mismatched items shows a yellow warning
- **Checksum validation** — CRC32 is verified on load; mismatches warn rather than block
- **Four input styles** driven by `uiModel` in `config-items.json`:
  - Default numeric text input with ▲/▼ stepper buttons
  - `slider` — range slider for wide-range values (e.g. hardware calibration)
  - `select` — styled dropdown for enumerated options
  - `bitfield` — a column of checkboxes for packed bit flags
- **Offset display** via `dataModel: "offset:N"` — stores the raw value but displays and accepts signed/offset values (e.g. transpose shown as −12 to +12)

## File format

NuEVI config sysex structure (205 bytes):

| Bytes | Content |
|-------|---------|
| 0–2 | Vendor ID `00 3E 7F` |
| 3–10 | Command `NuEVIc01` (ASCII) |
| 11–12 | Payload size (7-bit MIDI encoded uint16, always 188) |
| 13–200 | 94 × uint16 config values (7-bit MIDI encoded, 2 bytes each) |
| 201–204 | CRC32 (IEEE 802.3, 4 bytes with MSB stripped) |

When wrapped in a `.mid` file the payload sits in a type-0 MIDI file with a single track-0 sysex event.

## Config items

Defined in `config-items.json` as an array of sections. Each item has:

```json
"ID": {
  "address":        0,
  "friendlyName":   "Human readable name",
  "min":            0,
  "max":            127,
  "factoryDefault": 0,
  "minVersion":     24,
  "uiModel":        "slider | select:v;label:... | bitfield:bit;label:...",
  "dataModel":      "offset:N"
}
```

`address` is the byte offset within the 188-byte EEPROM payload (always even; each value occupies 2 bytes).

## Tech stack

Single-file web app — `config.html` + `config.css`. Uses Vue 3 via CDN (no build step). All sysex encoding/decoding and MIDI file parsing is implemented in plain JavaScript in `config.html`.
