import os
import struct


def hex_dump(data):
    return " ".join(f"{b:02x}" for b in data).upper()


def brute_force_scan(flp_path):
    print(f"\n--- STARTE BRUTE-FORCE HEX-SCAN FÜR {os.path.basename(flp_path)} ---")

    with open(flp_path, 'rb') as f:
        data = f.read()

    targets = {
        "Int32 (165000)": struct.pack('<I', 165000),
        "Int32 (165)": struct.pack('<I', 165),
        "Float32 (165.0)": struct.pack('<f', 165.0),
        "Float64 (165.0)": struct.pack('<d', 165.0),
        "String ASCII ('165')": b"165",
        "String UTF-16 ('165')": b"1\x006\x005\x00"
    }

    found_anything = False
    for name, pattern in targets.items():
        offset = 0
        while True:
            offset = data.find(pattern, offset)
            if offset == -1:
                break
            found_anything = True

            # Wir holen uns die 5 Bytes VOR dem Muster.
            # In der FLP-Struktur steht direkt vor den Daten die Event-ID (1 Byte).
            start = max(0, offset - 5)
            end = min(len(data), offset + len(pattern) + 4)

            context_before = data[start:offset]
            context_after = data[offset + len(pattern):end]

            print(f"\n[BINGO!] Muster gefunden: {name}")
            print(f"Byte-Offset im File: {offset}")

            # Wenn wir ein 4-Byte Event gefunden haben, ist das allerletzte Byte VOR dem Muster unsere ID!
            if len(context_before) > 0:
                mutmassliche_id = context_before[-1]
                print(f"Mutmaßliche Event-ID (dezimal): {mutmassliche_id}")

            print(f"Hex-Dump (-5 Bytes ... Muster ... +4 Bytes):")
            print(f"--> [ {hex_dump(context_before)} ]  {hex_dump(pattern)}  [ {hex_dump(context_after)} ]")

            offset += 1

    if not found_anything:
        print("\nKein exaktes Muster gefunden. FL Studio speichert das Tempo verschlüsselt oder normalisiert.")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_165 = os.path.join(base_dir, "tempo_165.flp")

    brute_force_scan(file_165)