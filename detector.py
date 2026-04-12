import uuid
import logging
import os
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO  # ✅ ต้องติดตั้ง pip install ultralytics

from config import MODEL_PATH, UPLOAD_DIR, MENU_PATH
from utils import load_menu

logger = logging.getLogger(__name__)

# ── สีของ bounding box ────────────────
BOX_COLORS_RGB = [(0, 229, 160), (0, 153, 255), (255, 107, 53), (176, 106, 255)]

# ── ฟอนต์ภาษาไทย ──────────────────────
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/tlwg/Loma.ttf",
    "/usr/share/fonts/truetype/thai/Garuda.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
]

def _find_thai_font(size: int = 20) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

class FoodDetector:
    def __init__(self):
        # 1. โหลดเมนูราคาจาก JSON
        self.menu = load_menu(MENU_PATH)
        self._font_label = _find_thai_font(size=22)
        
        # 2. โหลด YOLO Model (best.pt)
        self.model = None
        try:
            if os.path.exists(MODEL_PATH):
                # โหลดโมเดล (บน Pi 5 แนะนำให้ใช้ .pt หรือแปลงเป็น .engine/ncnn เพื่อความเร็ว)
                self.model = YOLO(MODEL_PATH)
                logger.info(f"✅ FoodDetector: Loaded model from {MODEL_PATH}")
            else:
                logger.error(f"❌ Model file NOT FOUND at {MODEL_PATH}")
        except Exception as e:
            logger.error(f"❌ Failed to load YOLO model: {e}")

    def detect(self, image_path: str) -> dict:
        """ตรวจจับอาหารด้วย Model YOLO จริง"""
        if not Path(image_path).exists():
            return {"success": False, "error": f"Image not found: {image_path}"}
        
        if self.model is None:
            return {"success": False, "error": "Model not initialized"}

        try:
            # 1. รันการตรวจจับ (Inference)
            # stream=False เพื่อรอผลลัพธ์, conf=0.4 คือค่าความมั่นใจขั้นต่ำ
            results = self.model.predict(image_path, conf=0.4, device='cpu')[0]
            
            pil_img = Image.open(image_path).convert("RGB")
            detections = []
            total_price = 0

            # 2. ประมวลผลผลลัพธ์แต่ละ Object ที่เจอ
            for i, box in enumerate(results.boxes):
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                label_en = results.names[cls_id] # ชื่อ class ภาษาอังกฤษที่เทรนมา
                
                # ดึงข้อมูลจาก menu.json ตามชื่อ class
                item = self.menu.get(label_en, {"name_th": label_en, "price": 0})
                
                # พิกัด Bounding Box [x1, y1, x2, y2]
                b = box.xyxy[0].cpu().numpy()
                det = {
                    "name": label_en,
                    "name_th": item.get("name_th", label_en),
                    "confidence": round(conf, 2),
                    "price": item.get("price", 0),
                    "bbox": {"x1": int(b[0]), "y1": int(b[1]), "x2": int(b[2]), "y2": int(b[3])},
                }

                detections.append(det)
                total_price += det["price"]

                # วาดกรอบและภาษาไทยลงบนภาพ
                self._draw_box_pil(pil_img, det, i)

            # 3. บันทึกภาพที่วาดกรอบแล้ว
            p = Path(image_path)
            annotated_path = str(p.parent / f"annotated_{p.name}")
            pil_img.save(annotated_path, "JPEG", quality=95)

            return {
                "success": True,
                "detections": detections,
                "total_price": total_price,
                "annotated_path": annotated_path,
                "count": len(detections)
            }

        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return {"success": False, "error": str(e)}

    def _draw_box_pil(self, img, det, idx):
        color = BOX_COLORS_RGB[idx % len(BOX_COLORS_RGB)]
        b = det["bbox"]
        draw = ImageDraw.Draw(img)
        
        # วาดกรอบ
        draw.rectangle([b["x1"], b["y1"], b["x2"], b["y2"]], outline=color, width=5)
        
        # วาดพื้นหลังข้อความ
        label_text = f"{det['name_th']} {int(det['confidence']*100)}%"
        text_bbox = draw.textbbox((b["x1"], b["y1"]), label_text, font=self._font_label)
        draw.rectangle([text_bbox[0], text_bbox[1]-5, text_bbox[2]+10, text_bbox[3]+5], fill=color)
        
        # วาดข้อความภาษาไทย (สีขาว)
        draw.text((b["x1"] + 5, b["y1"] - 30), label_text, font=self._font_label, fill=(255, 255, 255))