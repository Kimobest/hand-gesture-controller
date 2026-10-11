"""
====================================================================
 ملف الإعدادات الرئيسي (AI Hand-Gesture PC Controller Configuration)
====================================================================
يحتوي هذا الملف على كافة إعدادات:
1. ربط حركات وإيماءات اليد بأوامر واختصارات النظام.
2. إعدادات الكاميرا ودقتها والتبديل التلقائي.
3. مؤقتات التهدئة (Cooldown) لمنع التكرار العشوائي للأوامر.
4. المؤثرات الصوتية التنبيهية عند تنفيذ الأوامر.
====================================================================
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")

# ====================================================================
# 1. إعدادات الكاميرا والتعرف على اليد (Camera & Tracking Settings)
# ====================================================================

def detect_available_cameras(max_check=4):
    """فحص واكتشاف أرقام الكاميرات المتاحة في النظام"""
    available = []
    try:
        import cv2
        for i in range(max_check):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available.append(i)
                cap.release()
    except Exception:
        pass
    return available if available else [0]

# رقم الكاميرا الافتراضية
CAMERA_INDEX = 0

# إظهار قائمة اختيار الكاميرا عند بدء التشغيل إذا وُجد أكثر من كاميرا
PROMPT_CAMERA_ON_START = True

# أبعاد إطار الكاميرا
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FLIP_HORIZONTAL = True  # وضع المرآة لتسهيل التحكم الطبيعي

# تتبع يد واحدة (يد يمنى أو يسرى) لضمان أعلى استجابة (60+ FPS) ودقة 100%
NUM_HANDS = 1

# حساسية نموذج الذكاء الاصطناعي (من 0.0 إلى 1.0)
MIN_DETECTION_CONFIDENCE = 0.70
MIN_TRACKING_CONFIDENCE = 0.70
MIN_GESTURE_SCORE = 0.70

# مسار نموذج MediaPipe Gesture Recognizer
MODEL_PATH = os.path.join(BASE_DIR, "gesture_recognizer.task")
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"

# ====================================================================
# 2. مؤقتات التهدئة ومنع التكرار (Cooldown & Anti-Spam Timers)
# ====================================================================

# المؤقت العام بين تنفيذ الأوامر (بالثواني)
COOLDOWN_SECONDS = 1.0

# مؤقت مخصص لرفع وخفض الصوت لجعله أكثر سلاسة وسرعة
VOLUME_COOLDOWN_SECONDS = 0.25

# منع تكرار الأمر إلا بعد إفلات الحركة وإعادتها مجدداً (Re-arming)
REQUIRE_GESTURE_RELEASE = True

# ====================================================================
# 3. التأكيد الصوتي المسموع (Audio Feedback Settings)
# ====================================================================

ENABLE_AUDIO_FEEDBACK = True
AUDIO_FEEDBACK_VOLUME = 0.60

# ====================================================================
# 4. خريطة الأوامر والحركات (Gesture-to-Action Mapping)
# ====================================================================
# يمكنك تعديل أي أمر أو تغيير الاختصار من القائمة المتاحة أدناه:
# الأوامر المتاحة:
# - "MEDIA_PLAY_PAUSE"   : تشغيل / إيقاف مؤقت لليوتيوب وسبوتيفاي والفيديو
# - "VOLUME_UP"          : رفع صوت الجهاز (+4%)
# - "VOLUME_DOWN"        : خفض صوت الجهاز (-4%)
# - "VOLUME_MUTE"        : كتم / إلغاء كتم الصوت
# - "MEDIA_NEXT_TRACK"   : الانتقال للمقطع أو الأغنية التالية
# - "MEDIA_PREV_TRACK"   : الانتقال للمقطع السابق
# - "SHOW_DESKTOP"       : إظهار سطح المكتب وإخفاء كافة النوافذ (Win + D)
# - "TAKE_SCREENSHOT"    : تشغيل أداة لقطة الشاشة (Win + Shift + S)
# - "LOCK_PC"            : قفل شاشة الكمبيوتر (Win + L)
# - "TASK_SWITCH"        : التنقل بين النوافذ المفتوحة (Alt + Tab)
# ====================================================================

GESTURE_ACTION_MAP = {
    # 🖐️ كف مفتوح -> تشغيل / إيقاف مؤقت للوسائط
    "Open_Palm": {
        "action": "MEDIA_PLAY_PAUSE",
        "label": "Play / Pause",
        "label_ar": "تشغيل / إيقاف مؤقت",
        "emoji": "🖐️",
        "color": (0, 255, 128),     # أخضر نيون
        "cooldown": 1.2,
        "require_release": True
    },

    # ✊ قبضة اليد -> كتم / إلغاء كتم الصوت
    "Closed_Fist": {
        "action": "VOLUME_MUTE",
        "label": "Mute / Unmute",
        "label_ar": "كتم / إلغاء كتم الصوت",
        "emoji": "✊",
        "color": (0, 80, 255),      # أحمر
        "cooldown": 1.0,
        "require_release": True
    },

    # 👍 إبهام لأعلى -> رفع مستوى الصوت
    "Thumb_Up": {
        "action": "VOLUME_UP",
        "label": "Volume Up",
        "label_ar": "رفع الصوت",
        "emoji": "👍",
        "color": (0, 220, 255),     # أصفر
        "cooldown": VOLUME_COOLDOWN_SECONDS,
        "require_release": False    # يمكن الاستمرار برفع الصوت بسلاسة
    },

    # 👎 إبهام لأسفل -> خفض مستوى الصوت
    "Thumb_Down": {
        "action": "VOLUME_DOWN",
        "label": "Volume Down",
        "label_ar": "خفض الصوت",
        "emoji": "👎",
        "color": (255, 100, 200),   # أرجواني
        "cooldown": VOLUME_COOLDOWN_SECONDS,
        "require_release": False    # يمكن الاستمرار بخفض الصوت بسلاسة
    },

    # ✌️ علامة النصر -> التقاط لقطة شاشة (قص الشاشة)
    "Victory": {
        "action": "TAKE_SCREENSHOT",
        "label": "Take Screenshot",
        "label_ar": "لقطة شاشة (قص)",
        "emoji": "✌️",
        "color": (255, 200, 0),     # أزرق سماوي
        "cooldown": 1.5,
        "require_release": True
    },

    # ☝️ سبابة لأعلى -> التخطي للمقطع التالي
    "Pointing_Up": {
        "action": "MEDIA_NEXT_TRACK",
        "label": "Next Track",
        "label_ar": "المقطع التالي",
        "emoji": "☝️",
        "color": (200, 50, 255),    # وردي
        "cooldown": 1.0,
        "require_release": True
    },

    # 🤟 علامة الروك / الحب -> إظهار سطح المكتب وتصغير النوافذ
    "ILoveYou": {
        "action": "SHOW_DESKTOP",
        "label": "Show Desktop",
        "label_ar": "إظهار سطح المكتب",
        "emoji": "🤟",
        "color": (255, 120, 0),     # أزرق كهربائي
        "cooldown": 1.2,
        "require_release": True
    }
}
