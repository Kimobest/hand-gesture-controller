# 🖐️⚡ AI Hand-Gesture PC Controller (Hand Commander)

A real-time, low-latency **AI Hand-Gesture PC Controller** that translates webcam hand gestures into Windows hotkeys, multimedia controls, and system actions without touching your keyboard or mouse.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-green?logo=opencv)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Vision%20Tasks-orange?logo=google)
![Windows](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-lightgrey?logo=windows)
![License](https://img.shields.io/badge/License-MIT-purple)

---

## 🌟 Key Features

* **Real-Time 60+ FPS Tracking**: Powered by Google MediaPipe Tasks Vision for smooth, instantaneous gesture recognition with minimal CPU/GPU overhead.
* **Instant Native Windows Control**: Direct Win32 `ctypes` key event dispatcher without cumbersome external drivers or background lag.
* **Smart Cooldown & Anti-Spam Engine**: Re-arming release logic prevents accidental multi-triggers, while volume gestures support smooth continuous adjustments.
* **Futuristic HUD Overlay**: Glassmorphism HUD displaying real-time hand skeleton joints, gesture confidence scores, animated trigger badges, and camera status.
* **Auditory Confirmation (Audio Feedback)**: Modern acoustic UI sound cues confirm every executed command through your headphones or speakers.
* **Live Camera Switcher**: Press **`C`** on your keyboard to switch between multiple connected webcams on the fly without closing the app.

---

## 🖐️ Gesture Commands & Hotkeys Mapping

| Gesture | Movement | Action Triggered | Windows Function |
| :---: | :--- | :--- | :--- |
| 🖐️ | **Open Palm** | **Play / Pause Media** | `VK_MEDIA_PLAY_PAUSE` (Spotify, YouTube, Chrome, VLC) |
| ✊ | **Closed Fist** | **Mute / Unmute Audio** | `VK_VOLUME_MUTE` (Instant audio silence toggle) |
| 👍 | **Thumb Up** | **Volume Up (+4%)** | `VK_VOLUME_UP` (Smooth volume increase) |
| 👎 | **Thumb Down** | **Volume Down (-4%)** | `VK_VOLUME_DOWN` (Smooth volume decrease) |
| ✌️ | **Victory (V Sign)** | **Take Screenshot** | `Win + Shift + S` (Windows Snipping Tool) |
| ☝️ | **Pointing Up** | **Next Track** | `VK_MEDIA_NEXT_TRACK` (Skip song / video) |
| 🤟 | **Rock / Love** | **Show Desktop** | `Win + D` (Minimize / Restore all windows) |

---

## 📁 Project Structure

```
hand-gesture-controller/
├── hand_controller.py         # Main application (Camera loop, MediaPipe, HUD, Controller loop)
├── actions.py                 # Windows system action executor (Media keys, hotkeys, ctypes)
├── config.py                  # Configuration file (Gesture mappings, sensitivity, cooldowns)
├── list_cameras.py            # Webcam discovery, live preview, and default selector tool
├── generate_audio_feedback.py # DSP sound synthesizer for UI feedback audio assets
├── requirements.txt           # Python library dependencies
├── run_controller.bat         # One-click Windows runner
├── sounds/                    # Confirmation audio sound effects (.wav)
│   ├── volume.wav
│   ├── trigger.wav
│   ├── toggle.wav
│   └── screenshot.wav
└── دليل_الاوامر.md              # Complete Arabic quickstart and gesture reference
```

---

## ⚡ Quick Start

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/Kimobest/hand-gesture-controller.git
cd hand-gesture-controller
pip install -r requirements.txt
```

### 2. Preview & Select Camera (Optional)

If you have multiple webcams (laptop camera, external USB cam, DroidCam, etc.):

```bash
python list_cameras.py
```

### 3. Launch the Controller

Launch via command line or double-click `run_controller.bat`:

```bash
python hand_controller.py
```

* Press **`C`** on your keyboard at any time to switch to the next camera.
* Press **`Q`** or **`ESC`** to exit cleanly.

---

## 🎛️ Customization

Edit `config.py` to customize any behavior:
* `GESTURE_ACTION_MAP`: Easily remap any gesture to another command (`SHOW_DESKTOP`, `LOCK_PC`, `TASK_SWITCH`, etc.).
* `COOLDOWN_SECONDS`: Adjust debounce delay (default: `1.0`s).
* `VOLUME_COOLDOWN_SECONDS`: Adjust volume step delay (default: `0.25`s).
* `ENABLE_AUDIO_FEEDBACK`: Enable/disable audio sound cues (`True` / `False`).

---

## 📜 License

MIT License. Free to use, modify, and distribute for personal and commercial projects.
