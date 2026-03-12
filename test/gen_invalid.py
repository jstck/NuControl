#!/usr/bin/env python3
"""Generate invalid test sysex files from default_47.syx."""

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def crc32(data):
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
    return (~crc) & 0xFFFFFFFF

def from_midi_u16(b0, b1):
    return ((b0 & 0x7F) << 7) | (b1 & 0x7F)

def to_midi_u16(v):
    return [(v >> 7) & 0x7F, v & 0x7F]

def to_midi_crc(crc):
    return bytes([(crc >> 24) & 0x7F, (crc >> 16) & 0x7F,
                  (crc >>  8) & 0x7F,  crc         & 0x7F])

def add_crc(data):
    return bytes(data) + to_midi_crc(crc32(bytes(data)))

def save(name, data):
    path = os.path.join(SCRIPT_DIR, name)
    open(path, 'wb').write(data)
    print(f"  {name}: {len(data)} bytes")

HEADER_LEN = 13
CRC_LEN = 4

raw = open(os.path.join(SCRIPT_DIR, 'default_47.syx'), 'rb').read()
payload_size = from_midi_u16(raw[11], raw[12])  # 188
version = from_midi_u16(raw[13], raw[14])        # VERSION field at address 0

print(f"Source: default_47.syx  payload_size={payload_size}  VERSION={version}")
print("Generating:")

# Helpers: base = header + payload (no CRC)
def base():
    return bytearray(raw[:HEADER_LEN + payload_size])

# ── invalid_crc: replace CRC bytes with junk ─────────────────────────────────
data = bytearray(raw)
data[-4:] = bytes([0x12, 0x34, 0x56, 0x78])
save('invalid_crc.syx', bytes(data))

# ── invalid_msb: set MSB on low byte of BREATH_THR (addr 2) and DIPSW_BITS (addr 66)
# File offsets: addr N → bytes 13+N (high), 13+N+1 (low)
# BREATH_THR low byte: 13+2+1 = 16
# DIPSW_BITS low byte: 13+66+1 = 80
data = base()
data[16] |= 0x80   # BREATH_THR low byte
data[80] |= 0x80   # DIPSW_BITS low byte
save('invalid_msb.syx', add_crc(data))

# ── invalid_range: BREATH_THR=5000 (max=4095), OCTAVE=10 (max=6)
# BREATH_THR: file bytes 15,16 (addr 2)
# OCTAVE: file bytes 53,54 (addr 40)
data = base()
data[15], data[16] = to_midi_u16(5000)
data[53], data[54] = to_midi_u16(10)
save('invalid_range.syx', add_crc(data))

# ── invalid_unused: non-zero data at gap addresses 142 and 144
# (gap between FWCTYPE@140 and HMZKEY@150)
# File bytes: addr 142 → 155,156;  addr 144 → 157,158
data = base()
data[155], data[156] = to_midi_u16(42)
data[157], data[158] = to_midi_u16(17)
save('invalid_unused.syx', add_crc(data))

# ── invalid_version: VERSION says 47 but payload only covers up to version 40
# Max address for version-40 items: LEVER_MAX at addr 166 → payload_size = 168
V40_PAYLOAD_SIZE = 168
data = bytearray(raw[:HEADER_LEN + V40_PAYLOAD_SIZE])
data[11], data[12] = to_midi_u16(V40_PAYLOAD_SIZE)   # update size field
data[13], data[14] = to_midi_u16(47)                  # set VERSION = 47
save('invalid_version.syx', add_crc(data))

# ── invalid_size: payload_size field says 180 (8 less than actual 188 payload bytes)
# Full 188-byte payload is present; CRC covers all of it (at offset 201).
# Parser reads size=180, looks for CRC at offset 193 — finds payload data instead,
# so CRC check fails. Version/size check also fires (payload < expected for version).
data = base()                                          # 13+188 = 201 bytes
data[11], data[12] = to_midi_u16(180)                 # size field says 180
save('invalid_size.syx', add_crc(data))               # CRC over all 201 bytes, at 201

# ── invalid_command: change "NuEVIc01" → "NuFOOx99" (scanner won't find it)
data = base()
data[3:11] = b'NuFOOx99'
save('invalid_command.syx', add_crc(data))

print("Done.")
