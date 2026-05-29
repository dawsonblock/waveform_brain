"""
check_prbs_capture.py

This script checks a captured PRBS31 sequence against a known good pattern.
It can be used to validate the deterministic data path of the Waveform
Brain hardware. The capture should be exported from the Vivado ILA in
binary or CSV format and loaded into Python for comparison.
"""

def check_prbs_sequence(capture, trigger_word=0xACCE5515):
    """Validate that the captured PRBS sequence matches the expected pattern.

    :param capture: Iterable of 32‑bit words from the ILA capture.
    :param trigger_word: The trigger marker used to align the sequence.
    :return: True if the sequence matches, False otherwise.
    """
    # Find trigger position
    try:
        idx = capture.index(trigger_word)
    except ValueError:
        return False
    # Generate expected PRBS sequence starting after the trigger
    seq = []
    lfsr = capture[idx]
    for _ in range(len(capture) - idx):
        # LFSR tap: x^31 + x^28 + 1
        feedback = ((lfsr >> 30) ^ (lfsr >> 27)) & 1
        lfsr = ((lfsr << 1) | feedback) & 0x7FFFFFFF
        seq.append(lfsr)
    return capture[idx+1:] == seq[:-1]

if __name__ == "__main__":
    # Example usage: load capture from a text file and check
    import sys
    if len(sys.argv) < 2:
        print("Usage: python check_prbs_capture.py <capture_file.txt>")
        sys.exit(1)
    with open(sys.argv[1], 'r') as f:
        data = [int(line.strip(), 0) for line in f]
    ok = check_prbs_sequence(data)
    print("PRBS check:", "PASS" if ok else "FAIL")