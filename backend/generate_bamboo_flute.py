#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate bamboo flute style background music - 兰亭序风格"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from scipy.io import wavfile


def generate_bamboo_flute_music():
    """Generate 60-second bamboo flute style music - elegant and flowing like 兰亭序"""

    sample_rate = 44100
    duration = 60

    # 五声音阶 (Pentatonic scale in C)
    notes = {
        'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'G4': 392.00, 'A4': 440.00,
        'C5': 523.25, 'D5': 587.33, 'E5': 659.26, 'G5': 783.99, 'A5': 880.00,
        'C6': 1046.50, 'D6': 1174.66, 'E6': 1318.51,
        'C3': 130.81, 'D3': 146.83, 'E3': 164.81, 'G3': 196.00, 'A3': 220.00,
    }

    fade_samples = int(sample_rate * 0.8)
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    audio = np.zeros(len(t), dtype=np.float32)

    def create_flute_envelope(samples, attack=0.1, decay=0.15, sustain=0.7, release=0.15):
        env = np.ones(samples, dtype=np.float32)
        attack_samples = int(samples * attack)
        decay_samples = int(samples * decay)
        release_samples = int(samples * release)

        if attack_samples > 0:
            env[:attack_samples] = np.linspace(0, 1, attack_samples) ** 2

        decay_end = attack_samples + decay_samples
        if decay_samples > 0 and decay_end < samples:
            env[attack_samples:decay_end] = np.linspace(1, sustain, decay_samples)

        sustain_end = samples - release_samples
        if sustain_end > decay_end and sustain_end < samples:
            env[decay_end:sustain_end] = sustain

        if release_samples > 0 and sustain_end < samples:
            env[sustain_end:] = np.linspace(sustain, 0, release_samples) ** 2

        return env

    def add_flute_note(freq, start_time, note_duration, volume=0.12):
        start = int(start_time * sample_rate)
        samples = int(note_duration * sample_rate)
        if start >= len(audio):
            return
        end = min(start + samples, len(audio))
        actual_samples = end - start
        note_t = np.linspace(0, note_duration, actual_samples, dtype=np.float32)
        envelope = create_flute_envelope(actual_samples)

        # Bamboo flute waveform - sine with subtle harmonics
        wave = np.sin(2 * np.pi * freq * note_t)
        wave += np.sin(2 * np.pi * freq * 2 * note_t) * 0.15
        wave += np.sin(2 * np.pi * freq * 3 * note_t) * 0.05
        wave += np.sin(2 * np.pi * freq * 0.5 * note_t) * 0.1  # warmth

        # Add slight vibrato
        vibrato = np.sin(2 * np.pi * 5 * note_t) * 0.003
        wave *= (1 + vibrato)

        wave = wave * envelope * volume
        audio[start:end] += wave

    def add_bass_note(freq, start_time, note_duration, volume=0.06):
        start = int(start_time * sample_rate)
        samples = int(note_duration * sample_rate)
        if start >= len(audio):
            return
        end = min(start + samples, len(audio))
        actual_samples = end - start
        note_t = np.linspace(0, note_duration, actual_samples, dtype=np.float32)
        envelope = create_flute_envelope(actual_samples, attack=0.15, decay=0.2, sustain=0.6, release=0.2)

        wave = np.sin(2 * np.pi * freq * note_t)
        wave += np.sin(2 * np.pi * freq * 0.5 * note_t) * 0.3

        wave = wave * envelope * volume
        audio[start:end] += wave

    # === 兰亭序风格旋律引用 ===
    # 主题：永和九年，岁在癸丑...
    # 使用五声音阶，优雅流畅

    # 0-10s: 开场，清雅
    add_bass_note(196.00, 0, 4, 0.05)  # G3

    # 主旋律 - 模仿兰亭序的悠扬
    add_flute_note(523.25, 0.5, 1.5, 0.10)   # C5
    add_flute_note(587.33, 2.0, 1.5, 0.09)   # D5
    add_flute_note(523.25, 3.5, 1.0, 0.08)   # C5
    add_flute_note(440.00, 4.5, 1.5, 0.09)   # A4

    add_flute_note(523.25, 6.0, 1.0, 0.10)
    add_flute_note(659.26, 7.0, 1.5, 0.09)   # E5
    add_flute_note(587.33, 8.5, 1.0, 0.08)   # D5

    # 10-20s: 发展
    add_bass_note(146.83, 10, 2, 0.04)  # D3

    add_flute_note(523.25, 10, 0.8, 0.10)
    add_flute_note(587.33, 10.8, 0.8, 0.09)
    add_flute_note(659.26, 11.6, 1.0, 0.11)
    add_flute_note(523.25, 12.6, 0.8, 0.09)
    add_flute_note(440.00, 13.4, 1.0, 0.08)
    add_flute_note(392.00, 14.4, 1.0, 0.07)

    add_flute_note(523.25, 16, 1.0, 0.10)
    add_flute_note(659.26, 17, 1.0, 0.09)
    add_flute_note(783.99, 18, 1.5, 0.11)   # G5
    add_flute_note(659.26, 19.5, 0.8, 0.09)

    # 20-30s: 高潮
    add_bass_note(130.81, 20, 3, 0.05)  # C3

    add_flute_note(523.25, 20, 0.6, 0.11)
    add_flute_note(587.33, 20.6, 0.6, 0.10)
    add_flute_note(659.26, 21.2, 0.6, 0.11)
    add_flute_note(783.99, 21.8, 0.8, 0.12)
    add_flute_note(659.26, 22.6, 0.6, 0.10)
    add_flute_note(523.25, 23.2, 0.6, 0.09)
    add_flute_note(440.00, 23.8, 0.8, 0.08)

    add_flute_note(392.00, 25, 1.0, 0.09)
    add_flute_note(440.00, 26, 1.0, 0.10)
    add_flute_note(523.25, 27, 1.5, 0.11)
    add_flute_note(392.00, 28.5, 0.8, 0.08)

    # 30-40s: 过渡
    add_bass_note(164.81, 30, 2, 0.04)  # E3

    add_flute_note(440.00, 30, 1.0, 0.09)
    add_flute_note(523.25, 31, 1.0, 0.10)
    add_flute_note(587.33, 32, 1.0, 0.09)
    add_flute_note(523.25, 33, 0.8, 0.08)
    add_flute_note(440.00, 33.8, 0.8, 0.07)

    add_flute_note(392.00, 35, 1.0, 0.08)
    add_flute_note(440.00, 36, 1.0, 0.09)
    add_flute_note(523.25, 37, 1.0, 0.10)
    add_flute_note(659.26, 38, 1.5, 0.11)
    add_flute_note(523.25, 39.5, 0.8, 0.09)

    # 40-50s: 再现
    add_bass_note(196.00, 40, 3, 0.05)  # G3

    add_flute_note(440.00, 40, 1.0, 0.10)
    add_flute_note(523.25, 41, 1.5, 0.11)
    add_flute_note(587.33, 42.5, 1.0, 0.09)
    add_flute_note(523.25, 43.5, 0.8, 0.08)
    add_flute_note(440.00, 44.3, 1.0, 0.07)

    add_flute_note(392.00, 46, 1.0, 0.08)
    add_flute_note(440.00, 47, 1.0, 0.09)
    add_flute_note(523.25, 48, 1.5, 0.10)

    # 50-60s: 尾声
    add_bass_note(130.81, 50, 4, 0.04)  # C3

    add_flute_note(440.00, 50, 1.0, 0.08)
    add_flute_note(392.00, 51, 1.0, 0.07)
    add_flute_note(440.00, 52, 1.0, 0.06)
    add_flute_note(523.25, 53, 2.0, 0.07)
    add_flute_note(392.00, 55, 1.5, 0.05)
    add_flute_note(329.63, 56.5, 2.0, 0.04)

    add_flute_note(261.63, 58, 2.0, 0.03)  # C4 fade out

    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.80

    audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)

    audio_int = (audio * 32767).astype(np.int16)
    return sample_rate, audio_int


if __name__ == "__main__":
    print("[INFO] Generating bamboo flute style music (兰亭序风)...")

    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "bgm")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, "bamboo_flute.wav")

    sample_rate, audio = generate_bamboo_flute_music()
    wavfile.write(output_path, sample_rate, audio)

    print(f"[OK] Music generated: {output_path}")
    print(f"     Duration: 60 seconds")
    print(f"     Style: Bamboo flute, elegant and flowing (兰亭序风)")