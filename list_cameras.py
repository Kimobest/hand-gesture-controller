"""
====================================================================
 أداة فحص واختيار كاميرات النظام (Camera Device Explorer & Selector)
====================================================================
تتيح لك هذه الأداة:
1. فحص واكتشاف كافة كاميرات الويب المتصلة بجهازك (Camera Index 0, 1, 2...).
2. معاينة الصورة الحية من كل كاميرا لاختيار الكاميرا الصحيحة.
3. حفظ رقم الكاميرا المفضلة مباشرة في ملف config.py بنقرة واحدة.
====================================================================
"""

import os
import sys
import time
import re

# ضمان دعم الترميز UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
import cv2


def scan_cameras(max_tested=5):
    """فحص واكتشاف جميع الكاميرات المتاحة"""
    print("\n[*] جاري فحص الكاميرات المتصلة بالنظام...")
    cameras = []
    for i in range(max_tested):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                backend = cap.getBackendName()
                cameras.append({
                    "index": i,
                    "width": w,
                    "height": h,
                    "fps": int(fps) if fps > 0 else 30,
                    "backend": backend
                })
            cap.release()
    return cameras


def preview_camera(camera_index):
    """عرض معاينة فيديو حية لكاميرا معينة"""
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"[X] تعذر فتح الكاميرا رقم {camera_index} للمعاينة!")
        return

    win_name = f"Camera #{camera_index} Preview - Press [SPACE] or [Q] to close"
    cv2.namedWindow(win_name, cv2.WINDOW_AUTOSIZE)

    print(f"\n[📷] تم فتح معاينة الكاميرا #{camera_index}. اضغط [مسافة Space] أو [Q] للإغلاق.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.putText(frame, f"Camera #{camera_index} PREVIEW", (20, 35),
                    cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 128), 2, cv2.LINE_AA)
        cv2.putText(frame, "Press SPACE or Q to Close Preview", (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)

        cv2.imshow(win_name, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('Q') or key == 27 or key == 32:
            break

    cap.release()
    cv2.destroyWindow(win_name)


def set_config_camera(selected_index):
    """حفظ رقم الكاميرا المختار في ملف config.py"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py")
    if not os.path.exists(config_path):
        print(f"[X] لم يتم العثور على ملف: {config_path}")
        return False

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = re.sub(r'CAMERA_INDEX\s*=\s*\d+', f'CAMERA_INDEX = {selected_index}', content)

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"\n[✓] تم حفظ الكاميرا #{selected_index} ككاميرا افتراضية في config.py بنجاح!")
    return True


def main():
    print("=" * 70)
    print("      📷 أداة فحص واختيار كاميرات الساوند بورد (Camera Explorer) 📷")
    print("=" * 70)

    cameras = scan_cameras()

    if not cameras:
        print("\n[!] لم يتم العثور على أي كاميرا متصلة بالنظام!")
        input("\nاضغط Enter للخروج...")
        return

    print(f"\n[✓] تم العثور على {len(cameras)} كاميرا متصلة:")
    print("-" * 70)
    print(f"{'الرقم (ID)':<12} | {'الأبعاد (Resolution)':<22} | {'الواجهة (Backend)':<15}")
    print("-" * 70)
    for cam in cameras:
        res = f"{cam['width']}x{cam['height']} @ {cam['fps']}fps"
        print(f"[{cam['index']}] Camera #{cam['index']:<3} | {res:<22} | {cam['backend']:<15}")
    print("-" * 70)

    while True:
        print("\nالخيارات المتاحة:")
        print(" [P] معاينة كاميرا معينة (Preview Camera Live)")
        print(" [S] تعيين وحفظ الكاميرا الافتراضية في config.py")
        print(" [Q] خروج")

        choice = input("\nاختر خياراً [P / S / Q]: ").strip().upper()

        if choice == 'P':
            cam_input = input(f"أدخل رقم الكاميرا التي تريد معاينتها ({', '.join(str(c['index']) for c in cameras)}): ").strip()
            if cam_input.isdigit() and int(cam_input) in [c['index'] for c in cameras]:
                preview_camera(int(cam_input))
            else:
                print("[!] رقم كاميرا غير صحيح.")
        elif choice == 'S':
            cam_input = input(f"أدخل رقم الكاميرا التي تريد استخدامها ({', '.join(str(c['index']) for c in cameras)}): ").strip()
            if cam_input.isdigit() and int(cam_input) in [c['index'] for c in cameras]:
                set_config_camera(int(cam_input))
                break
            else:
                print("[!] رقم كاميرا غير صحيح.")
        elif choice == 'Q' or choice == '':
            print("[*] تم الخروج.")
            break
        else:
            print("[!] خيار غير معروف.")


if __name__ == "__main__":
    main()
