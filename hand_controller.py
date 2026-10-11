"""
================================================================================
 تطبيق التحكم بجهاز الكمبيوتر بإيماءات اليد الذكية (AI Hand-Gesture PC Controller)
================================================================================
الخصائص والميزات:
- تحكم فوري في وسائط واختصارات وصوت ويندوز بدون لمس لوحة المفاتيح أو الماوس.
- أداء فائق وسريع جداً (60+ FPS) بأقل استهلاك للمعالج والذاكرة.
- منع التكرار العشوائي (Anti-Spam Cooldown & Re-Arming Engine).
- تأكيد صوتي ناعم (Audio Confirmation) عند تنفيذ كل أمر.
- واجهة HUD تفاعلية مستقبلية مع إمكانية التبديل بين الكاميرات مباشرة بحرف [C].
================================================================================
"""

import os
import sys
import time
import threading
import urllib.request
import numpy as np
import cv2
import sounddevice as sd
import soundfile as sf

# ضمان دعم الترميز UTF-8 في ويندوز
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
from actions import ActionManager

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# روابط مفاصل اليد (21 Landmark Hand Topology)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # الإبهام (Thumb)
    (0, 5), (5, 6), (6, 7), (7, 8),        # السبابة (Index)
    (5, 9), (9, 10), (10, 11), (11, 12),   # الوسطى (Middle)
    (9, 13), (13, 14), (14, 15), (15, 16), # البنصر (Ring)
    (13, 17), (17, 18), (18, 19), (19, 20),# الخنصر (Pinky)
    (0, 17)                                # قاعدة الكف (Palm Base)
]


class AudioFeedbackManager:
    """محرك التأكيد الصوتي المسموع عند تنفيذ أوامر اليد"""

    def __init__(self):
        self.sounds = {}
        self.enabled = config.ENABLE_AUDIO_FEEDBACK
        self.volume = config.AUDIO_FEEDBACK_VOLUME
        self.preload_sounds()

    def preload_sounds(self):
        """تحميل النغمات التنبيهية مسبقاً في الذاكرة لتشغيلها بلحظية (< 1ms)"""
        if not self.enabled:
            return

        sound_files = {
            "volume": "volume.wav",
            "trigger": "trigger.wav",
            "toggle": "toggle.wav",
            "screenshot": "screenshot.wav"
        }

        for key, fname in sound_files.items():
            path = os.path.join(config.SOUNDS_DIR, fname)
            if os.path.exists(path):
                try:
                    data, sr = sf.read(path, dtype='float32')
                    if len(data.shape) == 1:
                        data = np.column_stack((data, data))
                    data = data * float(self.volume)
                    self.sounds[key] = (data, sr)
                except Exception:
                    pass

    def play_feedback(self, sound_key):
        """تشغيل النغمة في خيط منفصل لتفادي أي تجميد للـ HUD"""
        if not self.enabled or sound_key not in self.sounds:
            return

        data, sr = self.sounds[sound_key]

        def _worker():
            try:
                sd.play(data, sr)
                sd.wait()
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()


class GestureCooldownManager:
    """نظام ذكي لمنع تكرار الأوامر بالخطأ مع دعم التكرار السلس لمستوى الصوت"""

    def __init__(self):
        self.last_trigger_times = {g: 0.0 for g in config.GESTURE_ACTION_MAP}
        self.last_detected_gesture = "None"
        self.gesture_released = True

    def update_state(self, current_gesture):
        """تحديث حالة إفلات اليد لإعادة تفعيل الأوامر (Re-arming)"""
        if current_gesture != self.last_detected_gesture:
            self.gesture_released = True
        self.last_detected_gesture = current_gesture

    def can_trigger(self, gesture):
        """التحقق مما إذا كانت الحركة مؤهلة لإطلاق الأمر الآن"""
        info = config.GESTURE_ACTION_MAP.get(gesture)
        if not info:
            return False, 0.0

        now = time.time()
        last_time = self.last_trigger_times.get(gesture, 0.0)
        cooldown = info.get("cooldown", config.COOLDOWN_SECONDS)
        require_release = info.get("require_release", config.REQUIRE_GESTURE_RELEASE)

        # التحقق من شرط إفلات اليد للحركات التي تتطلب ذلك
        if require_release and not self.gesture_released:
            return False, 0.0

        # التحقق من انقضاء وقت الـ Cooldown
        if (now - last_time) >= cooldown:
            return True, 1.0

        ratio = max(0.0, min(1.0, (now - last_time) / cooldown))
        return False, ratio

    def mark_triggered(self, gesture):
        """تسجيل وقت تفعيل الحركة"""
        self.last_trigger_times[gesture] = time.time()
        info = config.GESTURE_ACTION_MAP.get(gesture, {})
        if info.get("require_release", True):
            self.gesture_released = False

    def get_remaining_cooldown(self, gesture):
        """حساب النسبة المئوية للمؤقت (من 0.0 إلى 1.0)"""
        info = config.GESTURE_ACTION_MAP.get(gesture)
        if not info:
            return 1.0

        now = time.time()
        last_time = self.last_trigger_times.get(gesture, 0.0)
        cooldown = info.get("cooldown", config.COOLDOWN_SECONDS)
        elapsed = now - last_time
        if elapsed >= cooldown:
            return 1.0
        return max(0.0, min(1.0, elapsed / cooldown))


class HandControllerApp:
    """التطبيق الرئيسي للتحكم بالكمبيوتر بإيماءات اليد"""

    def __init__(self):
        self.ensure_model_exists()
        self.feedback_mgr = AudioFeedbackManager()
        self.cooldown_mgr = GestureCooldownManager()

        # الكشف عن الكاميرات المتاحة
        self.available_cameras = config.detect_available_cameras()
        self.camera_index = config.CAMERA_INDEX
        if self.camera_index not in self.available_cameras and self.available_cameras:
            self.camera_index = self.available_cameras[0]

        self.cap = None
        self.camera_toast_text = ""
        self.camera_toast_time = 0.0

        # أحدث أمر تم تنفيذه لعرضه في الواجهة
        self.last_action_label = "None"
        self.last_action_emoji = "💤"
        self.last_action_time = 0.0

        # وضع جهة تفعيل الكف ('BACK', 'FRONT', 'BOTH')
        self.open_palm_mode = getattr(config, "OPEN_PALM_TRIGGER_SIDE", "BACK").upper()

        # اختيار الكاميرا التفاعلي عند بدء التشغيل
        if getattr(config, "PROMPT_CAMERA_ON_START", True) and len(self.available_cameras) > 1:
            self.select_camera_interactive()

        # تهيئة نموذج MediaPipe Gesture Recognizer ليد واحدة
        base_options = mp_python.BaseOptions(model_asset_path=config.MODEL_PATH)
        options = mp_vision.GestureRecognizerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
            num_hands=config.NUM_HANDS,
            min_hand_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=config.MIN_TRACKING_CONFIDENCE,
            min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE
        )
        print("[*] جاري تحميل محرك الذكاء الاصطناعي (MediaPipe Tasks Vision)...")
        self.recognizer = mp_vision.GestureRecognizer.create_from_options(options)
        print("[✓] تم تفعيل محرك الذكاء الاصطناعي بنجاح!\n")

        self.fps = 0.0
        self.fps_filter = 0.9
        self.prev_time = time.time()

    def select_camera_interactive(self):
        """عرض قائمة اختيار الكاميرا عند توفر أكثر من كاميرا متصلة"""
        print("\n" + "=" * 65)
        print("  📷 تم اكتشاف أكثر من كاميرا متصلة بالنظام:")
        print("=" * 65)
        for idx in self.available_cameras:
            marker = " (الكاميرا الحالية)" if idx == self.camera_index else ""
            print(f"   [{idx}] Camera #{idx}{marker}")
        print("-----------------------------------------------------------------")
        print(f" اضغط رقم الكاميرا لاختيارها فوراً، أو اضغط Enter لمتابعة #{self.camera_index}")
        print(" (يمكنك أيضاً الضغط على حرف [C] في أي وقت أثناء عمل الكاميرا للتبديل)")
        print("-----------------------------------------------------------------")

        try:
            import msvcrt
            print(f"[*] المتابعة تلقائياً خلال 3 ثوانٍ: ", end="", flush=True)
            start_t = time.time()
            timeout = 3.0
            chosen = None
            last_sec = -1

            while time.time() - start_t < timeout:
                remaining = int(timeout - (time.time() - start_t) + 0.9)
                if remaining != last_sec:
                    print(f"{remaining}.. ", end="", flush=True)
                    last_sec = remaining

                if msvcrt.kbhit():
                    ch = msvcrt.getch().decode("utf-8", errors="ignore").strip()
                    if ch in [str(c) for c in self.available_cameras]:
                        chosen = int(ch)
                        break
                    elif ch in ["\r", "\n", " "]:
                        chosen = self.camera_index
                        break
                time.sleep(0.05)

            if chosen is not None:
                self.camera_index = chosen
                print(f"\n[✓] تم اختيار الكاميرا #{self.camera_index}!\n")
            else:
                print(f"\n[✓] تم المتابعة بالكاميرا الافتراضية #{self.camera_index}.\n")
        except Exception:
            pass

    def ensure_model_exists(self):
        """التأكد من وجود ملف نموذج MediaPipe وتنزيله تلقائياً إذا كان مفقوداً"""
        if not os.path.exists(config.MODEL_PATH):
            print(f"[!] جاري تنزيل نموذج الذكاء الاصطناعي من Google: {config.MODEL_URL}")
            try:
                urllib.request.urlretrieve(config.MODEL_URL, config.MODEL_PATH)
                print("[✓] اكتمل تنزيل النموذج بنجاح!")
            except Exception as e:
                print(f"[X] فشل تنزيل النموذج: {e}")
                sys.exit(1)

    def switch_camera(self):
        """التبديل الفوري إلى الكاميرا التالية في الوقت الفعلي"""
        if len(self.available_cameras) <= 1:
            self.camera_toast_text = "Only 1 Camera Detected"
            self.camera_toast_time = time.time()
            return

        cur_pos = self.available_cameras.index(self.camera_index) if self.camera_index in self.available_cameras else 0
        next_cam = self.available_cameras[(cur_pos + 1) % len(self.available_cameras)]

        print(f"\n[*] جاري التبديل من الكاميرا #{self.camera_index} إلى الكاميرا #{next_cam}...")
        new_cap = cv2.VideoCapture(next_cam)
        new_cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        new_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        if new_cap.isOpened():
            ret_test, _ = new_cap.read()
            if ret_test:
                if self.cap:
                    self.cap.release()
                self.cap = new_cap
                self.camera_index = next_cam
                self.camera_toast_text = f"Switched to Cam #{self.camera_index}"
                self.camera_toast_time = time.time()
                print(f"[✓] تم الانتقال بنجاح إلى الكاميرا #{self.camera_index}!")
                return
            new_cap.release()

        print(f"[X] تعذر فتح الكاميرا #{next_cam}!")
        self.camera_toast_text = f"Failed to open Cam #{next_cam}"
        self.camera_toast_time = time.time()

    def toggle_open_palm_mode(self):
        """التبديل الفوري بين أوضاع الكف: وش اليد (FRONT) -> ضهر اليد (BACK) -> الجهتين (BOTH)"""
        modes = ["FRONT", "BACK", "BOTH"]
        idx = modes.index(self.open_palm_mode) if self.open_palm_mode in modes else 0
        self.open_palm_mode = modes[(idx + 1) % len(modes)]
        labels = {
            "FRONT": "وش اليد (Palm Front)",
            "BACK": "ضهر اليد (Back of Hand)",
            "BOTH": "الجهتين معاً (Both Sides)"
        }
        self.camera_toast_text = f"Mode: {self.open_palm_mode} ({labels[self.open_palm_mode]})"
        self.camera_toast_time = time.time()
        print(f"\n[🔄] تم تبديل وضع كف اليد فوراً إلى: {labels[self.open_palm_mode]}")

    def draw_hand_skeleton(self, frame, landmarks, color=(0, 255, 128)):
        """رسم هيكل اليد والمفاصل بخطوط متوهجة وتصميم عصري"""
        h, w, _ = frame.shape
        points = []

        for lm in landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            points.append((cx, cy))

        for p1_idx, p2_idx in HAND_CONNECTIONS:
            pt1 = points[p1_idx]
            pt2 = points[p2_idx]
            cv2.line(frame, pt1, pt2, (35, 35, 45), 4, cv2.LINE_AA)
            cv2.line(frame, pt1, pt2, color, 2, cv2.LINE_AA)

        for i, (cx, cy) in enumerate(points):
            radius = 5 if i in [4, 8, 12, 16, 20] else 3
            cv2.circle(frame, (cx, cy), radius + 2, (0, 0, 0), -1, cv2.LINE_AA)
            cv2.circle(frame, (cx, cy), radius, (255, 255, 255), -1, cv2.LINE_AA)

    @staticmethod
    def get_hand_orientation(landmarks, mediapipe_handedness):
        """
        تحديد ما إذا كان المعروض هو:
        - 'FRONT' (وش اليد / كف اليد Palm Front)
        - 'BACK'  (ضهر اليد / Back of Hand)
        في الكاميرا المنعكسة (cv2.flip) عبر المقارنة الهندسية لموضع الخنصر (17) والسبابة (5):
        - اليد اليمنى (تصنفها MediaPipe كـ 'Left'):
          وش اليد -> الخنصر يمين السبابة (landmarks[17].x > landmarks[5].x)
          ضهر اليد -> الخنصر يسار السبابة (landmarks[17].x < landmarks[5].x)
        - اليد اليسرى (تصنفها MediaPipe كـ 'Right'):
          وش اليد -> الخنصر يسار السبابة (landmarks[17].x < landmarks[5].x)
          ضهر اليد -> الخنصر يمين السبابة (landmarks[17].x > landmarks[5].x)
        """
        idx_x = landmarks[5].x
        pnk_x = landmarks[17].x

        if mediapipe_handedness == "Left":  # اليد اليمنى في المرآة
            is_front = pnk_x > idx_x
        elif mediapipe_handedness == "Right":  # اليد اليسرى في المرآة
            is_front = pnk_x < idx_x
        else:
            thumb_x = landmarks[4].x
            if thumb_x < pnk_x:
                is_front = pnk_x > idx_x
            else:
                is_front = pnk_x < idx_x

        return "FRONT" if is_front else "BACK"

    @staticmethod
    def are_fingers_open(landmarks):
        """فحص هندسي للمفاصل للتأكد مما إذا كانت أصابع اليد مفرودة بالكامل (Open Hand)."""
        def d(i, j):
            return ((landmarks[i].x - landmarks[j].x) ** 2 + (landmarks[i].y - landmarks[j].y) ** 2) ** 0.5

        index_ext = d(8, 0) > d(6, 0) * 1.15
        middle_ext = d(12, 0) > d(10, 0) * 1.15
        ring_ext = d(16, 0) > d(14, 0) * 1.15
        pinky_ext = d(20, 0) > d(18, 0) * 1.15
        thumb_ext = d(4, 17) > d(2, 17) * 1.10

        all_five = (index_ext and middle_ext and ring_ext and pinky_ext) and (thumb_ext or d(4, 0) > d(2, 0) * 1.15)
        four_fingers = (index_ext and middle_ext and ring_ext and pinky_ext)
        return all_five, four_fingers

    def draw_hud(self, frame, current_gesture, score, is_triggering, hand_name="", detected_side="UNKNOWN", is_matched=True):
        """رسم واجهة تفاعلية شاشية مستقبلية (HUD Overlay) مع عرض وضع وش/ضهر اليد"""
        h, w, _ = frame.shape

        # الشريط العلوي والسفلي الشفاف
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 75), (14, 14, 20), -1)
        cv2.rectangle(overlay, (0, h - 45), (w, h), (14, 14, 20), -1)
        cv2.addWeighted(overlay, 0.80, frame, 0.20, 0, frame)

        cv2.line(frame, (0, 75), (w, 75), (55, 55, 75), 1)
        cv2.line(frame, (0, h - 45), (w, h - 45), (55, 55, 75), 1)

        # معلومات الحركة الحالية
        gesture_info = config.GESTURE_ACTION_MAP.get(current_gesture, None)
        if gesture_info and score >= config.MIN_GESTURE_SCORE:
            label = gesture_info["label"]
            emoji = gesture_info.get("emoji", "")
            color = gesture_info.get("color", (0, 255, 128))
            cooldown_ratio = self.cooldown_mgr.get_remaining_cooldown(current_gesture)

            cv2.putText(frame, f"{emoji} {label.upper()}", (20, 32),
                        cv2.FONT_HERSHEY_DUPLEX, 0.75, color, 2, cv2.LINE_AA)

            sub_info = f"Conf: {int(score * 100)}%"
            if current_gesture == "Open_Palm":
                side_lbl = "BACK OF HAND" if detected_side == "BACK" else "PALM (FRONT)"
                sub_info += f" | {side_lbl} [ACTIVE]"
            cv2.putText(frame, sub_info, (20, 58),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (190, 190, 200), 1, cv2.LINE_AA)

            # شريط مؤقت الـ Cooldown
            bar_x, bar_y, bar_w, bar_h = 340, 44, 140, 12
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (40, 40, 50), -1)
            fill_w = int(bar_w * cooldown_ratio)
            bar_color = (0, 255, 128) if cooldown_ratio >= 1.0 else (0, 140, 255)
            if fill_w > 0:
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), bar_color, -1)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (100, 100, 120), 1)

            status_text = "READY" if cooldown_ratio >= 1.0 else f"WAIT {int((1.0 - cooldown_ratio) * 10) / 10}s"
            cv2.putText(frame, status_text, (bar_x + bar_w + 8, bar_y + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, bar_color, 1, cv2.LINE_AA)

            if is_triggering:
                cv2.rectangle(frame, (0, 0), (w, h), color, 6)
        else:
            if not is_matched and detected_side in ["BACK", "FRONT"]:
                expected = "BACK of hand" if self.open_palm_mode == "BACK" else "PALM (front)"
                cv2.putText(frame, f"BLOCKED: Show {expected}", (20, 32),
                            cv2.FONT_HERSHEY_DUPLEX, 0.62, (0, 140, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, f"Detected: {detected_side} | Press [T] to change Palm Mode", (20, 58),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 200, 255), 1, cv2.LINE_AA)
            elif detected_side in ["BACK", "FRONT"]:
                side_lbl = "BACK OF HAND" if detected_side == "BACK" else "PALM"
                cv2.putText(frame, f"{side_lbl} DETECTED | Ready", (20, 42),
                            cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 255, 128), 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, "READY | Show Hand Gesture", (20, 42),
                            cv2.FONT_HERSHEY_DUPLEX, 0.65, (160, 160, 170), 2, cv2.LINE_AA)

        # معدل الإطارات (FPS) وحالة الكاميرا ووضع الكف
        cv2.putText(frame, f"FPS: {int(self.fps)}", (w - 110, 26),
                    cv2.FONT_HERSHEY_DUPLEX, 0.60, (0, 255, 255), 1, cv2.LINE_AA)

        mode_badge = f"PALM: {self.open_palm_mode}"
        cv2.putText(frame, mode_badge, (w - 145, 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 255, 180), 1, cv2.LINE_AA)

        cam_text = f"CAM: #{self.camera_index}"
        cv2.putText(frame, cam_text, (w - 145, 66),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (100, 220, 255), 1, cv2.LINE_AA)

        # الشريط السفلي
        last_act = f"Last Action: {self.last_action_emoji} {self.last_action_label}"
        cv2.putText(frame, last_act, (20, h - 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 220, 100), 1, cv2.LINE_AA)

        hint_text = "[C] Switch Cam | [T] Mode (BACK/FRONT/BOTH) | [Q] Exit"
        cv2.putText(frame, hint_text, (w - 380, h - 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 170), 1, cv2.LINE_AA)

        # شارة تنفيذ الأمر الحية في منتصف الشاشة (Active Action Banner)
        if time.time() - self.last_action_time < 0.6:
            banner_w, banner_h = 360, 50
            bx = (w - banner_w) // 2
            by = (h - banner_h) // 2
            b_overlay = frame.copy()
            cv2.rectangle(b_overlay, (bx, by), (bx + banner_w, by + banner_h), (20, 25, 35), -1)
            cv2.addWeighted(b_overlay, 0.88, frame, 0.12, 0, frame)
            cv2.rectangle(frame, (bx, by), (bx + banner_w, by + banner_h), (0, 255, 128), 2)
            banner_txt = f"{self.last_action_emoji} {self.last_action_label.upper()}"
            cv2.putText(frame, banner_txt, (bx + 20, by + 34),
                        cv2.FONT_HERSHEY_DUPLEX, 0.70, (255, 255, 255), 2, cv2.LINE_AA)

        # إشعار منبثق عند تبديل الكاميرا (Toast Notification)
        if (time.time() - self.camera_toast_time < 2.5) and self.camera_toast_text:
            toast_w, toast_h = 320, 42
            tx = (w - toast_w) // 2
            ty = h - 90
            t_overlay = frame.copy()
            cv2.rectangle(t_overlay, (tx, ty), (tx + toast_w, ty + toast_h), (25, 25, 35), -1)
            cv2.addWeighted(t_overlay, 0.85, frame, 0.15, 0, frame)
            cv2.rectangle(frame, (tx, ty), (tx + toast_w, ty + toast_h), (0, 255, 128), 2)
            cv2.putText(frame, self.camera_toast_text, (tx + 18, ty + 28),
                        cv2.FONT_HERSHEY_DUPLEX, 0.58, (255, 255, 255), 1, cv2.LINE_AA)

    def run(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        if not self.cap.isOpened():
            print(f"[X] خطأ: تعذر فتح كاميرا الويب برقم الفهرس {self.camera_index}")
            return

        window_name = "AI Hand-Gesture PC Controller (Windows Actions)"
        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

        print("=" * 70)
        print("  🚀 نظام التحكم بالكمبيوتر بإيماءات اليد يعمل الآن بنجاح! 🚀")
        print(f"  - الكاميرا المستخدمة حالياً: Camera #{self.camera_index}")
        if len(self.available_cameras) > 1:
            print("  - [ميزة] اضغط حرف [C] في أي وقت للتبديل بين الكاميرات مباشرة.")
        print("  - أظهر يدك أمام الكاميرا ونفذ أي حركة لتنفيذ الأمر فوراً.")
        print("  - اضغط حرف [Q] من لوحة المفاتيح للخروج.")
        print("=" * 70 + "\n")

        while True:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.04)
                continue

            curr_time = time.time()
            instant_fps = 1.0 / max(curr_time - self.prev_time, 1e-5)
            self.fps = self.fps_filter * self.fps + (1.0 - self.fps_filter) * instant_fps
            self.prev_time = curr_time

            if config.FLIP_HORIZONTAL:
                frame = cv2.flip(frame, 1)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            recognition_result = self.recognizer.recognize(mp_image)

            current_gesture = "None"
            score = 0.0
            is_triggering = False
            hand_name = "Right"
            detected_side = "UNKNOWN"
            is_matched_side = True

            if recognition_result.hand_landmarks and len(recognition_result.hand_landmarks) > 0:
                hand_lms = recognition_result.hand_landmarks[0]

                if recognition_result.handedness and len(recognition_result.handedness) > 0:
                    hand_name = recognition_result.handedness[0][0].category_name

                # فحص اتجاه اليد (FRONT vs BACK) وفحص امتداد الأصابع
                detected_side = self.get_hand_orientation(hand_lms, hand_name)
                all_open, four_open = self.are_fingers_open(hand_lms)

                # مطابقة اتجاه اليد مع الوضع المختار (BACK أو FRONT أو BOTH)
                if self.open_palm_mode == "BOTH":
                    is_matched_side = True
                elif self.open_palm_mode == "BACK":
                    is_matched_side = (detected_side == "BACK")
                else:  # FRONT
                    is_matched_side = (detected_side == "FRONT")

                # قراءة الحركة من نموذج MediaPipe
                if recognition_result.gestures and len(recognition_result.gestures) > 0:
                    top_gesture = recognition_result.gestures[0][0]
                    current_gesture = top_gesture.category_name
                    score = top_gesture.score

                # تدقيق حركة الكف المفتوح (Open_Palm)
                if current_gesture == "Open_Palm":
                    if not is_matched_side:
                        # اليد غير مطابقة للوضع المختار -> حجب فوري للأمر
                        current_gesture = "None"
                        score = 0.0
                    else:
                        score = max(score, 0.95)
                elif (all_open or four_open) and is_matched_side:
                    current_gesture = "Open_Palm"
                    score = 0.95
                elif (all_open or four_open) and not is_matched_side:
                    current_gesture = "None"
                    score = 0.0

                # تحديد لون رسم هيكل اليد
                if current_gesture == "Open_Palm":
                    g_color = (0, 255, 128)  # أخضر فاقع للكف المفتوح المفعل
                elif not is_matched_side and (all_open or four_open):
                    g_color = (0, 140, 255)  # برتقالي تحذيري عند إظهار الجهة المحجوبة
                else:
                    g_color = config.GESTURE_ACTION_MAP.get(current_gesture, {}).get("color", (0, 255, 128))

                self.draw_hand_skeleton(frame, hand_lms, color=g_color)
                self.cooldown_mgr.update_state(current_gesture)

                # التحقق من شروط التفعيل وتنفيذ الأمر
                if current_gesture in config.GESTURE_ACTION_MAP and score >= config.MIN_GESTURE_SCORE:
                    can_fire, _ = self.cooldown_mgr.can_trigger(current_gesture)
                    if can_fire:
                        action_cfg = config.GESTURE_ACTION_MAP[current_gesture]
                        action_name = action_cfg["action"]

                        success, label, emoji = ActionManager.execute_action(action_name)
                        if success:
                            self.cooldown_mgr.mark_triggered(current_gesture)
                            is_triggering = True
                            self.last_action_label = label
                            self.last_action_emoji = emoji
                            self.last_action_time = time.time()

                            # تشغيل النغمة التنبيهية المناسبة
                            if "VOLUME" in action_name:
                                self.feedback_mgr.play_feedback("volume")
                            elif "SCREENSHOT" in action_name:
                                self.feedback_mgr.play_feedback("screenshot")
                            elif "PLAY_PAUSE" in action_name or "MUTE" in action_name:
                                self.feedback_mgr.play_feedback("toggle")
                            else:
                                self.feedback_mgr.play_feedback("trigger")

                            side_name = "ضهر اليد (Back)" if detected_side == "BACK" else "وش اليد (Palm)"
                            print(f"  [⚡ تنفيذ أمر!] {emoji} {label:<24} ({int(score * 100)}%) [{side_name}]")
            else:
                self.cooldown_mgr.update_state("None")

            self.draw_hud(frame, current_gesture, score, is_triggering,
                          hand_name=hand_name, detected_side=detected_side, is_matched=is_matched_side)

            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q') or key == 27:
                print("\n[*] إغلاق البرنامج...")
                break
            elif key == ord('c') or key == ord('C'):
                self.switch_camera()
            elif key == ord('t') or key == ord('T'):
                self.toggle_open_palm_mode()

        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        print("[✓] تم إنهاء جميع العمليات وإغلاق الكاميرا بأمان.")


if __name__ == "__main__":
    app = HandControllerApp()
    app.run()
