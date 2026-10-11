"""
====================================================================
 مولد المؤثرات الصوتية التنبيهية (DSP Audio Feedback Generator)
====================================================================
يقوم هذا السكريبت بإنشاء نغمات صوتية ناعمة وعصرية بصيغة WAV
تعمل كتأكيد صوتي (Auditory Confirmation) فوري عند تنفيذ أوامر اليد.
====================================================================
"""

import os
import sys
import numpy as np
import soundfile as sf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")
os.makedirs(SOUNDS_DIR, exist_ok=True)

SR = 44100


def save_wav(filename, signal):
    path = os.path.join(SOUNDS_DIR, filename)
    signal = np.clip(signal, -1.0, 1.0).astype(np.float32)
    stereo = np.column_stack((signal, signal))
    sf.write(path, stereo, SR)
    print(f"[✓] Created audio: {filename}")


def gen_click():
    # نقرة هادئة لتغيير مستوى الصوت
    dur = 0.04
    t = np.linspace(0, dur, int(SR * dur), False)
    env = np.exp(-t * 90)
    sig = 0.3 * np.sin(2 * np.pi * 880 * t) * env
    save_wav("volume.wav", sig)


def gen_trigger():
    # نغمة نجاح خفيفة للأوامر الأساسية
    dur = 0.08
    t = np.linspace(0, dur, int(SR * dur), False)
    env = np.exp(-t * 40)
    sig = 0.35 * (np.sin(2 * np.pi * 660 * t) + 0.5 * np.sin(2 * np.pi * 1320 * t)) * env
    save_wav("trigger.wav", sig)


def gen_toggle():
    # نغمة مزدوجة لـ Play/Pause و Mute
    dur = 0.12
    t = np.linspace(0, dur, int(SR * dur), False)
    env = np.exp(-t * 25)
    f = np.where(t < 0.06, 523.25, 659.25)
    sig = 0.35 * np.sin(2 * np.pi * f * t) * env
    save_wav("toggle.wav", sig)


def gen_shutter():
    # صوت التقاط لقطة الشاشة
    dur = 0.10
    t = np.linspace(0, dur, int(SR * dur), False)
    noise = np.random.uniform(-0.15, 0.15, len(t))
    env = np.exp(-t * 35)
    tone = np.sin(2 * np.pi * 1200 * t) * np.exp(-t * 60)
    sig = (0.2 * noise + 0.3 * tone) * env
    save_wav("screenshot.wav", sig)


if __name__ == "__main__":
    print("[*] Generating UI audio feedback effects...")
    gen_click()
    gen_trigger()
    gen_toggle()
    gen_shutter()
    print("[✓] All feedback sound assets generated successfully!\n")
