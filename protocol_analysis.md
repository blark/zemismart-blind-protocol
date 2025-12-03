# Blind Controller Protocol Analysis

**Device**: Zemismart motorized blind/shade controller remotes
**Remotes analyzed**: Living room (`0x93`), Office (`0x7c`), Spare room (`0x45`)

## Modulation

- **Frequency**: 433.92 MHz
- **Type**: OOK PWM (On-Off Keying, Pulse Width Modulation)
- **Encoding**: Short pulse (~263 µs) = 0, Long pulse (~582 µs) = 1

## Timing Parameters

| Parameter | Value |
|-----------|-------|
| Short pulse (bit 0) | ~263 µs |
| Long pulse (bit 1) | ~582 µs |
| Sync delimiter | ~4960 µs gap |
| Bit period | ~876 µs |
| Inter-burst gap | ~5000-19000 µs (variable) |

## Transmission Structure

```
┌────────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐        ┌────────┐ ┌────┐
│preamble│ │code│ │code│ │code│ │code│ │code│ │code│        │preamble│ │code│...
└────────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘        └────────┘ └────┘
          ↑      ↑      ↑      ↑      ↑      ↑         ↑              ↑
         sync   sync   sync   sync   sync   sync      GAP           sync

|<----------------- burst 1 (×6 codes) --------------->|   |<----- burst 2 ...
```

- **preamble**: 8-bit `0xFF` (all 1s)
- **sync**: ~4960 µs gap delimiter preceding each code
- **code**: 65-bit payload (64 data + 1 trailing sync bit, always 0)
- **GAP**: Variable inter-burst gap (~5000-19000 µs)

The sync delimiter (~4960 µs) appears before each code within a burst. The inter-burst GAP separates the two bursts and varies with transmitter timing - sometimes nearly indistinguishable from sync:

| Sample | Inter-burst GAP | Notes |
|--------|-----------------|-------|
| up_03 | ~5,002 µs | Nearly equals sync timing |
| up_02 | ~6,796 µs | |
| up_05 | ~8,792 µs | |
| up_01 | ~9,790 µs | |
| up_04 | ~18,765 µs | ~4× longer than minimum |

### Button Patterns

- **UP/DOWN**: Two bursts (action code + trailer code)
- **STOP**: Single burst (action code only)

## 64-bit Payload Format

```
5c5d92         93         0000       f47b
└──24 bits───┘└──8 bits──┘└─16 bits─┘└─16 bits─┘
   Prefix      Remote ID   Channel     Command
  (static)     (static)  (calculated) (calculated)
```

### Formulas

**Channel Field:**
```python
if ch == 0:  return 0x0000                      # CC (broadcast)
return 0xFFFF ^ (1 << ((ch + 7) % 16))          # Ch 1-16
```

**Command Field:**
```python
BASE = {'UP': 0xf3e8, 'DOWN': 0xbbb0, 'STOP': 0xdbd0, 'TRAILER': 0xdacf}
REMOTE = {'living_room': 0x93, 'office': 0x7c, 'spare_room': 0x45}

if ch == 0:  offset = 0                           # CC (broadcast)
else:        offset = 2 + (1 << ((ch - 1) % 8))   # Ch 1-16

return (BASE[button] + REMOTE[remote] - offset) & 0xFFFF
```

---

### Field Details

**Static Fields:**
- **Prefix** (24 bits): `0x5c5d92` - Manufacturer/protocol identifier
- **Remote ID** (8 bits): Unique per-remote (e.g., `0x93`, `0x7c`, `0x45`)

**Channel Field** - each channel clears one bit from `0xFFFF`:

| Channel | Field | Binary | Bit Cleared |
|---------|-------|--------|-------------|
| CC | `0x0000` | `00000000 00000000` | (broadcast) |
| 1 | `0xfeff` | `11111110 11111111` | bit 8 |
| 2 | `0xfdff` | `11111101 11111111` | bit 9 |
| 3 | `0xfbff` | `11111011 11111111` | bit 10 |
| 4 | `0xf7ff` | `11110111 11111111` | bit 11 |
| 5 | `0xefff` | `11101111 11111111` | bit 12 |
| 6 | `0xdfff` | `11011111 11111111` | bit 13 |
| 7 | `0xbfff` | `10111111 11111111` | bit 14 |
| 8 | `0x7fff` | `01111111 11111111` | bit 15 |
| 9 | `0xfffe` | `11111111 11111110` | bit 0 |
| 10 | `0xfffd` | `11111111 11111101` | bit 1 |
| 11 | `0xfffb` | `11111111 11111011` | bit 2 |
| 12 | `0xfff7` | `11111111 11110111` | bit 3 |
| 13 | `0xffef` | `11111111 11101111` | bit 4 |
| 14 | `0xffdf` | `11111111 11011111` | bit 5 |
| 15 | `0xffbf` | `11111111 10111111` | bit 6 |
| 16 | `0xff7f` | `11111111 01111111` | bit 7 |

**Channel Offset** - constant `2` plus exponentially shifting bit:

| Channel | Offset | Binary | Breakdown |
|---------|--------|--------|-----------|
| CC | 0 | `00000000` | (broadcast) |
| 1 | 3 | `00000011` | `00000010` + `00000001` |
| 2 | 4 | `00000100` | `00000010` + `00000010` |
| 3 | 6 | `00000110` | `00000010` + `00000100` |
| 4 | 10 | `00001010` | `00000010` + `00001000` |
| 5 | 18 | `00010010` | `00000010` + `00010000` |
| 6 | 34 | `00100010` | `00000010` + `00100000` |
| 7 | 66 | `01000010` | `00000010` + `01000000` |
| 8 | -126* | `10000010` | `00000010` + `10000000` |
| 9-16 | | | (mirrors 1-8 via modulo) |

\*130 exceeds signed 8-bit max (127), wraps to -126

**Example Calculations:**

| Remote | Channel | Button | Calculation | Result |
|--------|---------|--------|-------------|--------|
| Living room (`0x93`) | CC | UP | `0xf3e8 + 0x93 - 0` | `0xf47b` |
| Office (`0x7c`) | CC | DOWN | `0xbbb0 + 0x7c - 0` | `0xbc2c` |
| Spare room (`0x45`) | 5 | UP | `0xf3e8 + 0x45 - 18` | `0xf41b` |

## Working Flex Decoder

```bash
rtl_433 -X 'n=name,m=OOK_PWM,s=263,l=582,r=9790,g=6700,t=0,y=4960'
```

### Decoder Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| s | 263 | Short pulse width (µs) |
| l | 582 | Long pulse width (µs) |
| r | 9790 | Reset limit - gap that ends a transmission (µs) |
| g | 6700 | Gap limit - separates rows within transmission (µs) |
| t | 0 | Tolerance |
| y | 4960 | Sync pulse width (µs) |

## Open Questions

**Why do UP/DOWN send a trailer code but STOP doesn't?**
- UP/DOWN start continuous motor movement - trailer may signal "end of command, motor can stop listening"
- STOP is instantaneous - no need to signal completion

**Why use exponential channel offsets (2^n) instead of linear?**
- Maximizes bit distance between channels for error detection
- Likely tied to 8-bit microcontroller - same bit index used for channel field and offset calculation
- Acts as simple checksum: receiver validates `command - BASE - remote_id` matches expected offset for that channel

## Verified Remotes

| Location | Remote ID | Verified |
|----------|-----------|----------|
| Living room | `0x93` | CC, Ch1, Ch3 |
| Office | `0x7c` | CC |
| Spare room | `0x45` | Ch2-Ch6, Ch9-Ch11, Ch16 |

## Notes

- Command derivation formula verified across 3 different remotes
- Channel offset formula verified for 10 channels (1-6, 9-11, 16)
- Channels 9-16 mirror 1-8 using `(ch-1) mod 8` in the exponent
- Ch8 and Ch16 use signed 8-bit wraparound (130 → -126)
