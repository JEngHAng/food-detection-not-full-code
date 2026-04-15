"use strict";

if (typeof getEl === 'undefined') {
    var getEl = (id) => document.getElementById(id);
}

var piCapturedFilename = null; 
var lastDetectionData = null; // ✅ เพิ่มเพื่อเก็บข้อมูล AI ล่าสุดไว้บันทึก

/** ── 1. ถ่ายภาพ ── */
async function captureFromPi() {
    showLoading(true, "กำลังบันทึกภาพจากกล้อง...");
    try {
        const res = await fetch("/api/capture", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            const img = getEl("preview-img");
            if (img) {
                img.src = data.image_url; 
                img.style.display = "block";
            }
            piCapturedFilename = data.filename; 
            showToast("📸 ถ่ายภาพสำเร็จ!", "success");
        }
    } catch (err) { console.error(err); }
    showLoading(false);
}

/** ── 2. ตรวจจับ (Detection) ── */
async function startDetection() {
    if (!piCapturedFilename) {
        showToast("⚠️ ต้องถ่ายภาพก่อนครับ", "error");
        return;
    }
    showLoading(true, "AI กำลังวิเคราะห์อาหาร...");
    try {
        const res = await fetch("/api/detect-captured", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename: piCapturedFilename })
        });
        const data = await res.json();
        if (data.success) {
            lastDetectionData = data; // ✅ เก็บข้อมูลไว้ส่งไปบันทึกตอนกดยืนยัน
            renderResult(data); 
            showScreen("result-screen");
        }
    } catch (err) { console.error(err); }
    showLoading(false);
}

/** ── 3. ยืนยันและบันทึกข้อมูล (goToEnd) ── */
async function goToEnd() {
    if (!piCapturedFilename || !lastDetectionData) {
        showToast("❌ ไม่พบข้อมูลการตรวจจับ", "error");
        return;
    }

    showLoading(true, "กำลังบันทึกลงฐานข้อมูล...");
    try {
        // ดึงค่าน้ำหนักปัจจุบันจากหน้าจอ
        const weightVal = parseFloat(getEl("weight-display")?.textContent || "0");
        
        const res = await fetch("/api/confirm", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                filename: piCapturedFilename,
                total_price: lastDetectionData.total_price,
                dishes: lastDetectionData.dishes,
                weight: weightVal
            })
        });

        const result = await res.json();
        if (result.success) {
            showScreen("end-screen");
            startCountdown(5); // นับถอยหลัง 5 วิกลับหน้าแรก
        } else {
            showToast("❌ บันทึกล้มเหลว", "error");
        }
    } catch (err) { 
        console.error(err);
        showToast("❌ ติดต่อเซิร์ฟเวอร์ไม่ได้", "error"); 
    }
    showLoading(false);
}

/** ── 4. แสดงผลลัพธ์ ── */
function renderResult(data) {
    const ri = getEl("result-img");
    if (ri) ri.src = data.annotated_image;
    const list = getEl("menu-list");
    if (list) {
        const dishes = data.dishes || [];
        list.innerHTML = dishes.map(dish => `
            <div class="menu-card" style="background:#6d28d9; border-radius:10px; padding:15px; margin-bottom:10px; color:white; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:600;">${dish.name_th || dish.name}</span>
                <span style="font-weight:bold;">฿${Math.round(dish.price)}</span>
            </div>
        `).join("");
    }
    const total = getEl("total-price-display");
    if (total) total.textContent = Math.round(data.total_price || 0);
}

/** ── ฟังก์ชันเสริม ── */
function startCountdown(seconds) {
    let n = seconds;
    const el = getEl("countdown-num");
    const timer = setInterval(() => {
        n--;
        if (el) el.textContent = n;
        if (n <= 0) { clearInterval(timer); goHome(); }
    }, 1000);
}

function showScreen(id) {
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    getEl(id)?.classList.add("active");
}

function goHome() {
    piCapturedFilename = null;
    lastDetectionData = null;
    const img = getEl("preview-img");
    if (img) img.src = "/video_feed"; 
    showScreen("home-screen");
}

function showLoading(show, text = "") {
    const el = getEl("loading-overlay");
    if (el) {
        if (text) getEl("loader-text").textContent = text;
        el.classList.toggle("show", show);
    }
}

function showToast(msg, type = "") {
    const el = getEl("toast");
    if (el) {
        el.textContent = msg;
        el.className = `show ${type}`;
        setTimeout(() => el.className = "", 3000);
    }
}

window.onload = () => { console.log("✅ ระบบพร้อมใช้งาน"); };