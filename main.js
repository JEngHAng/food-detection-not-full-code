"use strict";

const $ = (id) => document.getElementById(id);
// ใช้ var เพื่อให้มั่นใจว่าเรียกใช้งานได้จากทุกฟังก์ชัน
var piCapturedFilename = null; 

/** ── 1. ฟังก์ชันถ่ายภาพ (Capture) ── */
async function captureFromPi() {
    console.log("📸 เริ่มสั่งถ่ายภาพ...");
    showLoading(true, "กำลังบันทึกภาพจากกล้อง...");
    
    try {
        const res = await fetch("/api/capture", { method: "POST" });
        const data = await res.json();

        if (data.success) {
            const img = $("preview-img");
            // 1. หยุดภาพสดและโชว์ภาพนิ่งที่ถ่ายได้ทันที
            // เพิ่ม ?t= เพื่อป้องกัน Browser จำภาพเก่า (Cache)
            img.src = data.image_url + "?t=" + new Date().getTime();
            
            // 2. เก็บชื่อไฟล์ไว้ในตัวแปรเพื่อส่งไปตรวจจับ
            piCapturedFilename = data.filename; 
            
            console.log("✅ ถ่ายสำเร็จ ไฟล์ชื่อ:", piCapturedFilename);
            showToast("📸 ถ่ายภาพสำเร็จ! ตรวจสอบภาพแล้วกดเริ่มตรวจจับ", "success");
        } else {
            showToast("❌ ถ่ายภาพล้มเหลว: " + (data.error || "Unknown"), "error");
        }
    } catch (err) {
        console.error("Capture Error:", err);
        showToast("❌ เชื่อมต่อกล้องไม่ได้", "error");
    }
    showLoading(false);
}

/** ── 2. ฟังก์ชันตรวจจับ (Detection) ── */
async function startDetection() {
    console.log("🚀 กำลังส่งภาพไปวิเคราะห์ AI...");
    
    if (!piCapturedFilename) {
        showToast("⚠️ ต้องถ่ายภาพก่อนเริ่มตรวจจับครับ", "error");
        return;
    }

    showLoading(true, "AI กำลังวิเคราะห์อาหารและคำนวณราคา...");
    try {
        const res = await fetch("/api/detect-captured", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename: piCapturedFilename })
        });

        const data = await res.json();
        if (data.success) {
            // ✅ แสดงผลลัพธ์ลงใน Result Screen
            renderResult(data); 
            showScreen("result-screen");
        } else {
            showToast("❌ วิเคราะห์ล้มเหลว: " + data.error, "error");
        }
    } catch (err) {
        console.error("Detection Error:", err);
        showToast("❌ การเชื่อมต่อล้มเหลว", "error");
    }
    showLoading(false);
}

/** ── 3. ฟังก์ชันแสดงผลลัพธ์ (Render) ── */
function renderResult(data) {
    // โชว์ภาพที่วาดกรอบแล้ว (Annotated Image)
    const ri = $("result-img");
    if (ri) ri.src = data.annotated_image || "";

    // โชว์รายการอาหาร
    const list = $("menu-list");
    if (list) {
        const dishes = data.dishes || [];
        if (dishes.length === 0) {
            list.innerHTML = `<div style="text-align:center;padding:20px;color:#64748b;">ไม่พบรายการอาหาร</div>`;
        } else {
            list.innerHTML = dishes.map((dish) => `
                <div class="menu-card" style="background:#6d28d9; border-radius:10px; padding:15px; margin-bottom:10px; color:white; display:flex; justify-content:space-between;">
                    <span style="font-weight:600;">${dish.name_th || dish.name}</span>
                    <span>฿${Math.round(dish.price)}</span>
                </div>
            `).join("");
        }
    }
    // โชว์ราคาทั้งหมด
    const totalPrice = $("total-price-display");
    if (totalPrice) totalPrice.textContent = Math.round(data.total_price || 0);
}

/** ── 4. จัดการหน้าจอและ Helper ── */
function showScreen(id) {
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    $(id).classList.add("active");
}

function goHome() {
    piCapturedFilename = null;
    const img = $("preview-img");
    if (img) img.src = "/video_feed"; // กลับไปโชว์ภาพสด
    showScreen("home-screen");
}

function showLoading(show, text = "") {
    const el = $("loading-overlay");
    if (el) {
        if (text) $("loader-text").textContent = text;
        el.classList.toggle("show", show);
    }
}

function showToast(msg, type = "") {
    const el = $("toast");
    if (el) {
        el.textContent = msg;
        el.className = `show ${type}`;
        setTimeout(() => el.className = "", 3000);
    }
}

// เริ่มต้นระบบเมื่อโหลดหน้าเสร็จ
window.onload = () => {
    console.log("✅ ระบบหน้าจอพร้อมใช้งาน");
    const uploadRow = $("upload-row");
    if (uploadRow) uploadRow.style.setProperty("display", "flex", "important");
    const detectBtn = $("detect-btn");
    if (detectBtn) {
        detectBtn.style.display = "block";
        detectBtn.disabled = false;
    }
};
