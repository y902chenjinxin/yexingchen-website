#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate garden-style background music with natural flow - v1.1"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from scipy.io import wavfile


def generate_garden_music():
    """Generate 60-second garden-style music with natural rise and fall"""

    sample_rate = 44100
    duration = 60

    frequencies = {
        'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23,
        'G4': 392.00, 'A4': 440.00, 'B4': 493.88,
        'C5': 523.25, 'D5': 587.33, 'E5': 659.26, 'F5': 698.46,
        'G5': 783.99, 'A5': 880.00,
    }

    fade_samples = int(sample_rate * 0.5)
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    audio = np.zeros(len(t), dtype=np.float32)

    def create_envelope(samples, attack=0.05, decay=0.15, sustain=0.7, release=0.1):
        env = np.ones(samples, dtype=np.float32)
        attack_samples = min(int(samples * attack), samples // 4)
        decay_samples = min(int(samples * decay), samples // 4)
        release_samples = min(int(samples * release), samples // 4)

        if attack_samples > 0:
            env[:attack_samples] = np.linspace(0, 1, attack_samples)

        decay_end = attack_samples + decay_samples
        if decay_samples > 0 and decay_end < samples:
            env[attack_samples:decay_end] = np.linspace(1, sustain, decay_samples)

        sustain_end = samples - release_samples
        if sustain_end > decay_end and sustain_end < samples:
            env[decay_end:sustain_end] = sustain

        if release_samples > 0 and sustain_end < samples:
            env[sustain_end:] = np.linspace(sustain, 0, release_samples)

        return env

    def add_tone(freq, start_time, note_duration, volume=0.15, wave_type='bright_square'):
        start = int(start_time * sample_rate)
        samples = int(note_duration * sample_rate)
        if start >= len(audio):
            return
        end = min(start + samples, len(audio))
        actual_samples = end - start
        note_t = np.linspace(0, note_duration, actual_samples, dtype=np.float32)
        envelope = create_envelope(actual_samples, attack=0.02, decay=0.08, sustain=0.85, release=0.08)

        if wave_type == 'bright_square':
            raw = np.sign(np.sin(2 * np.pi * freq * note_t))
            wave = raw * (1 - np.exp(-note_t * 40))
        elif wave_type == 'triangle':
            wave = np.abs(2 * (note_t * freq % 1)) - 1
        elif wave_type == 'bell':
            wave = np.sin(2 * np.pi * freq * note_t)
            wave += np.sin(2 * np.pi * freq * 2 * note_t) * 0.4
            wave += np.sin(2 * np.pi * freq * 3 * note_t) * 0.2
        elif wave_type == 'soft_triangle':
            wave = np.sin(2 * np.pi * freq * note_t)
            wave += np.sin(2 * np.pi * freq * 0.5 * note_t) * 0.3
        else:
            wave = np.sin(2 * np.pi * freq * note_t)

        wave = wave * envelope * volume
        audio[start:end] += wave

    beat = 0.5  # tempo

    # === 0-8s: Soft opening, like waking up ===
    add_tone(261.63, 0, 4, 0.06, 'soft_triangle')  # C3 pad
    add_tone(329.63, 0, 4, 0.04, 'soft_triangle')  # E3 pad

    add_tone(523.25, 0.5, 0.4, 0.07, 'bright_square')   # C5
    add_tone(659.26, 1.0, 0.4, 0.06, 'bright_square')   # E5
    add_tone(523.25, 1.5, 0.4, 0.07, 'bright_square')   # C5
    add_tone(587.33, 2.0, 0.4, 0.06, 'bright_square')   # D5
    add_tone(523.25, 2.5, 0.4, 0.07, 'bright_square')   # C5
    add_tone(493.88, 3.0, 0.4, 0.06, 'bright_square')   # B4
    add_tone(440.00, 3.5, 0.4, 0.05, 'bright_square')   # A4

    add_tone(523.25, 4.0, 0.4, 0.08, 'bright_square')   # C5
    add_tone(659.26, 4.5, 0.4, 0.07, 'bright_square')   # E5
    add_tone(783.99, 5.0, 0.4, 0.08, 'bright_square')   # G5
    add_tone(659.26, 5.5, 0.4, 0.07, 'bright_square')   # E5
    add_tone(523.25, 6.0, 0.4, 0.08, 'bright_square')   # C5
    add_tone(440.00, 6.5, 0.4, 0.06, 'bright_square')   # A4
    add_tone(392.00, 7.0, 0.4, 0.05, 'bright_square')   # G4
    add_tone(329.63, 7.5, 0.4, 0.04, 'bright_square')   # E4

    # === 8-16s: Gentle growth ===
    add_tone(261.63, 8, 4, 0.05, 'soft_triangle')
    add_tone(329.63, 8, 4, 0.04, 'soft_triangle')

    add_tone(523.25, 8.5, 0.4, 0.08, 'bright_square')
    add_tone(587.33, 9.0, 0.4, 0.07, 'bright_square')
    add_tone(659.26, 9.5, 0.4, 0.09, 'bright_square')   # slightly louder
    add_tone(698.46, 10.0, 0.4, 0.10, 'bright_square')  # F5 - build up
    add_tone(783.99, 10.5, 0.4, 0.11, 'bright_square')  # G5
    add_tone(880.00, 11.0, 0.4, 0.12, 'bright_square')  # A5 - crest

    add_tone(783.99, 12.0, 1.5, 0.10, 'bell')   # bell accent

    add_tone(659.26, 12.5, 0.4, 0.09, 'bright_square')
    add_tone(587.33, 13.0, 0.4, 0.08, 'bright_square')
    add_tone(523.25, 13.5, 0.4, 0.07, 'bright_square')
    add_tone(493.88, 14.0, 0.4, 0.06, 'bright_square')
    add_tone(440.00, 14.5, 0.4, 0.05, 'bright_square')
    add_tone(392.00, 15.0, 0.4, 0.04, 'bright_square')
    add_tone(329.63, 15.5, 0.4, 0.04, 'bright_square')

    # === 16-24s: More energy, adding bass ===
    add_tone(196.00, 16, 2, 0.05, 'triangle')  # G3 bass
    add_tone(246.94, 16, 2, 0.04, 'triangle')  # B3 bass

    add_tone(523.25, 16.5, 0.3, 0.10, 'bright_square')
    add_tone(659.26, 17.0, 0.3, 0.09, 'bright_square')
    add_tone(783.99, 17.5, 0.3, 0.11, 'bright_square')
    add_tone(880.00, 18.0, 0.3, 0.12, 'bright_square')
    add_tone(783.99, 18.5, 0.3, 0.10, 'bright_square')
    add_tone(659.26, 19.0, 0.3, 0.09, 'bright_square')
    add_tone(523.25, 19.5, 0.3, 0.08, 'bright_square')
    add_tone(440.00, 20.0, 0.3, 0.07, 'bright_square')

    add_tone(523.25, 21.0, 0.3, 0.10, 'bright_square')
    add_tone(587.33, 21.5, 0.3, 0.09, 'bright_square')
    add_tone(659.26, 22.0, 0.3, 0.10, 'bright_square')
    add_tone(698.46, 22.5, 0.3, 0.11, 'bright_square')
    add_tone(783.99, 23.0, 0.5, 0.12, 'bright_square')  # build
    add_tone(880.00, 23.5, 0.5, 0.13, 'bright_square')  # climax

    add_tone(880.00, 24, 1.0, 0.08, 'bell')  # accent

    # === 24-32s: Peak and gentle release ===
    add_tone(523.25, 24.5, 0.3, 0.11, 'bright_square')
    add_tone(659.26, 25.0, 0.3, 0.10, 'bright_square')
    add_tone(783.99, 25.5, 0.3, 0.12, 'bright_square')
    add_tone(880.00, 26.0, 0.3, 0.13, 'bright_square')
    add_tone(987.77, 26.5, 0.3, 0.12, 'bright_square')  # B5
    add_tone(880.00, 27.0, 0.3, 0.11, 'bright_square')
    add_tone(783.99, 27.5, 0.3, 0.10, 'bright_square')
    add_tone(659.26, 28.0, 0.3, 0.09, 'bright_square')

    add_tone(587.33, 29.0, 0.3, 0.10, 'bright_square')
    add_tone(523.25, 29.5, 0.3, 0.09, 'bright_square')
    add_tone(440.00, 30.0, 0.3, 0.08, 'bright_square')
    add_tone(392.00, 30.5, 0.3, 0.07, 'bright_square')
    add_tone(329.63, 31.0, 0.5, 0.06, 'bright_square')
    add_tone(293.66, 31.5, 0.5, 0.05, 'bright_square')  # softer

    # === 32-40s: Second wave, different motif ===
    add_tone(261.63, 32, 2, 0.05, 'triangle')
    add_tone(329.63, 32, 2, 0.04, 'triangle')

    add_tone(440.00, 33.0, 0.3, 0.09, 'bright_square')
    add_tone(523.25, 33.5, 0.3, 0.10, 'bright_square')
    add_tone(587.33, 34.0, 0.3, 0.11, 'bright_square')
    add_tone(659.26, 34.5, 0.3, 0.12, 'bright_square')
    add_tone(587.33, 35.0, 0.3, 0.10, 'bright_square')
    add_tone(523.25, 35.5, 0.3, 0.09, 'bright_square')
    add_tone(440.00, 36.0, 0.3, 0.08, 'bright_square')
    add_tone(392.00, 36.5, 0.3, 0.07, 'bright_square')

    add_tone(523.25, 37.5, 0.3, 0.10, 'bright_square')
    add_tone(587.33, 38.0, 0.3, 0.11, 'bright_square')
    add_tone(659.26, 38.5, 0.3, 0.12, 'bright_square')
    add_tone(698.46, 39.0, 0.5, 0.13, 'bright_square')  # rising
    add_tone(783.99, 39.5, 0.5, 0.14, 'bright_square')  # still building

    add_tone(783.99, 40, 1.0, 0.08, 'bell')

    # === 40-48s: Another peak ===
    add_tone(523.25, 40.5, 0.3, 0.12, 'bright_square')
    add_tone(659.26, 41.0, 0.3, 0.11, 'bright_square')
    add_tone(783.99, 41.5, 0.3, 0.13, 'bright_square')
    add_tone(880.00, 42.0, 0.3, 0.14, 'bright_square')
    add_tone(987.77, 42.5, 0.3, 0.13, 'bright_square')
    add_tone(880.00, 43.0, 0.3, 0.12, 'bright_square')
    add_tone(783.99, 43.5, 0.3, 0.11, 'bright_square')
    add_tone(659.26, 44.0, 0.3, 0.10, 'bright_square')

    add_tone(523.25, 45.0, 0.3, 0.11, 'bright_square')
    add_tone(440.00, 45.5, 0.3, 0.10, 'bright_square')
    add_tone(392.00, 46.0, 0.3, 0.09, 'bright_square')
    add_tone(329.63, 46.5, 0.3, 0.08, 'bright_square')
    add_tone(261.63, 47.0, 0.5, 0.07, 'bright_square')
    add_tone(293.66, 47.5, 0.5, 0.06, 'bright_square')

    # === 48-60s: Gentle winding down ===
    add_tone(329.63, 48, 3, 0.04, 'soft_triangle')
    add_tone(261.63, 48, 3, 0.05, 'soft_triangle')

    add_tone(440.00, 49.0, 0.4, 0.08, 'bright_square')
    add_tone(523.25, 49.5, 0.4, 0.07, 'bright_square')
    add_tone(440.00, 50.0, 0.4, 0.06, 'bright_square')
    add_tone(392.00, 50.5, 0.4, 0.05, 'bright_square')

    add_tone(523.25, 51.5, 0.4, 0.07, 'bright_square')
    add_tone(440.00, 52.0, 0.4, 0.06, 'bright_square')
    add_tone(392.00, 52.5, 0.4, 0.05, 'bright_square')
    add_tone(329.63, 53.0, 0.4, 0.04, 'bright_square')

    add_tone(440.00, 54.5, 0.4, 0.05, 'bright_square')
    add_tone(392.00, 55.0, 0.4, 0.04, 'bright_square')
    add_tone(329.63, 55.5, 0.4, 0.03, 'bright_square')
    add_tone(261.63, 56.0, 0.4, 0.03, 'bright_square')

    # Final soft ending
    add_tone(523.25, 58, 2, 0.03, 'bright_square')
    add_tone(440.00, 58, 2, 0.025, 'bright_square')
    add_tone(329.63, 58, 2, 0.03, 'soft_triangle')

    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.85

    audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)

    audio_int = (audio * 32767).astype(np.int16)
    return sample_rate, audio_int


if __name__ == "__main__":
    print("[INFO] Generating garden-style background music...")

    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "bgm")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, "garden_music.wav")

    sample_rate, audio = generate_garden_music()
    wavfile.write(output_path, sample_rate, audio)

    print(f"[OK] Music generated: {output_path}")
    print(f"     Duration: 60 seconds")
    print(f"     Style: Natural flow with rises and falls")