# SMPTE ST 2110 Test Suite

Python-based test suite for SMPTE ST 2110 Professional Media over Managed IP Networks.

## Overview

This tool validates implementations of:
- **ST 2110-10**: System Timing and Definitions
- **ST 2110-20**: Uncompressed Active Video Transport
- **ST 2110-30**: PCM Digital Audio Transport
- **ST 2110-21**: Traffic Shaping (timing validation)

Based on the SMPTE standards suite for professional broadcast media over IP networks.

## Background

SMPTE ST 2110 separates video, audio, and ancillary data into independent RTP streams, each synchronized to a common PTP (Precision Time Protocol) reference clock. This enables:
- Flexible routing in IP networks
- Independent processing of essence streams
- Precise A/V synchronization
- Scalable broadcast infrastructure

## Features

### Packet Structure Validation
- ✓ RTP header compliance (RFC 3550)
- ✓ ST 2110-20 video payload headers
- ✓ ST 2110-30 audio payload validation
- ✓ Sequence number and timestamp verification

### Timing Model Testing
- ✓ 90kHz clock for video (ST 2110-10)
- ✓ Sample-rate clock for audio (typically 48kHz)
- ✓ Packet interval calculations
- ✓ ST 2110-21 traffic shaping compliance

### Synchronization Testing
- ✓ Common PTP reference clock validation
- ✓ A/V lip-sync capabilities
- ✓ Timestamp alignment verification

## Installation

```bash
git clone https://github.com/necat101/smpte2110-tester.git
cd smpte2110-tester
chmod +x smpte2110_test.py
```

No external dependencies required - uses only Python standard library.

## Usage

### Run All Tests
```bash
python3 smpte2110_test.py
```

### Run Specific Tests
```bash
python3 smpte2110_test.py --test video    # ST 2110-20 video packets
python3 smpte2110_test.py --test audio    # ST 2110-30 audio packets
python3 smpte2110_test.py --test timing   # ST 2110-10/21 timing
python3 smpte2110_test.py --test sync     # A/V synchronization
```

### Example Output
```
============================================================
SMPTE ST 2110 Test Suite
Professional Media Over Managed IP Networks
============================================================

[TEST] ST 2110-20 Video Packet Structure
--------------------------------------------------
Packet size: 4820 bytes
  RTP header: 12 bytes
  Payload header: 8 bytes
  Video data: 4800 bytes
Sequence: 0
Timestamp: 583820004
Marker: 1
Validation: ✓ PASS - Valid ST 2110-20 packet

[TEST] ST 2110-30 Audio Packet Structure
--------------------------------------------------
Packet size: 300 bytes
  RTP header: 12 bytes
  Audio data: 288 bytes
  Samples: 48 per channel
  Duration: 1.0 ms
Validation: ✓ PASS - Valid ST 2110-30 packet

============================================================
TEST SUMMARY
============================================================
✓ PASS: Video Packet Structure
✓ PASS: Audio Packet Structure
✓ PASS: Timing Model
✓ PASS: A/V Sync
------------------------------------------------------------
Total: 4/4 tests passed

🎉 All tests PASSED! ST 2110 implementation is compliant.
```

## Technical Details

### ST 2110-20 Video Packets
- **Payload Type**: 96 (dynamic)
- **Clock Rate**: 90,000 Hz
- **Payload Header**: 8 bytes
  - Extended sequence number (16 bits)
  - Length (16 bits)
  - Line number + field bit (16 bits)
  - Offset (16 bits)
- **Typical Size**: ~4800 bytes per line (1080p, YCbCr 4:2:2 10-bit)

### ST 2110-30 Audio Packets
- **Payload Type**: 97 (dynamic)
- **Clock Rate**: Sample rate (typically 48,000 Hz)
- **Format**: L16 (16-bit) or L24 (24-bit) PCM
- **Packet Time**: Typically 1ms (48 samples @ 48kHz)
- **Typical Size**: 288 bytes (48 samples, 2ch, 24-bit)

### Timing Requirements (ST 2110-21)
- **Narrow Senders**: Packets evenly spaced
- **Wide Senders**: Bursty transmission allowed
- **Packet interval**: ~15.4 µs for 1080p60 (1080 lines/frame)
- **Network tolerance**: Typically <100 µs jitter

## Use Cases

1. **Validate ST 2110 Implementations**
   - Test encoder/decoder compliance
   - Verify packet structure
   - Check timing adherence

2. **Network Planning**
   - Calculate bandwidth requirements
   - Validate timing budgets
   - Plan for ST 2110-21 traffic classes

3. **Troubleshooting**
   - Diagnose packet structure issues
   - Verify timestamp alignment
   - Check A/V sync problems

4. **Education**
   - Learn ST 2110 packet formats
   - Understand timing model
   - Explore RTP/RTCP basics

## SMPTE Standards Access

As of 2024, SMPTE has made their standards **freely accessible** to promote open development and interoperability. This is a significant shift from the traditional paywall model.

Key standards in the ST 2110 suite:
- **ST 2110-10**: System architecture and timing
- **ST 2110-20**: Uncompressed video
- **ST 2110-21**: Traffic shaping
- **ST 2110-22**: Compressed video
- **ST 2110-30**: PCM audio
- **ST 2110-31**: AES3 audio
- **ST 2110-40**: Ancillary data

Access the standards at: https://www.smpte.org/standards/st2110

## References

- [SMPTE ST 2110 Suite](https://www.smpte.org/standards/st2110)
- [RFC 3550 - RTP](https://tools.ietf.org/html/rfc3550)
- [RFC 4175 - Uncompressed Video](https://tools.ietf.org/html/rfc4175)
- [AES67 - Audio over IP](https://www.aes.org/standards/blog/2018/4/aes67-2018/)
- [IEEE 1588 PTP](https://ieeexplore.ieee.org/document/4579760)

## Hacker News Discussion

This tool was created following the HN discussion on SMPTE making standards freely accessible:
https://news.ycombinator.com/item?id=48610827

Key sentiments from the community:
- ✅ Free access enables better implementations
- ✅ Prevents reverse-engineering from samples
- ✅ Aligns with IETF's successful open model
- ✅ Critical for data encodings and interoperability
- ⚠️ Standards bodies need sustainable funding models
- 💡 Balance between openness and organizational viability

## License

MIT License - Free to use for testing ST 2110 implementations.

## Contributing

Contributions welcome! Areas for expansion:
- [ ] ST 2110-22 (compressed video) support
- [ ] ST 2110-40 (ancillary data) validation
- [ ] PTP clock simulation
- [ ] Network impairment testing
- [ ] NMOS IS-04/05 integration
- [ ] PCAP file analysis

## Author

Created as a practical implementation reference for SMPTE ST 2110 standards.
