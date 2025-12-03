#!/usr/bin/env python3
import numpy as np
import SoapySDR
from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32
import sys

if len(sys.argv) < 2:
    print("Usage: python3 capture_rx.py <output.cu8> [seconds]")
    print("Example: python3 capture_rx.py stop.cu8 10")
    sys.exit(1)

output_file = sys.argv[1]
duration = float(sys.argv[2]) if len(sys.argv) > 2 else 10

sample_rate = 2e6
center_freq = 433920000
rx_gain = 20

# Setup SDR
devices = SoapySDR.Device.enumerate({"driver": "lime"})
if not devices:
    raise RuntimeError("No LimeSDR found!")
print(f"Found: {devices[0]['label']}")
sdr = SoapySDR.Device(devices[0])

sdr.setSampleRate(SOAPY_SDR_RX, 0, sample_rate)
sdr.setFrequency(SOAPY_SDR_RX, 0, center_freq)
sdr.setAntenna(SOAPY_SDR_RX, 0, "LNAL")
sdr.setGain(SOAPY_SDR_RX, 0, rx_gain)

print(f"RX: {center_freq/1e6} MHz, {sample_rate/1e6} Msps, {duration}s")
print(f"Output: {output_file}")
print("Press button during capture...")

rx_stream = sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [0])
sdr.activateStream(rx_stream)

num_samples = int(duration * sample_rate)
chunk_size = 65536
all_samples = []

buff = np.zeros(chunk_size, dtype=np.complex64)
collected = 0

print("Recording...")
while collected < num_samples:
    to_read = min(chunk_size, num_samples - collected)
    sr = sdr.readStream(rx_stream, [buff], to_read)
    if sr.ret > 0:
        all_samples.append(buff[:sr.ret].copy())
        collected += sr.ret

sdr.deactivateStream(rx_stream)
sdr.closeStream(rx_stream)

# Convert to cu8 format (unsigned 8-bit I/Q)
samples = np.concatenate(all_samples)
i_samples = (np.real(samples) * 127 + 128).clip(0, 255).astype(np.uint8)
q_samples = (np.imag(samples) * 127 + 128).clip(0, 255).astype(np.uint8)
interleaved = np.empty(len(samples) * 2, dtype=np.uint8)
interleaved[0::2] = i_samples
interleaved[1::2] = q_samples
interleaved.tofile(output_file)
print(f"Saved {len(samples)} samples to {output_file}")
