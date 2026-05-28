#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate guqin/pluck lute style background music - 青花瓷风格"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from scipy.io import wavfile


def generate_guqin_music():
    """Generate 60-second guqin style music - melodic and graceful like 青花瓷"""

    sample_rate = 44100
    duration = 60

    # Guqin uses pentatonic scale with emphasis on certain intervals
    notes = {
        'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'G4': 392.00, 'A4': 440.00,
        'C5': 523.25, 'D5': 587.33, 'E5': 659.26, 'G5': 783.99, 'A5': 880.00,
        'C6': 1046.50, 'E6': 1318.51,
    }

    fade_samples = int(sample_rate * 1.0)
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    audio = np.zeros(len(t), dtype=np.float32)

    def create_guqin_envelope(samples, attack=0.05, decay=0.2, sustain=0.6, release=0.2):
        env = np.ones(samples, dtype=np.float32)
        attack_samples = int(samples * attack)
        decay_samples = int(samples * decay)
        release_samples = int(samples * release)

        if attack_samples > 0:
            env[:attack_samples] = np.linspace(0, 1, attack_samples) ** 1.5

        decay_end = attack_samples + decay_samples
        if decay_samples > 0 and decay_end < samples:
            env[attack_samples:decay_end] = np.linspace(1, sustain, decay_samples)

        sustain_end = samples - release_samples
        if sustain_end > decay_end and sustain_end < samples:
            env[decay_end:sustain_end] = sustain

        if release_samples > 0 and sustain_end < samples:
            env[sustain_end:] = np.linspace(sustain, 0, release_samples) ** 1.5

        return env

    def add_guqin_note(freq, start_time, note_duration, volume=0.10, delay=0):
        """delay adds a slight echoing effect for guqin resonance"""
        start = int((start_time + delay) * sample_rate)
        samples = int(note_duration * sample_rate)
        if start >= len(audio):
            return
        end = min(start + samples, len(audio))
        actual_samples = end - start
        note_t = np.linspace(0, note_duration, actual_samples, dtype=np.float32)
        envelope = create_guqin_envelope(actual_samples)

        # Guqin pluck sound - muted, woody attack followed by ringing
        attack_env = np.exp(-note_t * 20)  # quick attack decay
        main_env = envelope * (1 - attack_env * 0.3)  # mix with sustain

        wave = np.sin(2 * np.pi * freq * note_t)
        # Add subtle harmonics for guqin timbre
        wave += np.sin(2 * np.pi * freq * 2 * note_t) * 0.2
        wave += np.sin(2 * np.pi * freq * 3 * note_t) * 0.08
        wave += np.sin(2 * np.pi * freq * 4 * note_t) * 0.03
        # Add warmth
        wave += np.sin(2 * np.pi * freq * 0.5 * note_t) * 0.15

        wave = wave * main_env * volume
        audio[start:end] += wave

        # Resonant echo for guqin
        if delay > 0:
            echo_start = int((start_time + note_duration * 0.7) * sample_rate)
            echo_samples = int(note_duration * 0.4 * sample_rate)
            if echo_start < len(audio):
                echo_end = min(echo_start + echo_samples, len(audio))
                echo_t = np.linspace(0, echo_end - echo_start, echo_end - echo_start, dtype=np.float32) / sample_rate
                echo_env = np.exp(-echo_t * 8) * 0.3
                echo_wave = np.sin(2 * np.pi * freq * echo_t) * echo_env * volume
                audio[echo_start:echo_end] += echo_wave

    def add_background_pad(freq, start_time, note_duration, volume=0.04):
        start = int(start_time * sample_rate)
        samples = int(note_duration * sample_rate)
        if start >= len(audio):
            return
        end = min(start + samples, len(audio))
        note_t = np.linspace(0, note_duration, end - start, dtype=np.float32)

        # Soft pad for background
        wave = np.sin(2 * np.pi * freq * note_t)
        wave += np.sin(2 * np.pi * freq * 2 * note_t) * 0.1

        env = np.ones(end - start, dtype=np.float32)
        fade_in = min(int(len(env) * 0.1), 1000)
        fade_out = min(int(len(env) * 0.3), 3000)
        env[:fade_in] = np.linspace(0, 1, fade_in)
        env[-fade_out:] = np.linspace(1, 0, fade_out)

        wave = wave * env * volume
        audio[start:end] += wave

    # === 青花瓷风格旋律 ===
    # 主题：天青色等烟雨，而我在等你...
    # 使用古琴的滑音和吟猱效果模拟

    # 0-8s: 序曲，悠然
    add_background_pad(130.81, 0, 4, 0.03)  # C3 soft pad
    add_background_pad(164.81, 0, 3, 0.025)  # E3

    # 古琴旋律 - 模拟青花瓷的婉转
    add_guqin_note(329.63, 0.5, 1.2, 0.09)   # E4
    add_guqin_note(392.00, 1.7, 1.0, 0.08)   # G4
    add_guqin_note(329.63, 2.7, 0.8, 0.07)   # E4

    add_guqin_note(440.00, 4.0, 1.5, 0.09)   # A4
    add_guqin_note(523.25, 5.5, 1.0, 0.08)   # C5
    add_guqin_note(440.00, 6.5, 0.8, 0.07)   # A4

    add_guqin_note(392.00, 7.5, 2.0, 0.08)   # G4

    # 8-16s: 展开
    add_background_pad(146.83, 8, 4, 0.025)  # D3

    add_guqin_note(523.25, 8.5, 0.6, 0.09)   # C5
    add_guqin_note(587.33, 9.1, 0.6, 0.08)   # D5
    add_guqin_note(659.26, 9.7, 0.8, 0.09)   # E5
    add_guqin_note(523.25, 10.5, 0.6, 0.08)
    add_guqin_note(440.00, 11.1, 0.8, 0.07)
    add_guqin_note(392.00, 11.9, 0.6, 0.06)

    add_guqin_note(523.25, 13.0, 0.8, 0.08)
    add_guqin_note(659.26, 13.8, 1.0, 0.09)
    add_guqin_note(783.99, 14.8, 1.5, 0.10)  # G5

    # 16-24s: 抒情
    add_background_pad(98.00, 16, 6, 0.03)   # G2 bass

    add_guqin_note(523.25, 16.5, 0.5, 0.09)
    add_guqin_note(587.33, 17.0, 0.5, 0.08)
    add_guqin_note(659.26, 17.5, 0.8, 0.09)
    add_guqin_note(783.99, 18.3, 0.6, 0.10)  # G5
    add_guqin_note(659.26, 18.9, 0.5, 0.08)
    add_guqin_note(523.25, 19.4, 0.8, 0.07)

    add_guqin_note(440.00, 20.5, 1.0, 0.08)
    add_guqin_note(523.25, 21.5, 1.0, 0.09)
    add_guqin_note(587.33, 22.5, 1.5, 0.10)  # D5

    # 24-32s: 高潮
    add_background_pad(130.81, 24, 4, 0.035)  # C3

    add_guqin_note(523.25, 24.5, 0.4, 0.10)
    add_guqin_note(587.33, 24.9, 0.4, 0.09)
    add_guqin_note(659.26, 25.3, 0.4, 0.10)
    add_guqin_note(783.99, 25.7, 0.6, 0.11)
    add_guqin_note(880.00, 26.3, 0.8, 0.12)  # A5
    add_guqin_note(783.99, 27.1, 0.4, 0.10)
    add_guqin_note(659.26, 27.5, 0.4, 0.09)
    add_guqin_note(523.25, 27.9, 0.6, 0.08)

    add_guqin_note(392.00, 29.0, 1.0, 0.08)
    add_guqin_note(440.00, 30.0, 1.0, 0.09)
    add_guqin_note(523.25, 31.0, 1.5, 0.10)

    # 32-40s: 过渡
    add_background_pad(164.81, 32, 3, 0.025)  # E3

    add_guqin_note(440.00, 32.5, 0.8, 0.08)
    add_guqin_note(523.25, 33.3, 0.8, 0.09)
    add_guqin_note(587.33, 34.1, 0.8, 0.08)
    add_guqin_note(523.25, 34.9, 0.6, 0.07)
    add_guqin_note(440.00, 35.5, 0.8, 0.06)

    add_guqin_note(392.00, 36.5, 0.8, 0.07)
    add_guqin_note(440.00, 37.3, 0.8, 0.08)
    add_guqin_note(523.25, 38.1, 1.0, 0.09)
    add_guqin_note(659.26, 39.1, 1.5, 0.10)

    # 40-50s: 再现与收束
    add_background_pad(98.00, 40, 5, 0.03)   # G2

    add_guqin_note(440.00, 40.5, 1.0, 0.09)
    add_guqin_note(523.25, 41.5, 1.0, 0.10)
    add_guqin_note(587.33, 42.5, 0.8, 0.08)
    add_guqin_note(523.25, 43.3, 0.6, 0.07)
    add_guqin_note(440.00, 43.9, 0.8, 0.06)

    add_guqin_note(392.00, 45.0, 1.0, 0.07)
    add_guqin_note(440.00, 46.0, 1.0, 0.08)
    add_guqin_note(523.25, 47.0, 1.5, 0.09)
    add_guqin_note(392.00, 48.5, 0.8, 0.06)

    # 50-60s: 尾声，余韵
    add_background_pad(130.81, 50, 6, 0.025)  # C3

    add_guqin_note(329.63, 50.5, 1.5, 0.07)   # E4
    add_guqin_note(392.00, 52.0, 1.0, 0.06)   # G4
    add_guqin_note(329.63, 53.0, 1.0, 0.05)
    add_guqin_note(261.63, 54.0, 2.0, 0.04)   # C4
    add_guqin_note(220.00, 56.0, 2.5, 0.03)   # A3 fade

    add_guqin_note(196.00, 58, 2.0, 0.02)     # G3 fade out

    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.75

    audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)

    audio_int = (audio * 32767).astype(np.int16)
    return sample_rate, audio_int


if __name__ == "__main__":
    print("[INFO] Generating guqin style music (青花瓷风)...")

    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "bgm")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, "pluck_lute.wav")

    sample_rate, audio = generate_guqin_music()
    wavfile.write(output_path, sample_rate, audio)

    print(f"[OK] Music generated: {output_path}")
    print(f"     Duration: 60 seconds")
    print(f"     Style: Guqin/pluck lute, melodic and graceful (青花瓷风)")