"""
================================================================================
 محرك تنفيذ أوامر واختصارات النظام (Windows System Actions Engine)
================================================================================
يقوم هذا الملف بتنفيذ أوامر واختصارات Windows مباشرة باستخدام ctypes وبدون
أي تأخير أو استهلاك لموارد النظام:
- التحكم في الوسائط (تشغيل / إيقاف مؤقت / التالي / السابق).
- التحكم في مستوى صوت الجهاز (رفع / خفض / كتم).
- اختصارات النظام (إظهار سطح المكتب / لقطة شاشة / قفل الشاشة).
================================================================================
"""

import sys
import time
import ctypes

user32 = ctypes.windll.user32
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001

# رموز أزرار ويندوز الافتراضية (Virtual-Key Codes)
VK_CODES = {
    # الوسائط (Media)
    "MEDIA_PLAY_PAUSE": 0xB3,
    "MEDIA_NEXT_TRACK": 0xB0,
    "MEDIA_PREV_TRACK": 0xB1,
    "MEDIA_STOP": 0xB2,
    # الصوت (Volume)
    "VOLUME_MUTE": 0xAD,
    "VOLUME_DOWN": 0xAE,
    "VOLUME_UP": 0xAF,
    # أزرار النظام (System & Modifiers)
    "LWIN": 0x5B,
    "SHIFT": 0x10,
    "CONTROL": 0x11,
    "MENU": 0x12,       # Alt
    "TAB": 0x09,
    "SNAPSHOT": 0x2C,   # PrintScreen
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    # الحروف (Letters)
    "D": 0x44,
    "L": 0x4C,
    "S": 0x53,
    "M": 0x4D,
    "Z": 0x5A,
}


def press_virtual_key(vk_code):
    """الضغط على زر افتراضي واحد وإفلاته"""
    user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
    time.sleep(0.01)
    user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


def press_hotkey_combo(vk_codes):
    """الضغط على تركيبة مفاتيح معاً (مثل Win + D أو Win + Shift + S)"""
    for vk in vk_codes:
        user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
    time.sleep(0.02)
    for vk in reversed(vk_codes):
        user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


class ActionManager:
    """مدير الأوامر الموحد"""

    @staticmethod
    def execute_action(action_name):
        """تنفيذ الأمر بالاسم وإرجاع النتيجة"""
        action = action_name.upper().strip()

        try:
            if action == "MEDIA_PLAY_PAUSE":
                press_virtual_key(VK_CODES["MEDIA_PLAY_PAUSE"])
                return True, "Play / Pause Media", "⏯️"

            elif action == "VOLUME_UP":
                # رفع الصوت درجتين لاستجابة سريعة وواضحة
                press_virtual_key(VK_CODES["VOLUME_UP"])
                time.sleep(0.02)
                press_virtual_key(VK_CODES["VOLUME_UP"])
                return True, "Volume Up (+4%)", "🔊"

            elif action == "VOLUME_DOWN":
                # خفض الصوت درجتين
                press_virtual_key(VK_CODES["VOLUME_DOWN"])
                time.sleep(0.02)
                press_virtual_key(VK_CODES["VOLUME_DOWN"])
                return True, "Volume Down (-4%)", "🔉"

            elif action == "VOLUME_MUTE":
                press_virtual_key(VK_CODES["VOLUME_MUTE"])
                return True, "Mute / Unmute Audio", "🔇"

            elif action == "MEDIA_NEXT_TRACK":
                press_virtual_key(VK_CODES["MEDIA_NEXT_TRACK"])
                return True, "Next Track", "⏭️"

            elif action == "MEDIA_PREV_TRACK":
                press_virtual_key(VK_CODES["MEDIA_PREV_TRACK"])
                return True, "Previous Track", "⏮️"

            elif action == "SHOW_DESKTOP":
                # إظهار سطح المكتب وإخفاء كافة النوافذ (Win + D)
                press_hotkey_combo([VK_CODES["LWIN"], VK_CODES["D"]])
                return True, "Show Desktop (Win+D)", "🖥️"

            elif action == "TAKE_SCREENSHOT":
                # أداة لقطة الشاشة في ويندوز (Win + Shift + S)
                press_hotkey_combo([VK_CODES["LWIN"], VK_CODES["SHIFT"], VK_CODES["S"]])
                return True, "Snipping Tool (Win+Shift+S)", "📸"

            elif action == "LOCK_PC":
                # قفل جهاز الكمبيوتر (Win + L)
                press_hotkey_combo([VK_CODES["LWIN"], VK_CODES["L"]])
                return True, "Lock Computer (Win+L)", "🔒"

            elif action == "TASK_SWITCH":
                # تبديل النوافذ (Alt + Tab)
                press_hotkey_combo([VK_CODES["MENU"], VK_CODES["TAB"]])
                return True, "Switch Task (Alt+Tab)", "🔀"

            else:
                print(f"[!] أمر غير معروف: {action}")
                return False, f"Unknown: {action}", "⚠️"

        except Exception as e:
            print(f"[X] خطأ أثناء تنفيذ الأمر {action}: {e}")
            return False, f"Error: {e}", "❌"
