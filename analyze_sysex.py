#!/usr/bin/env python3
"""Analyze and debug NuEVI sysex dumps (.syx or .mid files)."""

import json
import os
import sys

YELLOW = '\033[33m'
RESET  = '\033[0m'

def warn(s):
    return f"{YELLOW}{s}{RESET}"

# ── Sysex encoding helpers ────────────────────────────────────────────────────

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

def to_midi_crc(crc):
    return bytes([(crc >> 24) & 0x7F, (crc >> 16) & 0x7F,
                  (crc >>  8) & 0x7F,  crc         & 0x7F])

# ── Sysex finder ─────────────────────────────────────────────────────────────

SYSEX_HEADER_LEN = 13   # vendor(3) + command(8) + payloadSize(2)
SYSEX_CRC_LEN    = 4
CMD              = b'NuEVIc01'
KNOWN_VENDOR     = bytes([0x00, 0x3E, 0x7F])
NO_CHECKSUM      = bytes([0x00, 0x7F, 0x00, 0x7F])

def find_sysex(data):
    """Scan raw bytes for NuEVI sysex payload; return slice or raise ValueError."""
    min_len = SYSEX_HEADER_LEN + SYSEX_CRC_LEN
    for i in range(len(data) - min_len + 1):
        if data[i + 3 : i + 11] == CMD:
            payload_size = from_midi_u16(data[i + 11], data[i + 12])
            total = SYSEX_HEADER_LEN + payload_size + SYSEX_CRC_LEN
            if i + total <= len(data):
                return data[i : i + total]
    raise ValueError('No NuEVI config sysex found in file')

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
        with open(path, 'rb') as f:
            raw = f.read()
    else:
        raw = sys.stdin.buffer.read()

    try:
        sysex = find_sysex(raw)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    vendor_id    = sysex[0:3]
    command      = sysex[3:11].decode('ascii', errors='replace')
    payload_size = from_midi_u16(sysex[11], sysex[12])

    # ── MSB check (all sysex bytes must be 0x00–0x7F) ────────────────────────
    msb_offenders = [i for i, b in enumerate(sysex) if b & 0x80]
    if msb_offenders:
        offsets = ', '.join(f'{i:02X}' for i in msb_offenders)
        print(warn(f"MSB set in sysex data at byte offset(s): {offsets}"))
        print()

    # ── Header ────────────────────────────────────────────────────────────────
    vendor_fmt = ' '.join(f'{b:02X}' for b in vendor_id)
    vendor_line = f"Vendor ID:    {vendor_fmt}"
    if vendor_id != KNOWN_VENDOR:
        vendor_line += f"  {warn('(unknown vendor)')}"
    print(vendor_line)
    print(f"Command:      {command}")
    print(f"Payload size: {payload_size}")
    print()

    # ── Config items ──────────────────────────────────────────────────────────
    script_dir  = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config-items.json')
    with open(config_path) as f:
        sections = json.load(f)

    items_by_addr = {}
    for section in sections:
        for item_id, item in section['items'].items():
            items_by_addr[item['address']] = (item_id, item)

    # Decode payload values
    payload_base = 13
    values = {}
    for addr in range(0, payload_size, 2):
        b0 = sysex[payload_base + addr]
        b1 = sysex[payload_base + addr + 1]
        values[addr] = from_midi_u16(b0, b1)

    # Print each address
    for addr in sorted(values):
        raw_val = values[addr]
        if addr in items_by_addr:
            item_id, item = items_by_addr[addr]
            offset = 0
            dm = item.get('dataModel', '')
            if dm.startswith('offset:'):
                offset = int(dm[7:])
            display_val = raw_val - offset
            line = f"  {addr:02X}  {item_id}: {display_val}"
            if raw_val < item['min'] or raw_val > item['max']:
                line += f"  {warn('Outside valid range!')}"
        else:
            line = f"  {addr:02X}  (unknown): {raw_val}"
            if raw_val != 0:
                line += f"  {warn('Non-zero value in unassigned space!')}"
        print(line)

    print()

    # ── CRC ───────────────────────────────────────────────────────────────────
    checksum_pos = payload_base + payload_size
    stored = sysex[checksum_pos : checksum_pos + SYSEX_CRC_LEN]
    stored_hex = stored.hex().upper()

    if stored == NO_CHECKSUM:
        print(f"CRC32: {warn('NO_CHECKSUM magic — not verified')}")
    else:
        expected = to_midi_crc(crc32(sysex[:checksum_pos]))
        expected_hex = expected.hex().upper()
        if stored == expected:
            print(f"CRC32: {stored_hex} OK")
        else:
            print(f"CRC32: {stored_hex}  {warn(f'Invalid — expected {expected_hex}')}")

if __name__ == '__main__':
    main()
