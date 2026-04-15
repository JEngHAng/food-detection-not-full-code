import logging
import uuid
import os
import subprocess
import shutil
from pathlib import Path
from config import UPLOAD_DIR

logger = logging.getLogger(__name__)

class PiCamera:
    def __init__(self):
        # ล้างโปรเซสเก่า
        os.system("sudo pkill -9 rpicam")
        os.system("sudo pkill -9 libcamera")
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR, exist_ok=True)
        logger.info("✅ PiCamera (rpicam mode) Ready")

    def get_frame(self):
        """ดึงภาพสดลง RAM Disk"""
        try:
            cmd = ["rpicam-still", "-t", "1", "--width", "640", "--height", "480", 
                   "-e", "jpg", "-o", "/dev/shm/live.jpg", "--immediate", "--nopreview"]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists("/dev/shm/live.jpg"):
                with open("/dev/shm/live.jpg", "rb") as f:
                    return f.read()
            return None
        except Exception:
            return None

    def capture(self) -> str | None:
        """ก๊อปปี้เฟรมล่าสุดจาก RAM มาเป็นภาพนิ่ง"""
        try:
            filename = f"capture_{uuid.uuid4().hex}.jpg"
            path = str(UPLOAD_DIR / filename)
            live_image = "/dev/shm/live.jpg"
            
            if os.path.exists(live_image):
                shutil.copy2(live_image, path)
                logger.info(f"📸 บันทึกภาพสำเร็จ: {filename}")
                return path
            return None
        except Exception as exc:
            logger.error(f"Capture failed: {exc}")
            return None
