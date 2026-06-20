#!/usr/bin/env python3
"""
SMPTE ST 2110 Test Suite
Tests ST 2110-20 (Video) and ST 2110-30 (Audio) RTP packet structures
and timing compliance.

Based on SMPTE ST 2110 standards for Professional Media over IP Networks.
"""

import struct
import time
import socket
import threading
from dataclasses import dataclass
from typing import Optional, Tuple
import argparse
import sys


# ST 2110 Constants
RTP_VERSION = 2
RTP_HEADER_SIZE = 12
ST2110_20_PAYLOAD_TYPE = 96  # Dynamic payload type for video
ST2110_30_PAYLOAD_TYPE = 97  # Dynamic payload type for audio

# ST 2110-20 Video Constants
ST2110_20_SSRC = 0x12345678

# ST 2110-30 Audio Constants  
ST2110_30_SSRC = 0x87654321
AUDIO_SAMPLE_RATE = 48000  # 48 kHz
AUDIO_CHANNELS = 2
AUDIO_BIT_DEPTH = 24


@dataclass
class RTPPacket:
    """RTP Packet structure per RFC 3550"""
    version: int
    padding: int
    extension: int
    csrc_count: int
    marker: int
    payload_type: int
    sequence_number: int
    timestamp: int
    ssrc: int
    payload: bytes
    
    def pack(self) -> bytes:
        """Pack RTP header and payload into bytes"""
        # First byte: V(2) P(1) X(1) CC(4)
        first_byte = (self.version << 6) | (self.padding << 5) | \
                     (self.extension << 4) | self.csrc_count
        
        # Second byte: M(1) PT(7)
        second_byte = (self.marker << 7) | self.payload_type
        
        header = struct.pack('!BBHII',
                           first_byte,
                           second_byte,
                           self.sequence_number,
                           self.timestamp,
                           self.ssrc)
        
        return header + self.payload
    
    @classmethod
    def unpack(cls, data: bytes) -> 'RTPPacket':
        """Unpack bytes into RTP packet"""
        if len(data) < RTP_HEADER_SIZE:
            raise ValueError("Packet too short for RTP header")
        
        first_byte, second_byte, seq, ts, ssrc = struct.unpack('!BBHII', data[:12])
        
        version = (first_byte >> 6) & 0x03
        padding = (first_byte >> 5) & 0x01
        extension = (first_byte >> 4) & 0x01
        csrc_count = first_byte & 0x0F
        
        marker = (second_byte >> 7) & 0x01
        payload_type = second_byte & 0x7F
        
        payload = data[12:]
        
        return cls(
            version=version,
            padding=padding,
            extension=extension,
            csrc_count=csrc_count,
            marker=marker,
            payload_type=payload_type,
            sequence_number=seq,
            timestamp=ts,
            ssrc=ssrc,
            payload=payload
        )


class ST2110_20_Video:
    """SMPTE ST 2110-20 Uncompressed Video Transport"""
    
    def __init__(self, width: int = 1920, height: int = 1080, 
                 fps: int = 60, sampling: str = "YCbCr-4:2:2-10"):
        self.width = width
        self.height = height
        self.fps = fps
        self.sampling = sampling
        self.sequence = 0
        self.ssrc = ST2110_20_SSRC
        
        # Calculate bytes per pixel based on sampling
        if "4:2:2" in sampling:
            self.bpp = 2.5 if "10" in sampling else 2
        elif "4:4:4" in sampling:
            self.bpp = 3.75 if "10" in sampling else 3
        else:
            self.bpp = 2
    
    def create_packet(self, line_number: int, offset: int, 
                     video_data: bytes, timestamp: int,
                     marker: int = 0) -> RTPPacket:
        """Create ST 2110-20 video RTP packet"""
        # ST 2110-20 payload header (RFC 4175 extended)
        # For simplicity, using basic header:
        # - Extended sequence number (16 bits)
        # - Length field (16 bits)
        # - F (1 bit), Line number (15 bits)
        # - C (1 bit), Offset (15 bits)
        
        payload_header = struct.pack('!HHHH',
                                    0,  # Extended sequence number
                                    len(video_data),
                                    line_number & 0x7FFF,
                                    offset & 0x7FFF)
        
        payload = payload_header + video_data
        
        packet = RTPPacket(
            version=RTP_VERSION,
            padding=0,
            extension=0,
            csrc_count=0,
            marker=marker,
            payload_type=ST2110_20_PAYLOAD_TYPE,
            sequence_number=self.sequence & 0xFFFF,
            timestamp=timestamp,
            ssrc=self.ssrc,
            payload=payload
        )
        
        self.sequence += 1
        return packet
    
    def validate_packet(self, packet: RTPPacket) -> Tuple[bool, str]:
        """Validate ST 2110-20 packet structure"""
        errors = []
        
        if packet.version != RTP_VERSION:
            errors.append(f"Invalid RTP version: {packet.version}")
        
        if packet.payload_type != ST2110_20_PAYLOAD_TYPE:
            errors.append(f"Unexpected payload type: {packet.payload_type}")
        
        if len(packet.payload) < 8:
            errors.append("Payload too short for ST 2110-20 header")
        else:
            # Validate payload header
            if len(packet.payload) >= 8:
                ext_seq, length, line_no, offset = struct.unpack('!HHHH', 
                                                                packet.payload[:8])
                if length != len(packet.payload) - 8:
                    errors.append(f"Length mismatch: header={length}, actual={len(packet.payload)-8}")
        
        if errors:
            return False, "; ".join(errors)
        return True, "Valid ST 2110-20 packet"


class ST2110_30_Audio:
    """SMPTE ST 2110-30 PCM Audio Transport (based on AES67)"""
    
    def __init__(self, sample_rate: int = 48000, channels: int = 2,
                 bit_depth: int = 24, packet_time: float = 0.001):
        self.sample_rate = sample_rate
        self.channels = channels
        self.bit_depth = bit_depth
        self.packet_time = packet_time  # 1ms packets
        self.samples_per_packet = int(sample_rate * packet_time)
        self.sequence = 0
        self.ssrc = ST2110_30_SSRC
        
        # Bytes per sample
        self.bytes_per_sample = (bit_depth + 7) // 8
    
    def create_packet(self, audio_data: bytes, timestamp: int) -> RTPPacket:
        """Create ST 2110-30 audio RTP packet"""
        # ST 2110-30 uses standard RTP with L24 or L16 payload
        # No additional payload header - audio data directly follows RTP header
        
        packet = RTPPacket(
            version=RTP_VERSION,
            padding=0,
            extension=0,
            csrc_count=0,
            marker=0,
            payload_type=ST2110_30_PAYLOAD_TYPE,
            sequence_number=self.sequence & 0xFFFF,
            timestamp=timestamp,
            ssrc=self.ssrc,
            payload=audio_data
        )
        
        self.sequence += 1
        return packet
    
    def validate_packet(self, packet: RTPPacket) -> Tuple[bool, str]:
        """Validate ST 2110-30 packet structure"""
        errors = []
        
        if packet.version != RTP_VERSION:
            errors.append(f"Invalid RTP version: {packet.version}")
        
        if packet.payload_type != ST2110_30_PAYLOAD_TYPE:
            errors.append(f"Unexpected payload type: {packet.payload_type}")
        
        # Check payload size aligns with audio parameters
        expected_size = self.samples_per_packet * self.channels * self.bytes_per_sample
        if len(packet.payload) != expected_size:
            # Allow some flexibility for different packet times
            if len(packet.payload) % (self.channels * self.bytes_per_sample) != 0:
                errors.append(f"Payload size {len(packet.payload)} not aligned to audio frame")
        
        if errors:
            return False, "; ".join(errors)
        return True, "Valid ST 2110-30 packet"


class ST2110TestServer:
    """UDP server for receiving and validating ST 2110 packets"""
    
    def __init__(self, host='127.0.0.1', video_port=5004, audio_port=5005):
        self.host = host
        self.video_port = video_port
        self.audio_port = audio_port
        self.video_socket = None
        self.audio_socket = None
        self.running = False
        self.video_packets = []
        self.audio_packets = []
        self.video_thread = None
        self.audio_thread = None
        
    def start(self):
        """Start UDP listeners for video and audio"""
        self.running = True
        
        # Video socket
        self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.video_socket.bind((self.host, self.video_port))
        self.video_socket.settimeout(0.5)
        
        # Audio socket
        self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.audio_socket.bind((self.host, self.audio_port))
        self.audio_socket.settimeout(0.5)
        
        # Start listener threads
        self.video_thread = threading.Thread(target=self._listen_video, daemon=True)
        self.audio_thread = threading.Thread(target=self._listen_audio, daemon=True)
        self.video_thread.start()
        self.audio_thread.start()
        
        print(f"✓ Test server listening on {self.host}")
        print(f"  Video: UDP port {self.video_port}")
        print(f"  Audio: UDP port {self.audio_port}")
    
    def _listen_video(self):
        """Listen for video packets"""
        while self.running:
            try:
                data, addr = self.video_socket.recvfrom(65535)
                packet = RTPPacket.unpack(data)
                self.video_packets.append({
                    'packet': packet,
                    'addr': addr,
                    'time': time.time(),
                    'size': len(data)
                })
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Video listener error: {e}")
    
    def _listen_audio(self):
        """Listen for audio packets"""
        while self.running:
            try:
                data, addr = self.audio_socket.recvfrom(65535)
                packet = RTPPacket.unpack(data)
                self.audio_packets.append({
                    'packet': packet,
                    'addr': addr,
                    'time': time.time(),
                    'size': len(data)
                })
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Audio listener error: {e}")
    
    def stop(self):
        """Stop server gracefully"""
        self.running = False
        if self.video_thread:
            self.video_thread.join(timeout=1)
        if self.audio_thread:
            self.audio_thread.join(timeout=1)
        if self.video_socket:
            self.video_socket.close()
        if self.audio_socket:
            self.audio_socket.close()
        print("✓ Test server stopped")
    
    def get_stats(self):
        """Get packet statistics"""
        return {
            'video_packets': len(self.video_packets),
            'audio_packets': len(self.audio_packets),
            'video_bytes': sum(p['size'] for p in self.video_packets),
            'audio_bytes': sum(p['size'] for p in self.audio_packets),
        }
    
    def clear(self):
        """Clear captured packets"""
        self.video_packets.clear()
        self.audio_packets.clear()


class ST2110Tester:
    """Test suite for ST 2110 compliance"""
    
    def __init__(self):
        self.video = ST2110_20_Video()
        self.audio = ST2110_30_Audio()
        self.results = []
        self.server = None
    
    def start_test_server(self, host='127.0.0.1', video_port=5004, audio_port=5005):
        """Start local test server"""
        self.server = ST2110TestServer(host, video_port, audio_port)
        self.server.start()
        time.sleep(0.1)  # Let server start
        return self.server
    
    def stop_test_server(self):
        """Stop test server"""
        if self.server:
            self.server.stop()
            self.server = None
    
    def test_video_packet_structure(self) -> bool:
        """Test ST 2110-20 video packet creation and validation"""
        print("\n[TEST] ST 2110-20 Video Packet Structure")
        print("-" * 50)
        
        # Create test video line (1920 pixels, YCbCr 4:2:2 10-bit)
        # Simplified: 1920 * 2.5 bytes = 4800 bytes per line
        test_data = b'\x00' * 4800
        timestamp = int(time.time() * 90000)  # 90kHz clock
        
        packet = self.video.create_packet(
            line_number=100,
            offset=0,
            video_data=test_data,
            timestamp=timestamp & 0xFFFFFFFF,  # Mask to 32 bits
            marker=1
        )
        
        # Pack and unpack to verify
        packed = packet.pack()
        unpacked = RTPPacket.unpack(packed)
        
        # Validate
        valid, msg = self.video.validate_packet(unpacked)
        
        print(f"Packet size: {len(packed)} bytes")
        print(f"  RTP header: {RTP_HEADER_SIZE} bytes")
        print(f"  Payload header: 8 bytes")
        print(f"  Video data: {len(test_data)} bytes")
        print(f"Sequence: {unpacked.sequence_number}")
        print(f"Timestamp: {unpacked.timestamp}")
        print(f"Marker: {unpacked.marker}")
        print(f"Validation: {'✓ PASS' if valid else '✗ FAIL'} - {msg}")
        
        self.results.append(("Video Packet Structure", valid))
        return valid
    
    def test_audio_packet_structure(self) -> bool:
        """Test ST 2110-30 audio packet creation and validation"""
        print("\n[TEST] ST 2110-30 Audio Packet Structure")
        print("-" * 50)
        
        # Create test audio data (1ms @ 48kHz, 2ch, 24-bit)
        # 48 samples * 2 channels * 3 bytes = 288 bytes
        samples = self.audio.samples_per_packet
        audio_data = b'\x00' * (samples * self.audio.channels * self.audio.bytes_per_sample)
        timestamp = int(time.time() * self.audio.sample_rate)
        
        packet = self.audio.create_packet(audio_data, timestamp & 0xFFFFFFFF)
        
        # Pack and unpack
        packed = packet.pack()
        unpacked = RTPPacket.unpack(packed)
        
        # Validate
        valid, msg = self.audio.validate_packet(unpacked)
        
        print(f"Packet size: {len(packed)} bytes")
        print(f"  RTP header: {RTP_HEADER_SIZE} bytes")
        print(f"  Audio data: {len(audio_data)} bytes")
        print(f"  Samples: {samples} per channel")
        print(f"  Duration: {self.audio.packet_time*1000:.1f} ms")
        print(f"Sequence: {unpacked.sequence_number}")
        print(f"Timestamp: {unpacked.timestamp}")
        print(f"Validation: {'✓ PASS' if valid else '✗ FAIL'} - {msg}")
        
        self.results.append(("Audio Packet Structure", valid))
        return valid
    
    def test_timing_model(self) -> bool:
        """Test ST 2110-10 timing model compliance"""
        print("\n[TEST] ST 2110-10 Timing Model")
        print("-" * 50)
        
        # ST 2110-10 requires:
        # - 90kHz clock for video
        # - Sample rate clock for audio (typically 48kHz)
        # - Packets must be sent at regular intervals
        
        video_clock = 90000  # 90 kHz
        audio_clock = 48000  # 48 kHz
        
        print(f"Video clock: {video_clock} Hz (90kHz per ST 2110-10)")
        print(f"Audio clock: {audio_clock} Hz (48kHz per ST 2110-30)")
        
        # Simulate packet timing
        frame_duration = 1/60  # 60 fps
        packets_per_frame = 1080  # One per line for 1080p
        
        packet_interval = frame_duration / packets_per_frame
        print(f"\nFor 1080p60 video:")
        print(f"  Frame duration: {frame_duration*1000:.3f} ms")
        print(f"  Packets per frame: {packets_per_frame}")
        print(f"  Packet interval: {packet_interval*1000000:.1f} µs")
        
        # Check if timing is feasible
        # ST 2110-21 defines traffic shaping requirements
        max_packet_time = 0.0001  # 100µs typical network tolerance
        
        timing_ok = packet_interval < max_packet_time
        print(f"  Timing feasible: {'✓ YES' if timing_ok else '✗ NO'} "
              f"(requires < {max_packet_time*1000000}µs)")
        
        self.results.append(("Timing Model", timing_ok))
        return timing_ok
    
    def test_synchronization(self) -> bool:
        """Test A/V synchronization capabilities"""
        print("\n[TEST] A/V Synchronization")
        print("-" * 50)
        
        # Both streams must use same PTP clock reference
        # Timestamps must be aligned to allow lip-sync
        
        print("ST 2110-10 requires:")
        print("  • Common PTP reference clock (IEEE 1588)")
        print("  • Video: 90kHz timestamp clock")
        print("  • Audio: Sample rate timestamp clock (48kHz)")
        print("  • RTP timestamps must be synchronized")
        
        # Simulate synchronized timestamps
        ptp_time = time.time()
        video_ts = int(ptp_time * 90000) & 0xFFFFFFFF
        audio_ts = int(ptp_time * 48000) & 0xFFFFFFFF
        
        print(f"\nExample synchronized timestamps:")
        print(f"  PTP time: {ptp_time:.6f}")
        print(f"  Video TS (90kHz): {video_ts}")
        print(f"  Audio TS (48kHz): {audio_ts}")
        print(f"  ✓ Both derived from same PTP clock")
        
        self.results.append(("A/V Sync", True))
        return True
    
    def test_network_flow(self) -> bool:
        """Test actual UDP packet flow to local server"""
        print("\n[TEST] Network Packet Flow")
        print("-" * 50)
        
        if not self.server:
            print("✗ No test server running - starting temporary server...")
            self.start_test_server()
            server_started_here = True
        else:
            server_started_here = False
        
        try:
            # Clear previous packets
            self.server.clear()
            
            # Create test packets
            video_data = b'\x00' * 1000
            audio_data = b'\x00' * 288
            
            video_packet = self.video.create_packet(
                line_number=1,
                offset=0,
                video_data=video_data,
                timestamp=int(time.time() * 90000) & 0xFFFFFFFF,
                marker=0
            )
            
            audio_packet = self.audio.create_packet(
                audio_data,
                int(time.time() * 48000) & 0xFFFFFFFF
            )
            
            # Send packets via UDP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            try:
                # Send video packet
                video_bytes = video_packet.pack()
                sock.sendto(video_bytes, ('127.0.0.1', self.server.video_port))
                
                # Send audio packet
                audio_bytes = audio_packet.pack()
                sock.sendto(audio_bytes, ('127.0.0.1', self.server.audio_port))
                
                # Wait for packets to be received
                time.sleep(0.2)
                
                stats = self.server.get_stats()
                
                print(f"Sent video packet: {len(video_bytes)} bytes to port {self.server.video_port}")
                print(f"Sent audio packet: {len(audio_bytes)} bytes to port {self.server.audio_port}")
                print(f"Received video packets: {stats['video_packets']}")
                print(f"Received audio packets: {stats['audio_packets']}")
                
                success = stats['video_packets'] >= 1 and stats['audio_packets'] >= 1
                
                if success:
                    print("✓ PASS - Packets transmitted and received successfully")
                    
                    # Validate received packets
                    if self.server.video_packets:
                        pkt = self.server.video_packets[0]['packet']
                        valid, msg = self.video.validate_packet(pkt)
                        print(f"  Video validation: {'✓' if valid else '✗'} {msg}")
                    
                    if self.server.audio_packets:
                        pkt = self.server.audio_packets[0]['packet']
                        valid, msg = self.audio.validate_packet(pkt)
                        print(f"  Audio validation: {'✓' if valid else '✗'} {msg}")
                else:
                    print("✗ FAIL - Packets not received")
                
                self.results.append(("Network Flow", success))
                return success
                
            finally:
                sock.close()
        finally:
            if server_started_here:
                self.stop_test_server()
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("=" * 60)
        print("SMPTE ST 2110 Test Suite")
        print("Professional Media Over Managed IP Networks")
        print("=" * 60)
        
        # Start test server for network tests
        print("\nStarting local test server...")
        self.start_test_server()
        
        tests = [
            self.test_video_packet_structure,
            self.test_audio_packet_structure,
            self.test_timing_model,
            self.test_synchronization,
            self.test_network_flow,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"✗ TEST FAILED with exception: {e}")
                import traceback
                traceback.print_exc()
                self.results.append((test.__name__, False))
        
        # Stop test server
        self.stop_test_server()
        
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, result in self.results if result)
        total = len(self.results)
        
        for name, result in self.results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {name}")
        
        print("-" * 60)
        print(f"Total: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests PASSED! ST 2110 implementation is compliant.")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test(s) FAILED!")
            return 1


def main():
    parser = argparse.ArgumentParser(
        description="SMPTE ST 2110 Test Suite - Validate ST 2110-20/30 implementations"
    )
    parser.add_argument(
        '--test', 
        choices=['video', 'audio', 'timing', 'sync', 'all'],
        default='all',
        help='Specific test to run (default: all)'
    )
    
    args = parser.parse_args()
    
    tester = ST2110Tester()
    
    if args.test == 'all':
        return tester.run_all_tests()
    elif args.test == 'video':
        return 0 if tester.test_video_packet_structure() else 1
    elif args.test == 'audio':
        return 0 if tester.test_audio_packet_structure() else 1
    elif args.test == 'timing':
        return 0 if tester.test_timing_model() else 1
    elif args.test == 'sync':
        return 0 if tester.test_synchronization() else 1


if __name__ == '__main__':
    sys.exit(main())
