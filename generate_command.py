#!/usr/bin/env python3
"""
Blind Controller Protocol - Command Generator

Generates valid command payloads for motorized blind remotes.
"""

# Base commands (before remote ID and channel offset applied)
BASE_COMMANDS = {
    'UP': 0xf3e8,
    'DOWN': 0xbbb0,
    'STOP': 0xdbd0,
    'TRAILER': 0xdacf,
}

PROTOCOL_PREFIX = 0x5c5d92


def get_channel_offset(channel: int) -> int:
    """
    Calculate channel offset.

    Offset = 2 + 2^((channel-1) mod 8)
    For ch8/ch16, applies signed 8-bit wraparound (130 -> -126)
    """
    if channel == 0:  # Broadcast (CC)
        return 0

    exponent = (channel - 1) % 8
    offset = 2 + (2 ** exponent)

    # Signed 8-bit wraparound for offset >= 128
    if offset >= 128:
        offset -= 256

    return offset


def get_channel_field(channel: int) -> int:
    """
    Generate 16-bit channel field.

    Each channel clears one bit from 0xFFFF:

    Channel | Field  | Binary             | Bit Cleared
    --------|--------|--------------------|-----------
       CC   | 0x0000 | 00000000 00000000 | (broadcast)
        1   | 0xfeff | 11111110 11111111 | bit 8
        2   | 0xfdff | 11111101 11111111 | bit 9
        3   | 0xfbff | 11111011 11111111 | bit 10
        4   | 0xf7ff | 11110111 11111111 | bit 11
        5   | 0xefff | 11101111 11111111 | bit 12
        6   | 0xdfff | 11011111 11111111 | bit 13
        7   | 0xbfff | 10111111 11111111 | bit 14
        8   | 0x7fff | 01111111 11111111 | bit 15
        9   | 0xfffe | 11111111 11111110 | bit 0
       10   | 0xfffd | 11111111 11111101 | bit 1
       11   | 0xfffb | 11111111 11111011 | bit 2
       12   | 0xfff7 | 11111111 11110111 | bit 3
       13   | 0xffef | 11111111 11101111 | bit 4
       14   | 0xffdf | 11111111 11011111 | bit 5
       15   | 0xffbf | 11111111 10111111 | bit 6
       16   | 0xff7f | 11111111 01111111 | bit 7
    """
    if not 0 <= channel <= 16:
        raise ValueError(f"Channel must be 0-16, got {channel}")
    if channel == 0:
        return 0x0000
    return 0xFFFF ^ (1 << ((channel + 7) % 16))


def generate_command(remote_id: int, channel: int, button: str) -> int:
    """
    Generate command value.

    Command = BaseCommand + RemoteID - ChannelOffset
    """
    if button.upper() not in BASE_COMMANDS:
        raise ValueError(f"Button must be one of {list(BASE_COMMANDS.keys())}")

    base = BASE_COMMANDS[button.upper()]
    offset = get_channel_offset(channel)

    return (base + remote_id - offset) & 0xFFFF


def generate_payload(remote_id: int, channel: int, button: str) -> bytes:
    """
    Generate complete 64-bit payload.

    Format: [prefix 24b][remote_id 8b][channel 16b][command 16b]
            |-------- static --------|-------- calculated -------|
    """
    channel_field = get_channel_field(channel)
    command = generate_command(remote_id, channel, button)

    payload = (
        (PROTOCOL_PREFIX << 40) |
        (remote_id << 32) |
        (channel_field << 16) |
        command
    )

    return payload.to_bytes(8, 'big')


def payload_to_hex(payload: bytes) -> str:
    """Format payload as hex string."""
    return payload.hex()


def generate_transmission(remote_id: int, channel: int, button: str) -> dict:
    """
    Generate complete transmission data for a button press.

    UP/DOWN: returns action + trailer
    STOP: returns action only
    """
    action_payload = generate_payload(remote_id, channel, button)

    result = {
        'button': button.upper(),
        'remote_id': f"0x{remote_id:02x}",
        'channel': 'CC' if channel == 0 else channel,
        'action': payload_to_hex(action_payload),
    }

    if button.upper() in ('UP', 'DOWN'):
        trailer_payload = generate_payload(remote_id, channel, 'TRAILER')
        result['trailer'] = payload_to_hex(trailer_payload)

    return result


REMOTE_NAMES = {0x93: 'living_room', 0x7c: 'office', 0x45: 'spare_room'}


def decode_payload(v: int) -> str:
    """
    Decode a payload back to human-readable form.

    Handles both 64-bit payloads and 65-bit rtl_433 output (with trailing bit).
    """
    if v > 0xFFFFFFFFFFFFFFFF:
        v = v >> 4

    h = f'{v:016x}'
    remote_id = int(h[6:8], 16)
    channel_val = int(h[8:12], 16)
    command_val = int(h[12:], 16)

    # Decode channel
    ch = 0
    if channel_val != 0x0000:
        for c in range(1, 17):
            if 0xFFFF ^ (1 << ((c + 7) % 16)) == channel_val:
                ch = c
                break

    # Decode button
    offset = 0 if ch == 0 else 2 + (1 << ((ch - 1) % 8))
    if offset >= 128:
        offset -= 256  # Signed 8-bit wraparound
    button = '?'
    for name, base in BASE_COMMANDS.items():
        if (base + remote_id - offset) & 0xFFFF == command_val:
            button = name
            break

    remote_name = REMOTE_NAMES.get(remote_id, f'0x{remote_id:02x}')
    ch_str = 'CC' if ch == 0 else str(ch)

    return f'{remote_name} ch{ch_str} {button}'


if __name__ == '__main__':
    # Example usage
    print("=== Blind Controller Command Generator ===\n")

    # Test cases matching verified captures
    test_cases = [
        (0x93, 0, 'UP'),      # Living room, broadcast
        (0x7c, 0, 'DOWN'),    # Office, broadcast
        (0x45, 5, 'UP'),      # Spare room, channel 5
        (0x45, 16, 'UP'),     # Spare room, channel 16
    ]

    for remote_id, channel, button in test_cases:
        result = generate_transmission(remote_id, channel, button)
        ch_str = result['channel']
        print(f"Remote 0x{remote_id:02x}, Ch {ch_str}, {button}:")
        print(f"  Action:  {result['action']}")
        if 'trailer' in result:
            print(f"  Trailer: {result['trailer']}")
        print()
