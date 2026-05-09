import os
import wave
import struct
import math
import random


def generate_tone(filename, frequencies, duration_ms, volume=0.5, wave_type="sine", sample_rate=44100, envelope="fade"):
    """Generiert einen statischen Ton oder Akkord (für Klicks, Ticks, etc.)"""
    num_samples = int(sample_rate * (duration_ms / 1000.0))

    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for i in range(num_samples):
            t = float(i) / sample_rate
            sample = 0

            if wave_type == "noise":
                sample = random.uniform(-1.0, 1.0)
            else:
                for freq in frequencies:
                    if wave_type == "sine":
                        sample += math.sin(2.0 * math.pi * freq * t)
                    elif wave_type == "square":
                        sample += 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
                if frequencies:
                    sample = sample / len(frequencies)

            fade = 1.0
            if envelope == "fade":
                if i > num_samples - 500:
                    fade = (num_samples - i) / 500.0
            elif envelope == "click":
                fade = math.exp(-i / (sample_rate * 0.005))
            elif envelope == "beep_beep":
                mid = num_samples // 2
                if (i > mid - 1000 and i < mid + 1000):
                    fade = 0.0
                else:
                    if i > num_samples - 500: fade = (num_samples - i) / 500.0
                    if i < 500: fade = i / 500.0

            audio = int(sample * 32767 * volume * fade)
            audio = max(-32768, min(32767, audio))
            wav_file.writeframesraw(struct.pack('<h', audio))


def generate_plucky_chime(filename, notes, duration_per_note_ms=120, decay_factor=0.04, volume=0.5, sample_rate=44100):
    """
    Generiert extrem knackige, abgehackte Pluck-Sounds (wie ein Synth-Pluck oder Pizzicato).
    Komplett ohne Nachhall und mit schnellen Obertönen für den Attack.
    """
    # Keine extra Tail-Zeit mehr! Die Note endet präzise.
    total_samples = int(sample_rate * ((len(notes) * duration_per_note_ms) / 1000.0))
    audio_buffer = [0.0] * total_samples

    for note_idx, freq in enumerate(notes):
        start_sample = int(sample_rate * (note_idx * duration_per_note_ms / 1000.0))
        note_samples = int(sample_rate * (duration_per_note_ms / 1000.0))

        for i in range(note_samples):
            t = float(i) / sample_rate

            # --- DER PLUCK-SYNTH ---
            # 1. Grundton
            sample = math.sin(2.0 * math.pi * freq * t)

            # 2. Die Attack-Obertöne (Diese klingen extrem schnell ab und erzeugen das "Zupfen")
            sample += 0.8 * math.sin(2.0 * math.pi * (freq * 2.0) * t) * math.exp(-i / (sample_rate * 0.015))
            sample += 0.4 * math.sin(2.0 * math.pi * (freq * 3.0) * t) * math.exp(-i / (sample_rate * 0.005))

            # --- DIE HÜLLKURVE ---
            # Steiler exponentieller Abfall für den trockenen Klang
            env = math.exp(-i / (sample_rate * decay_factor))

            # Anti-Knackser: Die allerletzten Samples der Note weich auf 0 faden
            if i > note_samples - 100:
                env *= (note_samples - i) / 100.0

            if start_sample + i < total_samples:
                audio_buffer[start_sample + i] += (sample / 1.5) * env

    # Audio schreiben
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for sample in audio_buffer:
            audio = int(max(-32768, min(32767, sample * 32767 * volume)))
            wav_file.writeframesraw(struct.pack('<h', audio))


def create_all_sounds():
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sounds")
    os.makedirs(base_dir, exist_ok=True)

    print("Generiere ultra-knackige Pluck-Sounds in:", base_dir)

    # 1. Realistischer mechanischer Button Klick
    generate_tone(os.path.join(base_dir, "click.wav"), [], 25, wave_type="noise", envelope="click", volume=0.35)

    # 2. Lobby Sounds (Plucky, trocken, Ba-Dum / Dum-Ba)
    # Join: "Ba-Dum" (A4 -> D5 aufsteigend)
    generate_plucky_chime(os.path.join(base_dir, "join.wav"), [440.0, 587.33], duration_per_note_ms=120,
                          decay_factor=0.04, volume=0.55)
    # Leave: "Dum-Ba" (D5 -> A4 absteigend)
    generate_plucky_chime(os.path.join(base_dir, "leave.wav"), [587.33, 440.0], duration_per_note_ms=120,
                          decay_factor=0.04, volume=0.55)

    # 3. Match Sounds
    generate_tone(os.path.join(base_dir, "start.wav"), [523.25, 659.25, 783.99, 1046.50], 800)
    generate_tone(os.path.join(base_dir, "turn_end.wav"), [587.33, 880.00], 600)

    # 4. Eskalierende Timer-Ticks
    generate_tone(os.path.join(base_dir, "tick_1.wav"), [800], 25, wave_type="square", volume=0.15)
    generate_tone(os.path.join(base_dir, "tick_2.wav"), [1000], 25, wave_type="square", volume=0.15)
    generate_tone(os.path.join(base_dir, "tick_3.wav"), [1300], 25, wave_type="square", volume=0.15)

    # 5. Eliminiert & Finish
    generate_tone(os.path.join(base_dir, "eliminated.wav"), [350], 450, wave_type="square", envelope="beep_beep",
                  volume=0.15)
    generate_tone(os.path.join(base_dir, "finish.wav"), [440, 554, 659, 880], 1200)

    print("Alle Sounds erfolgreich generiert!")


if __name__ == "__main__":
    create_all_sounds()