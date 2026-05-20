"""
AI Photo Booth — app.py
========================
Two-state UI:
  State 1 (before capture): live camera + frame gallery + capture button
  State 2 (after capture):  final photo + AI analysis + QR + download

Features:
  - Real-time frame overlay on live camera feed
  - Auto-detected transparent photo window per frame template
  - fit-cover compositing (no stretch, no black bars)
  - AWS Rekognition — up to 2 faces (emotion + age)
  - S3 upload + QR code + download
"""

import threading
import time
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
    page_title="AI Photo Booth",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #08080f; }
h1,h2,h3,h4 { color: #f0f0f5; }
p, li { color: #b0b0c0; }

/* ── video element ── */
video {
    border-radius: 12px;
    max-height: 430px;
    width: 100% !important;
    object-fit: contain;
    background: #000;
}

/* ── primary / capture button ── */
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

/* ── reset / secondary button ── */
.reset-btn > button {
    background: transparent !important;
    border: 1.5px solid #444 !important;
    color: #999 !important;
    width: 100%;
}

/* ── download button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg,#11998e,#38ef7d);
    color: white; border: none;
    border-radius: 10px; font-weight: 600; width: 100%;
}

/* ── frame gallery card ── */
.frame-thumb {
    border-radius: 10px;
    border: 2.5px solid transparent;
    padding: 6px;
    text-align: center;
    background: #12121e;
    transition: border .2s ease;
    cursor: pointer;
}
.frame-thumb.active {
    border-color: #6c63ff;
    box-shadow: 0 0 14px rgba(108,99,255,.45);
}

/* ── result image ── */
.stImage img { border-radius: 14px; }

/* ── divider ── */
hr { border-color: #1e1e2e !important; }

/* ── placeholder box ── */
.ph {
    border: 2px dashed #222;
    border-radius: 14px;
    padding: 60px 20px;
    text-align: center;
    color: #444;
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

rekognition = boto3.client(
    "rekognition", aws_access_key_id=_KEY,
    aws_secret_access_key=_SECRET, region_name=_REGION,
)
s3 = boto3.client(
    "s3", aws_access_key_id=_KEY,
    aws_secret_access_key=_SECRET, region_name=_REGION,
)

# ─────────────────────────────────────────────────────────────────────────────
# FRAME TEMPLATES REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

FRAME_REGISTRY = [
    {"id": "none",   "label": "No Frame",     "path": None},
    {"id": "frame1", "label": "Vignanotsava", "path": "assets/frame-1.png"},
    {"id": "frame2", "label": "Neon Tech",    "path": "assets/frame-2.png"},
    {"id": "frame3", "label": "Futuristic",   "path": "assets/frame-3.png"},
    {"id": "frame4", "label": "Cyber Matrix", "path": "assets/frame-4.png"},
    {"id": "frame5", "label": "Retro Arcade", "path": "assets/frame-5.png"},
    {"id": "frame6", "label": "Glow Circuit", "path": "assets/frame-6.png"},
]

# ─────────────────────────────────────────────────────────────────────────────
# FRAME RESOURCE LOADER  (cached — runs once per unique path)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def load_frame_resource(frame_path):
    """
    Return a dict with:
      window     — {x, y, w, h, ratio} of the transparent photo region
      frame_size — (W, H) of the full frame PNG
      overlay    — PIL RGBA image  (None for 'no frame')

    For the 'no frame' case we still return sensible dimensions so the
    VideoProcessor and compositor use a consistent canvas size.
    """
    FALLBACK_W, FALLBACK_H = 408, 612   # matches frame-1 canvas

    if frame_path is None:
        return {
            "window":     {"x": 0, "y": 0,
                           "w": FALLBACK_W, "h": FALLBACK_H,
                           "ratio": FALLBACK_W / FALLBACK_H},
            "frame_size": (FALLBACK_W, FALLBACK_H),
            "overlay":    None,
        }

    overlay = Image.open(frame_path).convert("RGBA")
    alpha   = np.array(overlay)[:, :, 3]
    mask    = alpha == 0

    row_idx = np.where(np.any(mask, axis=1))[0]
    col_idx = np.where(np.any(mask, axis=0))[0]

    if len(row_idx) == 0 or len(col_idx) == 0:
        W, H = overlay.size
        return {
            "window":     {"x": 0, "y": 0, "w": W, "h": H, "ratio": W / H},
            "frame_size": overlay.size,
            "overlay":    overlay,
        }

    top, bottom = int(row_idx[0]), int(row_idx[-1])
    left, right = int(col_idx[0]), int(col_idx[-1])
    pw = right - left + 1
    ph = bottom - top + 1

    return {
        "window":     {"x": left, "y": top, "w": pw, "h": ph, "ratio": pw / ph},
        "frame_size": overlay.size,
        "overlay":    overlay,
    }

# ─────────────────────────────────────────────────────────────────────────────
# IMAGE PROCESSING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def fit_cover(image: Image.Image, tw: int, th: int) -> Image.Image:
    """Scale + center-crop image to exactly (tw × th) — CSS object-fit:cover."""
    sw, sh = image.size
    if (sw / sh) > (tw / th):        # wider → fit height, crop sides
        nw, nh = int(sw * th / sh), th
    else:                             # taller → fit width, crop top/bottom
        nw, nh = tw, int(sh * tw / sw)

    r = image.resize((nw, nh), Image.LANCZOS)
    l, t = (nw - tw) // 2, (nh - th) // 2
    return r.crop((l, t, l + tw, t + th))


def composite(photo: Image.Image, res: dict) -> Image.Image:
    """
    Paste *photo* into the transparent window of the frame and
    alpha-composite the frame overlay on top.
    Returns a PIL RGBA image.
    """
    win = res["window"]
    fw, fh = res["frame_size"]

    bg = Image.new("RGBA", (fw, fh), (255, 255, 255, 255))
    fitted = fit_cover(photo.convert("RGBA"), win["w"], win["h"])
    bg.paste(fitted.convert("RGB"), (win["x"], win["y"]))
    bg = bg.convert("RGBA")

    if res["overlay"] is not None:
        return Image.alpha_composite(bg, res["overlay"])
    return bg


# ─────────────────────────────────────────────────────────────────────────────
# PREVIEW OVERLAY HELPER  (numpy, runs inside VideoProcessor thread)
# ─────────────────────────────────────────────────────────────────────────────

# Preview canvas scale relative to the full frame PNG.
# Targets ~290px wide canvas so the webrtc video stays compact on laptop screens.
PREVIEW_SCALE = 0.70          # 408×612  →  285×428

def build_preview_overlay(res: dict) -> tuple:
    """
    Pre-compute everything the VideoProcessor needs for one frame template.
    Returns (canvas_w, canvas_h, win_x, win_y, win_w, win_h, overlay_arr)

    IMPORTANT — channel order:
      PIL images are RGB.  OpenCV (and av.VideoFrame bgr24) is BGR.
      We store the overlay as BGRA so the numpy blend in recv() is correct.
    """
    fw, fh = res["frame_size"]
    win    = res["window"]

    cw = max(1, int(fw * PREVIEW_SCALE))
    ch = max(1, int(fh * PREVIEW_SCALE))

    wx = int(win["x"] * PREVIEW_SCALE)
    wy = int(win["y"] * PREVIEW_SCALE)
    ww = max(1, int(win["w"] * PREVIEW_SCALE))
    wh = max(1, int(win["h"] * PREVIEW_SCALE))

    if res["overlay"] is not None:
        # Resize overlay (PIL, RGBA = RGB order)
        ov_rgba = np.array(res["overlay"].resize((cw, ch), Image.LANCZOS))
        # Swap R↔B channels so it matches the BGR canvas in recv()
        # Result layout: [B, G, R, A]  (BGRA)
        ov_bgra = ov_rgba[:, :, [2, 1, 0, 3]].copy()
        
        # Pre-compute float values to avoid doing casts & divisions 30 times/sec in the loop
        alpha_f = ov_bgra[:, :, 3:4].astype(np.float32) / 255.0
        frame_bgr = ov_bgra[:, :, :3].astype(np.float32)
        ov = (frame_bgr, alpha_f)
    else:
        ov = None

    return cw, ch, wx, wy, ww, wh, ov


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO PROCESSOR
# ─────────────────────────────────────────────────────────────────────────────

class VideoProcessor:
    """
    Crops the webcam feed to the frame's photo-window aspect ratio,
    renders a real-time frame overlay on the live preview, and stores
    the full-resolution portrait for capture.
    """

    def __init__(self):
        self.portrait   = None          # full-res BGR portrait for capture
        self._lock      = threading.Lock()
        self._cw = self._ch = 300
        self._wx = self._wy = 0
        self._ww = self._wh = 300
        self._overlay   = None          # RGBA numpy array or None
        self._win_ratio = 300 / 423     # default; updated by set_template()

    def set_template(self, res: dict):
        """Call from the Streamlit main thread when the user picks a frame."""
        cw, ch, wx, wy, ww, wh, ov = build_preview_overlay(res)
        with self._lock:
            self._cw, self._ch = cw, ch
            self._wx, self._wy = wx, wy
            self._ww, self._wh = ww, wh
            self._overlay      = ov
            self._win_ratio    = res["window"]["ratio"]

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)          # mirror (selfie mode)
        h, w = img.shape[:2]

        with self._lock:
            ratio   = self._win_ratio
            cw, ch  = self._cw, self._ch
            wx, wy  = self._wx, self._wy
            ww, wh  = self._ww, self._wh
            overlay = self._overlay

        # ── Crop webcam to the frame window's aspect ratio ────────────────
        # Handles both landscape and portrait camera feeds dynamically
        feed_ratio = w / h
        if feed_ratio > ratio:
            # Camera feed is wider than target ratio → crop sides (width)
            crop_w = int(h * ratio)
            x1 = (w - crop_w) // 2
            portrait_bgr = img[:, x1: x1 + crop_w]
        else:
            # Camera feed is taller than target ratio → crop top/bottom (height)
            crop_h = int(w / ratio)
            y1 = (h - crop_h) // 2
            portrait_bgr = img[y1: y1 + crop_h, :]

        self.portrait = portrait_bgr   # store full-res for capture

        # ── Build preview canvas (white bg, frame dimensions) ─────────────
        canvas = np.full((ch, cw, 3), 255, dtype=np.uint8)
        thumb  = cv2.resize(portrait_bgr, (ww, wh), interpolation=cv2.INTER_LINEAR)

        y2 = min(wy + wh, ch)
        x2 = min(wx + ww, cw)
        canvas[wy:y2, wx:x2] = thumb[:y2 - wy, :x2 - wx]

        # ── Alpha-blend the frame overlay on top ──────────────────────────
        # overlay contains pre-computed float values (frame_bgr, alpha_f),
        # avoiding slow per-frame image allocations and CPU divisions.
        if overlay is not None:
            frame_bgr, alpha_f = overlay
            canvas = (frame_bgr * alpha_f + canvas.astype(np.float32) * (1.0 - alpha_f)).astype(np.uint8)

        return av.VideoFrame.from_ndarray(canvas, format="bgr24")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE  (initialised once)
# ─────────────────────────────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "captured":      False,
        "frame_id":      "frame1",      # selected frame template id
        "camera_run_id": 0,
        "final_image":   None,          # PIL image after capture
        "image_bytes":   None,
        "file_name":     None,
        "photo_url":     None,
        "rek_faces":     [],            # list of face dicts from Rekognition
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    "<h1 style='text-align:center;"
    "background:linear-gradient(135deg,#6c63ff,#e044ab);"
    "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
    "font-size:2.4rem;margin-bottom:0;'>📸 AI Photo Booth</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center;color:#555;margin-top:4px;font-size:.9rem;'>"
    "Crafted by Ankitha Jade and Sadhana S</p>",
    unsafe_allow_html=True,
)
st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS — load selected frame resource
# ─────────────────────────────────────────────────────────────────────────────

def _selected_entry():
    for f in FRAME_REGISTRY:
        if f["id"] == st.session_state.frame_id:
            return f
    return FRAME_REGISTRY[0]


def _selected_res():
    entry = _selected_entry()
    return load_frame_resource(entry["path"])


# ─────────────────────────────────────────────────────────────────────────────
# ══════════════════════  STATE 1 — BEFORE CAPTURE  ═══════════════════════════
# ─────────────────────────────────────────────────────────────────────────────

if not st.session_state.captured:

    left, right = st.columns([3, 2], gap="large")

    # ── LEFT: live camera + capture button ──────────────────────────────────
    with left:
        st.markdown("#### 📷 Live Preview")

        ctx = webrtc_streamer(
            key=f"booth_{st.session_state.camera_run_id}",
            desired_playing_state=True,
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=VideoProcessor,
            media_stream_constraints={
                "video": {
                    "width": {"ideal": 1080},   # Request portrait orientation as ideal
                    "height": {"ideal": 1920},
                    "frameRate": {"ideal": 30}
                },
                "audio": False
            },
            async_processing=True,
            # video_html_attrs must be a VideoHTMLAttributes object.
            # In React, the 'style' attribute MUST be a dictionary (camelCased keys).
            # Passing a string causes Minified React Error #62.
            video_html_attrs=VideoHTMLAttributes(
                autoPlay=True,
                controls=False,
                style={
                    "maxHeight": "420px",
                    "width": "auto",
                    "maxWidth": "100%",
                    "borderRadius": "12px",
                    "background": "#000",
                    "display": "block",
                    "margin": "0 auto"
                },
                muted=True,
                playsInline=True
            ),
        )

        # Sync selected frame template to the VideoProcessor
        if ctx.video_processor:
            res = _selected_res()
            ctx.video_processor.set_template(res)

        st.divider()

        # ── Capture button (moved below camera) ─────────────────────────────
        capture_clicked = st.button(
            "📸  Capture Photo",
            key="capture",
            type="primary",
            use_container_width=True,
        )

        if capture_clicked:
            if not ctx.video_processor:
                st.warning("Start the camera first, then click Capture.")
            elif ctx.video_processor.portrait is None:
                st.warning("No frame captured yet — wait a moment and try again.")
            else:
                with st.spinner("Processing…"):

                    portrait_bgr = ctx.video_processor.portrait
                    portrait_rgb = cv2.cvtColor(portrait_bgr, cv2.COLOR_BGR2RGB)
                    portrait_pil = Image.fromarray(portrait_rgb)

                    res = _selected_res()

                    # ── Rekognition ────────────────────────────────────
                    rek_buf = BytesIO()
                    portrait_pil.save(rek_buf, format="JPEG", quality=90)
                    try:
                        rek = rekognition.detect_faces(
                            Image={"Bytes": rek_buf.getvalue()},
                            Attributes=["ALL"],
                        )
                        faces = rek.get("FaceDetails", [])[:2]   # max 2
                    except Exception as e:
                        faces = []
                        st.error(f"Rekognition error: {e}")

                    # ── Composite photo into frame ──────────────────────
                    final_img = composite(portrait_pil, res)

                    # ── Encode to PNG bytes ────────────────────────────
                    buf = BytesIO()
                    final_img.save(buf, format="PNG")
                    img_bytes = buf.getvalue()

                    # ── Upload to S3 ───────────────────────────────────
                    ts        = int(time.time())
                    file_name = f"photo_{ts}.png"
                    photo_url = "#"
                    try:
                        s3.put_object(
                            Bucket=S3_BUCKET, Key=file_name,
                            Body=img_bytes,   ContentType="image/png",
                        )
                        photo_url = (
                            f"https://{S3_BUCKET}.s3.amazonaws.com/{file_name}"
                        )
                    except Exception as e:
                        st.error(f"S3 upload error: {e}")

                    # ── Store in session state → trigger State 2 ───────
                    st.session_state.captured    = True
                    st.session_state.final_image = final_img
                    st.session_state.image_bytes = img_bytes
                    st.session_state.file_name   = file_name
                    st.session_state.photo_url   = photo_url
                    st.session_state.rek_faces   = faces

                st.rerun()

    # ── RIGHT: frame gallery ──────────────────────────────────────────────
    with right:

        # ── Frame gallery ──────────────────────────────────────────────
        st.markdown("#### 🖼️ Choose a Frame")

        # Render in a compact 4-column grid to fit all frames on screen without scrolling
        cols_per_row = 4
        for row_idx in range(0, len(FRAME_REGISTRY), cols_per_row):
            row_entries = FRAME_REGISTRY[row_idx : row_idx + cols_per_row]
            gallery_cols = st.columns(cols_per_row)
            for col_idx, entry in enumerate(row_entries):
                with gallery_cols[col_idx]:
                    # Thumbnail image
                    if entry["path"]:
                        thumb = Image.open(entry["path"]).convert("RGBA")
                        # Shrink thumbnail to fit without high memory usage or layout overflow
                        thumb.thumbnail((100, 150), Image.Resampling.LANCZOS)
                        # Compose on dark blue background
                        bg = Image.new("RGB", thumb.size, (20, 20, 30))
                        bg.paste(thumb, mask=thumb.split()[3])
                        st.image(bg, use_container_width=True)
                    else:
                        st.markdown(
                            "<div style='background:#12121e;border-radius:8px;"
                            "height:65px;display:flex;align-items:center;"
                            "justify-content:center;font-size:1.3rem;'>🚫</div>",
                            unsafe_allow_html=True,
                        )

                    # Select button  (highlight if active)
                    is_active = st.session_state.frame_id == entry["id"]
                    btn_label = f"✅ {entry['label']}" if is_active else entry["label"]
                    if st.button(btn_label, key=f"frame_btn_{entry['id']}",
                                 use_container_width=True):
                        st.session_state.frame_id = entry["id"]
                        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ══════════════════════  STATE 2 — AFTER CAPTURE  ════════════════════════════
# ─────────────────────────────────────────────────────────────────────────────

else:
    left, right = st.columns([2, 3], gap="large")

    # ── LEFT: final framed photo ───────────────────────────────────────────
    with left:
        st.markdown("#### 🖼️ Your Photo")
        st.image(
            st.session_state.final_image,
            use_container_width=True,
        )

        # Reset / take another photo
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("🔄  Take Another Photo", key="reset", use_container_width=True):
            st.session_state.camera_run_id += 1
            for k in ["captured", "final_image", "image_bytes",
                      "file_name", "photo_url", "rek_faces"]:
                st.session_state[k] = (
                    False if k == "captured" else
                    [] if k == "rek_faces" else None
                )
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── RIGHT: AI analysis + QR + download ────────────────────────────────
    with right:

        # ── AI Analysis ────────────────────────────────────────────────
        st.markdown("#### 🤖 AI Analysis")

        faces = st.session_state.rek_faces

        if not faces:
            st.info("No faces detected in the captured photo.")
        else:
            for i, face in enumerate(faces, start=1):
                top_emotion = max(face["Emotions"], key=lambda e: e["Confidence"])
                age_lo      = face["AgeRange"]["Low"]
                age_hi      = face["AgeRange"]["High"]
                confidence  = top_emotion["Confidence"]

                person_label = f"Person {i}" if len(faces) > 1 else "Detected Face"

                with st.container():
                    st.markdown(
                        f"<div style='background:#12121e;border-radius:14px;"
                        f"padding:16px 20px;margin-bottom:12px;'>"
                        f"<p style='color:#6c63ff;font-weight:700;"
                        f"margin:0 0 10px;font-size:.95rem;'>👤 {person_label}</p>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric(
                            "Emotion",
                            top_emotion["Type"].capitalize(),
                            f"{confidence:.0f}% confident",
                        )
                    with c2:
                        st.metric("Age Range", f"{age_lo}–{age_hi} yrs")

                    # Emotion breakdown bar chart
                    with st.expander(f"All emotions — Person {i}"):
                        for e in sorted(
                            face["Emotions"],
                            key=lambda x: x["Confidence"], reverse=True,
                        ):
                            st.progress(
                                min(int(e["Confidence"]), 100),
                                text=f"{e['Type'].capitalize()}  "
                                     f"({e['Confidence']:.1f}%)",
                            )

        st.divider()

        # ── Download ───────────────────────────────────────────────────
        st.markdown("#### 📥 Save Your Photo")
        st.download_button(
            label="Download Framed Photo",
            data=st.session_state.image_bytes,
            file_name=st.session_state.file_name,
            mime="image/png",
            use_container_width=True,
        )

        st.divider()

        # ── QR Code ────────────────────────────────────────────────────
        url = st.session_state.photo_url
        if url and url != "#":
            st.markdown("#### 📱 Scan to Get Your Photo")
            qr_pil = qrcode.make(url)
            qr_buf = BytesIO()
            qr_pil.save(qr_buf, format="PNG")

            qr_col, info_col = st.columns([1, 2])
            with qr_col:
                st.image(qr_buf.getvalue(), width=160)
            with info_col:
                st.caption("Point your phone camera at this QR code")
                st.code(url, language=None)
        else:
            st.info("Photo URL not available (S3 upload may have failed).")