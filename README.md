# Zemismart Blind Controller Protocol

Reverse-engineered RF protocol for Zemismart motorized blind/shade remotes.

## Quick Start

**Decode a captured payload:**
```python
from generate_command import decode_payload

decode_payload(0x5c5d9293fefff4780)  # -> 'living_room ch1 UP'
```

**Generate a command:**
```python
from generate_command import generate_transmission

generate_transmission(0x93, 5, 'UP')  # remote_id, channel, button
```

**Capture with LimeSDR:**
```bash
python capture_rx.py output.cu8 10  # 10 second capture
```

**Decode with rtl_433:**
```bash
rtl_433 -r capture.cu8 -s 2000000 -X 'n=name,m=OOK_PWM,s=263,l=582,r=9790,g=6700,t=0,y=4960'
```

## Protocol Summary

- **Frequency:** 433.92 MHz
- **Modulation:** OOK PWM (short=0, long=1)
- **Payload:** 64 bits

```
[prefix 24b][remote_id 8b][channel 16b][command 16b]
```

**Channel field:** `0xFFFF ^ (1 << ((ch + 7) % 16))` or `0x0000` for broadcast

**Command field:** `(BASE[button] + remote_id - offset) & 0xFFFF`
- BASE: UP=0xf3e8, DOWN=0xbbb0, STOP=0xdbd0, TRAILER=0xdacf
- Offset: `2 + (1 << ((ch - 1) % 8))` with signed 8-bit wraparound

See [protocol_analysis.md](protocol_analysis.md) for full details.

## Files

- `protocol_analysis.md` - Complete protocol documentation
- `generate_command.py` - Encode/decode library
- `capture_rx.py` - LimeSDR capture script (SoapySDR)
- `*.cu8` - Raw IQ captures from various remotes/channels

## Remotes

| Location | ID | Captures |
|----------|-----|----------|
| Living room | 0x93 | CC, ch1-3 |
| Office | 0x7c | - |
| Spare room | 0x45 | ch2-6, ch9-11, ch16 |
