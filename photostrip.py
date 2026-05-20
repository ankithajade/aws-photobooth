"""
AI Photo Booth — photostrip.py
========================
Standalone photostrip capture mode.

Features:
  - Live webcam feed (landscape 4:3, selfie-mirrored)
  - 3 selectable strip templates with visual gallery
  - 4-photo capture sequence with countdown + flash
  - Overlay compositing (photos as background, template on top)
  - S3 upload (PNG + mobile-friendly HTML share page)
  - QR code generation pointing to HTML share page
"""

import threading
import time
import traceback
import base64
from io import BytesIO

import av
import boto3
import cv2
import numpy as np
import qrcode
import streamlit as st
from PIL import Image
from streamlit_webrtc import WebRtcMode, webrtc_streamer, VideoHTMLAttributes

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be the FIRST Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Photostrip Booth",
    page_icon="🎞️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — Global styles, flash animation, gallery cards, buttons
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #08080f; }
h1,h2,h3,h4 { color: #f0f0f5; }
p, li { color: #b0b0c0; }

/* ── flash overlay on capture ── */
@keyframes flash-animation {
    0% { opacity: 0; }
    10% { opacity: 1; }
    100% { opacity: 0; }
}
.flash-active {
    position: fixed;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    background-color: rgba(255, 255, 255, 0.95);
    z-index: 99999;
    pointer-events: none;
    animation: flash-animation 0.4s ease-out forwards;
}

/* ── video element ── */
video {
    border-radius: 12px;
    max-height: 430px;
    width: 100% !important;
    object-fit: contain;
    background: #000;
}

/* ── buttons ── */
.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    transition: all .15s ease;
}
.stButton > button:hover { transform: translateY(-2px); opacity: .86; }

button[kind="primary"], .primary-btn button {
    background: linear-gradient(135deg,#6c63ff,#e044ab) !important;
    color: white !important;
    border: none !important;
    padding: .75rem !important;
    font-size: 1.05rem !important;
    width: 100%;
}

.reset-btn > button {
    background: transparent !important;
    border: 1.5px solid #444 !important;
    color: #999 !important;
    width: 100%;
}

/* ── strip gallery thumbnail card ── */
.strip-card {
    border-radius: 12px;
    border: 2.5px solid transparent;
    padding: 8px;
    text-align: center;
    background: #12121e;
    transition: all .25s ease;
    cursor: pointer;
    margin-bottom: 4px;
}
.strip-card:hover {
    border-color: rgba(224, 68, 171, 0.3);
    box-shadow: 0 0 10px rgba(224, 68, 171, 0.2);
}
.strip-card.selected {
    border-color: #e044ab;
    box-shadow: 0 0 18px rgba(224, 68, 171, 0.5),
                inset 0 0 6px rgba(224, 68, 171, 0.15);
}

/* ── result image ── */
.stImage img { border-radius: 14px; }

/* ── divider ── */
hr { border-color: #1e1e2e !important; }

/* ── countdown text ── */
.countdown-text {
    font-size: 3rem;
    font-weight: 800;
    text-align: center;
    color: #e044ab;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# AWS CLIENTS
# ─────────────────────────────────────────────────────────────────────────────

_KEY    = "AKIAWWJIEP3GN5ZFX3RS"
_SECRET = "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"
_REGION = "ap-south-1"
S3_BUCKET = "vignanotsava-photo-booth"

s3 = boto3.client(
    "s3", aws_access_key_id=_KEY,
    aws_secret_access_key=_SECRET, region_name=_REGION,
)

# ─────────────────────────────────────────────────────────────────────────────
# STRIP TEMPLATE REGISTRY
#
# Each template defines:
#   name  — display label for the gallery
#   path  — PNG file with transparent cutouts for photo placement
#   slots — bounding boxes (x, y, w, h) for the 4 photo regions
#
# All templates share the same canvas size: 736 × 1308.
# ─────────────────────────────────────────────────────────────────────────────

STRIP_TEMPLATES = {
    "strip-1": {
        "name": "Retro Event",
        "path": "assets/strip-1.png",
        "slots": [
            {"x": 186, "y":  27, "w": 373, "h": 289},
            {"x": 183, "y": 329, "w": 376, "h": 291},
            {"x": 182, "y": 633, "w": 377, "h": 296},
            {"x": 179, "y": 942, "w": 380, "h": 296},
        ]
    },
    "strip-2": {
        "name": "Neon Party",
        "path": "assets/strip-2.png",
        "slots": [
            {"x": 180, "y":  41, "w": 376, "h": 280},
            {"x": 180, "y": 354, "w": 376, "h": 281},
            {"x": 179, "y": 670, "w": 375, "h": 281},
            {"x": 180, "y": 983, "w": 376, "h": 281},
        ]
    },
    "strip-3": {
        "name": "Classic Film",
        "path": "assets/strip-3.png",
        "slots": [
            {"x": 206, "y":  60, "w": 357, "h": 246},
            {"x": 206, "y": 319, "w": 357, "h": 246},
            {"x": 207, "y": 575, "w": 356, "h": 264},
            {"x": 207, "y": 852, "w": 357, "h": 237},
        ]
    },
}

TARGET_RATIO = 4 / 3  # Standard landscape 4:3 webcam aspect ratio

# ─────────────────────────────────────────────────────────────────────────────
# IMAGE FILTERS
# ─────────────────────────────────────────────────────────────────────────────

def apply_bw_filter(img: np.ndarray) -> np.ndarray:
    """High-quality grayscale conversion with slightly boosted contrast."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=1.1, beta=-5)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

# Precompute LUT for Vintage filter for maximum performance (0 overhead at 30fps)
_VINTAGE_LUT = np.zeros((256, 1, 3), dtype=np.uint8)
for i in range(256):
    # compress contrast / fade
    val = (i * 0.9) + 15
    b = min(255, max(0, val * 0.8))   # Less blue
    g = min(255, max(0, val * 1.0))
    r = min(255, max(0, val * 1.2))   # More red (warm)
    _VINTAGE_LUT[i, 0, 0] = int(b)
    _VINTAGE_LUT[i, 0, 1] = int(g)
    _VINTAGE_LUT[i, 0, 2] = int(r)

def apply_vintage_filter(img: np.ndarray) -> np.ndarray:
    """Warm nostalgic tones, faded film look using a precomputed LUT."""
    return cv2.LUT(img, _VINTAGE_LUT)

# ─────────────────────────────────────────────────────────────────────────────
# VIDEO PROCESSOR — crops webcam feed to 4:3 landscape, selfie-mirrored
# ─────────────────────────────────────────────────────────────────────────────

class StripVideoProcessor:
    """Crop webcam feed to 4:3 landscape ratio with selfie-mirror and live filters."""

    def __init__(self):
        self.frame_bgr = None
        self._lock = threading.Lock()
        self.filter_mode = "color"

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)  # selfie mirror
        h, w = img.shape[:2]
        ratio = w / h

        if ratio > TARGET_RATIO:
            cw = int(h * TARGET_RATIO)
            x0 = (w - cw) // 2
            cropped = img[:, x0:x0 + cw]
        else:
            ch = int(w / TARGET_RATIO)
            y0 = (h - ch) // 2
            cropped = img[y0:y0 + ch, :]

        # Apply selected filter to the cropped preview (and inherently the capture)
        mode = getattr(self, "filter_mode", "color")
        if mode == "bw":
            cropped = apply_bw_filter(cropped)
        elif mode == "vintage":
            cropped = apply_vintage_filter(cropped)

        with self._lock:
            self.frame_bgr = cropped

        return av.VideoFrame.from_ndarray(cropped, format="bgr24")

# ─────────────────────────────────────────────────────────────────────────────
# IMAGE PROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def fit_cover(image: Image.Image, tw: int, th: int) -> Image.Image:
    """Scale + center-crop *image* to exactly (tw × th) — 'cover' mode."""
    sw, sh = image.size
    if (sw / sh) > (tw / th):
        nw, nh = int(sw * th / sh), th
    else:
        nw, nh = tw, int(sh * tw / sw)
    r = image.resize((nw, nh), Image.LANCZOS)
    l, t = (nw - tw) // 2, (nh - th) // 2
    return r.crop((l, t, l + tw, t + th))


@st.cache_resource
def _load_template(template_path: str) -> Image.Image:
    """Cache-load a strip template PNG to avoid repeated disk I/O."""
    return Image.open(template_path).convert("RGBA")


def create_photostrip(photos: list, template_id: str) -> Image.Image:
    """
    Compositing pipeline:
      1. Create a black background canvas matching template dimensions.
      2. Paste the 4 captured photos into each slot (fit-cover).
      3. Alpha-composite the template PNG ON TOP (decorative overlay).
    """
    cfg = STRIP_TEMPLATES.get(template_id, STRIP_TEMPLATES["strip-1"])
    template_img = _load_template(cfg["path"])
    tw, th = template_img.size

    # Background canvas
    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 255))

    # Paste photos into slots
    for i, photo in enumerate(photos):
        if i >= len(cfg["slots"]):
            break
        s = cfg["slots"][i]
        fitted = fit_cover(photo, s["w"], s["h"])
        canvas.paste(fitted.convert("RGB"), (s["x"], s["y"]))

    # Overlay template on top
    return Image.alpha_composite(canvas, template_img)


@st.cache_resource
def _load_gallery_thumb(path: str) -> Image.Image:
    """Cache-load and downscale a strip template thumbnail for the gallery."""
    thumb = Image.open(path).convert("RGBA")
    thumb.thumbnail((140, 240), Image.Resampling.LANCZOS)
    return thumb

# ─────────────────────────────────────────────────────────────────────────────
# MOBILE SHARE PAGE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_share_page(image_url: str) -> str:
    """Build a dark-themed, responsive HTML page for mobile share & download."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Photostrip Capture</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
    body {{
      margin: 0; padding: 20px;
      background: #08080f; color: #f0f0f5;
      font-family: 'Inter', sans-serif;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      min-height: 100vh; box-sizing: border-box;
    }}
    .container {{
      max-width: 480px; width: 100%; text-align: center;
      background: rgba(18,18,30,0.6); backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.05);
      border-radius: 20px; padding: 24px;
      box-shadow: 0 15px 35px rgba(0,0,0,0.5);
    }}
    h1 {{
      font-size: 1.8rem; font-weight: 800; margin: 0 0 8px;
      background: linear-gradient(135deg,#6c63ff,#e044ab);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }}
    p {{ color: #b0b0c0; font-size: .95rem; margin-bottom: 24px; }}
    .image-preview {{
      width: 100%; border-radius: 12px; overflow: hidden;
      margin-bottom: 24px; box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      border: 2px solid rgba(255,255,255,0.1);
      display: flex; justify-content: center; background: #000;
    }}
    .image-preview img {{
      max-height: 55vh; width: auto;
      object-fit: contain; display: block;
    }}
    .btn {{
      display: flex; align-items: center; justify-content: center;
      gap: 8px; width: 100%; padding: 14px; border-radius: 12px;
      font-size: 1rem; font-weight: 600; border: none; cursor: pointer;
      margin-bottom: 12px; transition: all .2s ease;
      box-sizing: border-box; text-decoration: none;
    }}
    .btn-share {{ background: linear-gradient(135deg,#6c63ff,#e044ab); color: white; }}
    .btn-download {{ background: linear-gradient(135deg,#11998e,#38ef7d); color: white; }}
    .btn:active {{ transform: scale(0.98); }}
    .footer {{ margin-top: 24px; font-size: .8rem; color: #555; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>📸 Photostrip Saved!</h1>
    <p>Your photostrip memory is ready.</p>
    <div class="image-preview">
      <img id="booth-img" src="{image_url}" alt="Photostrip Capture">
    </div>
    <button class="btn btn-share" id="share-btn">📤 Share Photostrip</button>
    <a href="{image_url}" download="photostrip_capture.png" class="btn btn-download" id="download-btn">
      📥 Download Photostrip
    </a>
    <div class="footer">Powered by AI Photo Booth</div>
  </div>
  <script>
    const shareBtn = document.getElementById('share-btn');
    const imageUrl = "{image_url}";
    shareBtn.addEventListener('click', async () => {{
      if (navigator.share) {{
        try {{
          const r = await fetch(imageUrl);
          const blob = await r.blob();
          const file = new File([blob], 'photo.png', {{ type: 'image/png' }});
          if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
            await navigator.share({{ files: [file], title: 'My Photostrip', text: 'Check out my photostrip!' }});
            return;
          }}
        }} catch (e) {{ console.log("File share failed:", e); }}
        try {{
          await navigator.share({{ title: 'My Photostrip', text: 'Check out my photostrip!', url: window.location.href }});
        }} catch (e) {{ console.log("URL share failed:", e); }}
      }} else {{
        alert("Native sharing is not supported. Use the download button instead.");
      }}
    }});
  </script>
</body>
</html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# S3 UPLOAD HELPER
# ─────────────────────────────────────────────────────────────────────────────

def upload_to_s3(img_bytes: bytes) -> tuple[str, str | None]:
    """
    Upload the photostrip PNG + a companion HTML share page to S3.

    Returns:
        (photo_url, error_message)
        photo_url — URL of the HTML share page, or "#" on failure.
        error_message — None on success, or a string describing the error.
    """
    ts = int(time.time())
    png_key  = f"photostrip_{ts}.png"
    html_key = f"photostrip_{ts}.html"

    try:
        # 1. Upload the PNG image
        s3.put_object(Bucket=S3_BUCKET, Key=png_key,
                      Body=img_bytes, ContentType="image/png")
        raw_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{png_key}"

        # 2. Generate and upload the HTML share page
        html_body = generate_share_page(raw_url)
        s3.put_object(Bucket=S3_BUCKET, Key=html_key,
                      Body=html_body.encode("utf-8"), ContentType="text/html")

        return f"https://{S3_BUCKET}.s3.amazonaws.com/{html_key}", None

    except Exception as exc:
        traceback.print_exc()
        return "#", str(exc)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULTS = {
    "mode":            "capture",   # "capture" | "result"
    "captured_photos": [],          # list[PIL.Image]
    "camera_run_id":   0,
    "final_strip":     None,
    "image_bytes":     None,
    "file_name":       None,
    "photo_url":       None,
    "is_capturing":    False,
    "selected_strip":  "strip-1",
    "selected_filter": "color",
    "upload_error":    None,
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────────────────────────────────────
# RESET HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _reset_session():
    """Reset all capture-related state for a new session."""
    st.session_state.camera_run_id += 1
    st.session_state.mode = "capture"
    st.session_state.captured_photos = []
    st.session_state.final_strip = None
    st.session_state.image_bytes = None
    st.session_state.file_name = None
    st.session_state.photo_url = None
    st.session_state.is_capturing = False
    st.session_state.upload_error = None

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    "<h1 style='text-align:center; font-size:2.4rem; margin-bottom:0;'>"
    "🎞️ <span style='background:linear-gradient(135deg,#6c63ff,#e044ab);"
    "-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>"
    "Photostrip Booth</span></h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center;color:#555;margin-top:4px;font-size:.9rem;'>"
    "Capture 4 photos · Choose your strip · Share instantly</p>",
    unsafe_allow_html=True,
)
st.divider()

# ═════════════════════════════════════════════════════════════════════════════
#  STATE 1 — BEFORE CAPTURE
# ═════════════════════════════════════════════════════════════════════════════

if st.session_state.mode == "capture":
    left, right = st.columns([3, 2], gap="large")

    # ── LEFT: Live Camera Feed ─────────────────────────────────────────────
    with left:
        st.markdown("#### 📷 Live Preview")
        ctx = webrtc_streamer(
            key=f"booth_{st.session_state.camera_run_id}",
            desired_playing_state=True,
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=StripVideoProcessor,
            media_stream_constraints={
                "video": {
                    "width": {"ideal": 1280},
                    "height": {"ideal": 720},
                    "frameRate": {"ideal": 30},
                },
                "audio": False,
            },
            async_processing=True,
            video_html_attrs=VideoHTMLAttributes(
                autoPlay=True, controls=False,
                style={
                    "maxHeight": "420px", "width": "auto", "maxWidth": "100%",
                    "borderRadius": "12px", "background": "#000",
                    "display": "block", "margin": "0 auto",
                },
                muted=True, playsInline=True,
            ),
        )
        
        if ctx.video_processor:
            ctx.video_processor.filter_mode = st.session_state.selected_filter

        st.divider()

        capture_ph = st.empty()
        status_ph  = st.empty()

        start_clicked = capture_ph.button(
            "🚀 Start Photostrip",
            key="start_capture", type="primary",
            use_container_width=True,
            disabled=st.session_state.is_capturing,
        )

        if start_clicked:
            if not ctx.video_processor:
                st.warning("Start the camera first!")
            elif ctx.video_processor.frame_bgr is None:
                st.warning("Waiting for camera feed…")
            else:
                st.session_state.is_capturing = True
                st.session_state.captured_photos = []
                st.rerun()

        # ── Capture sequence (blocking in main thread) ─────────────────────
        if st.session_state.is_capturing:
            capture_ph.empty()

            for photo_num in range(1, 5):
                for countdown in range(3, 0, -1):
                    status_ph.markdown(
                        f"<div class='countdown-text'>Photo {photo_num}/4<br>{countdown}…</div>",
                        unsafe_allow_html=True,
                    )
                    time.sleep(1)

                # Flash effect
                st.markdown("<div class='flash-active'></div>", unsafe_allow_html=True)
                status_ph.markdown(
                    "<div class='countdown-text' style='color:#fff;'>📸!</div>",
                    unsafe_allow_html=True,
                )

                # Grab frame
                with ctx.video_processor._lock:
                    frame_bgr = ctx.video_processor.frame_bgr.copy()
                frame_pil = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
                st.session_state.captured_photos.append(frame_pil)
                time.sleep(0.5)

            status_ph.markdown(
                "<div class='countdown-text' style='color:#38ef7d;'>Processing…</div>",
                unsafe_allow_html=True,
            )

            # Composite the photostrip
            final_strip = create_photostrip(
                st.session_state.captured_photos,
                st.session_state.selected_strip,
            )

            # Export to PNG bytes
            buf = BytesIO()
            final_strip.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            # Upload to S3
            photo_url, upload_err = upload_to_s3(img_bytes)
            if upload_err:
                st.error(f"S3 upload error: {upload_err}")

            # Commit results to session state
            st.session_state.final_strip  = final_strip
            st.session_state.image_bytes  = img_bytes
            st.session_state.file_name    = f"photostrip_{int(time.time())}.png"
            st.session_state.photo_url    = photo_url
            st.session_state.upload_error = upload_err
            st.session_state.mode         = "result"
            st.session_state.is_capturing = False
            st.rerun()

    # ── RIGHT: Strip Gallery + Capture Controls ────────────────────────────
    with right:
        st.markdown("#### 🎞️ Choose Your Strip")

        # Thumbnail gallery — 3 columns
        gallery_cols = st.columns(3)
        for idx, (strip_id, info) in enumerate(STRIP_TEMPLATES.items()):
            with gallery_cols[idx]:
                is_active = (st.session_state.selected_strip == strip_id)
                css_class = "selected" if is_active else ""

                # Render thumbnail inside a styled card
                thumb = _load_gallery_thumb(info["path"])
                
                # Convert PIL image to base64 for inline HTML rendering
                buf = BytesIO()
                thumb.save(buf, format="PNG")
                img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                
                html_card = f"""
                <div class="strip-card {css_class}">
                    <img src="data:image/png;base64,{img_b64}" style="width: 100%; border-radius: 6px; display: block;">
                </div>
                """
                st.markdown(html_card, unsafe_allow_html=True)

                # Selection button
                label = f"✅ {info['name']}" if is_active else info["name"]
                if st.button(label, key=f"sel_{strip_id}", use_container_width=True):
                    st.session_state.selected_strip = strip_id
                    st.rerun()

        st.divider()
        st.markdown("#### 🎨 Choose Filter")
        filter_cols = st.columns(3)
        
        filters = [
            ("color", "🎨 Color"),
            ("bw", "🖤 B&W"),
            ("vintage", "📼 Vintage")
        ]
        
        for idx, (f_id, f_name) in enumerate(filters):
            with filter_cols[idx]:
                is_sel = (st.session_state.selected_filter == f_id)
                if st.button(f_name, key=f"btn_flt_{f_id}", type="primary" if is_sel else "secondary", use_container_width=True):
                    st.session_state.selected_filter = f_id
                    st.rerun()

        st.divider()
        st.markdown("#### 🚀 Ready to Shoot?")
        st.info("This will take **4 photos** in a row with the selected strip template.")



# ═════════════════════════════════════════════════════════════════════════════
#  STATE 2 — AFTER CAPTURE (Result Screen)
# ═════════════════════════════════════════════════════════════════════════════

elif st.session_state.mode == "result":
    left, right = st.columns([2, 3], gap="large")

    # ── LEFT: Final Photostrip Preview ─────────────────────────────────────
    with left:
        st.markdown("#### 🎞️ Your Photostrip")
        # Display at 400px width — balanced size for laptop without overflow
        st.image(st.session_state.final_strip, width=400)

    # ── RIGHT: QR Code + Retake ────────────────────────────────────────────
    with right:
        url = st.session_state.photo_url
        if url and url != "#":
            st.markdown("#### 📱 Scan to Share & Download")
            qr_img = qrcode.make(url)
            qr_buf = BytesIO()
            qr_img.save(qr_buf, format="PNG")
            st.image(qr_buf.getvalue(), width=280)
            st.caption("Scan with your phone to share or download your photostrip!")
        else:
            st.info("Photo URL not available (S3 upload may have failed).")
            if st.session_state.upload_error:
                st.error(f"Error: {st.session_state.upload_error}")

        st.divider()

        # Retake button — positioned below QR in the right panel
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("🔄  Take Another Photo", key="reset", use_container_width=True):
            _reset_session()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
