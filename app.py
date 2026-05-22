import base64
import threading
import time
import uuid
import traceback
import urllib.parse as _urlparse
from io import BytesIO

import av
import boto3
import cv2
import numpy as np
import qrcode
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from streamlit_webrtc import WebRtcMode, webrtc_streamer, VideoHTMLAttributes
import ai_personality as aip
import caption_generator as cg
import vibe_engine as ve

st.set_page_config(
    page_title="AI Photo Booth ✨",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

/* ══════════ RESET & BASE ══════════ */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: #08080d;
    overflow-x: hidden;
}

/* Reduce top padding to fit content higher up */
.block-container, [data-testid="stAppViewBlockContainer"] {
    padding-top: 1rem !important;
    padding-bottom: 1.5rem !important;
}

/* ── Animated gradient orbs in background ── */
.stApp::before,
.stApp::after {
    content: '';
    position: fixed;
    border-radius: 50%;
    filter: blur(120px);
    opacity: 0.35;
    pointer-events: none;
    z-index: 0;
    animation: orbFloat 18s ease-in-out infinite alternate;
}
.stApp::before {
    width: 500px; height: 500px;
    top: -10%; left: -8%;
    background: radial-gradient(circle, #ff2d75 0%, transparent 70%);
}
.stApp::after {
    width: 600px; height: 600px;
    bottom: -15%; right: -10%;
    background: radial-gradient(circle, #6c3bff 0%, transparent 70%);
    animation-delay: -8s;
}
@keyframes orbFloat {
    0%   { transform: translate(0, 0) scale(1); }
    50%  { transform: translate(40px, -30px) scale(1.12); }
    100% { transform: translate(-20px, 20px) scale(0.95); }
}

/* ── Tech Grid Pattern Overlay ── */
.tech-grid {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    background-image:
        linear-gradient(rgba(255,45,117,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,45,117,0.03) 1px, transparent 1px);
    background-size: 60px 60px;
}

/* ── Animated Scan Line ── */
.scan-line {
    position: fixed;
    left: 0; right: 0;
    height: 2px;
    pointer-events: none;
    z-index: 0;
    background: linear-gradient(90deg,
        transparent 0%,
        rgba(255,45,117,0.15) 20%,
        rgba(108,59,255,0.25) 50%,
        rgba(255,45,117,0.15) 80%,
        transparent 100%);
    animation: scanMove 8s linear infinite;
    box-shadow: 0 0 15px rgba(108,59,255,0.15);
}
@keyframes scanMove {
    0%   { top: -2px; }
    100% { top: 100vh; }
}

/* ── Circuit Trace Decorations ── */
.circuit-corner {
    position: fixed;
    pointer-events: none;
    z-index: 0;
}
.circuit-corner svg {
    opacity: 0.08;
}
.circuit-tl { top: 20px; left: 20px; }
.circuit-br { bottom: 20px; right: 20px; transform: rotate(180deg); }

/* ══════════ TYPOGRAPHY ══════════ */
h1, h2, h3, h4 {
    font-family: 'Space Grotesk', sans-serif !important;
    color: #f5f5f7 !important;
    letter-spacing: -0.03em;
}
p, li, span, label, .stMarkdown {
    color: #a0a0b8;
}

/* ══════════ HIDE STREAMLIT CHROME ══════════ */
#MainMenu, footer, header { display: none !important; }

/* ══════════ SCROLLBAR ══════════ */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,45,117,0.25); border-radius: 10px; }

/* ══════════ VIDEO — SIZING FIX ══════════ */
/*  Use width:100% and max-width so the video occupies the full column width
    for laptop screens, making it 5x larger than before.
    Set border-radius to 0px to display as a proper rectangle.            */
[data-testid="stVerticalBlock"] video,
video {
    width: 80% !important;
    max-width: 275px !important;
    aspect-ratio: 2 / 3 !important;
    height: auto !important;
    object-fit: contain;
    border-radius: 0px !important;
    background: #0c0c14;
    border: 1px solid rgba(255,45,117,0.12);
    display: block !important;
    margin: 0 auto !important;
    transition: border-color 0.4s ease;
}
video:hover {
    border-color: rgba(255,45,117,0.3);
    box-shadow: 0 0 30px rgba(255,45,117,0.08);
}

/* ══════════ DIVIDERS ══════════ */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg,
        transparent 0%,
        rgba(255,45,117,0.3) 30%,
        rgba(108,59,255,0.3) 70%,
        transparent 100%) !important;
    margin: 20px 0 !important;
}

/* ══════════ BUTTONS — BASE ══════════ */
.stButton > button {
    border-radius: 14px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    letter-spacing: -0.01em;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    position: relative;
    overflow: hidden;
}
.stButton > button:hover {
    transform: translateY(-3px) scale(1.02);
}
.stButton > button:active {
    transform: translateY(0) scale(0.98);
    transition-duration: 0.1s;
}

/* ── Capture Button ── */
button[kind="primary"],
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #ff2d75, #ff6b6b, #ff2d75) !important;
    background-size: 200% 200% !important;
    animation: shimmerBtn 4s ease infinite !important;
    color: white !important;
    border: none !important;
    padding: 16px 24px !important;
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    box-shadow: 0 8px 30px rgba(255,45,117,0.35);
    letter-spacing: 0.02em;
}
button[kind="primary"]:hover,
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 12px 40px rgba(255,45,117,0.5) !important;
}

/* Force capture button text to be white */
button[kind="primary"] *,
.stButton > button[kind="primary"] * {
    color: white !important;
}
@keyframes shimmerBtn {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* ── Reset Button ── */
.reset-btn button {
    background: transparent !important;
    border: 1.5px solid rgba(255,255,255,0.1) !important;
    color: #777 !important;
    padding: 12px 20px !important;
    border-radius: 14px !important;
}
.reset-btn button:hover {
    border-color: rgba(255,45,117,0.3) !important;
    color: #ff6b6b !important;
    background: rgba(255,45,117,0.05) !important;
}

/* ── Download Button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #6c3bff, #a855f7) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    padding: 14px 20px;
    box-shadow: 0 6px 25px rgba(108,59,255,0.3);
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.stDownloadButton > button:hover {
    box-shadow: 0 10px 35px rgba(108,59,255,0.5) !important;
    transform: translateY(-3px) scale(1.02);
}

/* ══════════ FRAME GALLERY BUTTONS ══════════ */
.frame-active button {
    background: rgba(255,45,117,0.1) !important;
    border: 2px solid #ff2d75 !important;
    color: #ff6b6b !important;
    font-weight: 700 !important;
    box-shadow: 0 0 20px rgba(255,45,117,0.2);
    animation: activeGlow 2s ease-in-out infinite;
}
@keyframes activeGlow {
    0%, 100% { box-shadow: 0 0 15px rgba(255,45,117,0.15); }
    50%      { box-shadow: 0 0 25px rgba(255,45,117,0.3); }
}

.frame-inactive button {
    background: rgba(255,255,255,0.03) !important;
    border: 1.5px solid rgba(255,255,255,0.06) !important;
    color: #666 !important;
    font-weight: 500 !important;
}
.frame-inactive button:hover {
    border-color: rgba(255,45,117,0.2) !important;
    color: #999 !important;
    background: rgba(255,45,117,0.04) !important;
}

/* ── No-frame placeholder ── */
.no-frame-ph {
    background: rgba(255,255,255,0.03);
    border: 1.5px dashed rgba(255,255,255,0.08);
    border-radius: 12px;
    height: 70px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    transition: border-color 0.3s;
}
.no-frame-ph:hover { border-color: rgba(255,255,255,0.15); }

/* ══════════ RESULT IMAGE ══════════ */
.stImage img {
    border-radius: 0px !important;
    border: 2px solid rgba(255,255,255,0.06);
    transition: border-color 0.3s;
    width: 70% !important;
    margin: 0 auto !important;
    display: block !important;
}
.stImage img:hover {
    border-color: rgba(255,45,117,0.2);
}

/* ══════════ AI ANALYSIS CARD ══════════ */
.ai-face-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 16px;
    transition: border-color 0.3s, transform 0.3s;
}
.ai-face-card:hover {
    border-color: rgba(108,59,255,0.25);
    transform: translateY(-2px);
}
.ai-face-label {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 1rem;
    margin: 0 0 4px;
    background: linear-gradient(135deg, #ff2d75, #ff6b6b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* ══════════ METRICS ══════════ */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 14px;
    padding: 16px;
}
[data-testid="stMetricValue"] {
    color: #f0f0f5 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] { color: #ff6b6b !important; }
[data-testid="stMetricLabel"] { color: #666 !important; }

/* ══════════ EXPANDER ══════════ */
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 12px !important;
    color: #888 !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

/* ══════════ PROGRESS BARS ══════════ */
.stProgress > div > div {
    background: linear-gradient(90deg, #ff2d75, #6c3bff) !important;
    border-radius: 6px;
}
.stProgress > div {
    background: rgba(255,255,255,0.04) !important;
    border-radius: 6px;
}
/* Force progress labels/values in breakdown to be clean white */
.stProgress [data-testid="stWidgetLabel"] p {
    color: #ffffff !important;
}

/* ══════════ ALERTS ══════════ */
[data-testid="stAlert"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 14px !important;
    color: #888 !important;
}

/* ══════════ CODE BLOCK ══════════ */
code {
    background: rgba(255,255,255,0.04) !important;
    color: #ff6b6b !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
}

/* ══════════ CAPTION ══════════ */
.stCaption, [data-testid="stCaption"] { color: #555 !important; }

/* ══════════ SECTION LABEL ══════════ */
.sec-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #555;
    margin-bottom: 6px;
}
.sec-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: #f0f0f5;
    margin-bottom: 18px;
    line-height: 1.2;
}

/* ══════════ FUN TAGLINE ══════════ */
.tagline {
    text-align: center;
    font-size: 0.85rem;
    color: #555;
    margin-top: 2px;
    margin-bottom: 0;
    letter-spacing: 0.03em;
}
.tagline span {
    background: linear-gradient(135deg, #ff2d75, #6c3bff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 600;
}

/* ── Premium Insight slide-up ── */
@keyframes slideUp {
    0% { opacity: 0; transform: translateY(12px); }
    100% { opacity: 1; transform: translateY(0); }
}
.ai-insight-card {
    animation: slideUp 0.6s ease-out;
}

/* ══════════ FLOATING EMOJI BG ══════════ */
.float-emoji {
    position: fixed;
    font-size: 1.4rem;
    opacity: 0.06;
    pointer-events: none;
    z-index: 0;
    animation: emojiDrift 20s linear infinite;
}
@keyframes emojiDrift {
    0%   { transform: translateY(100vh) rotate(0deg); opacity: 0; }
    10%  { opacity: 0.06; }
    90%  { opacity: 0.06; }
    100% { transform: translateY(-20vh) rotate(360deg); opacity: 0; }
}

/* ══════════ SPINNER ══════════ */
.stSpinner > div { border-top-color: #ff2d75 !important; }

@keyframes flash-animation {
    0% { opacity: 0; }
    10% { opacity: 1; }
    100% { opacity: 0; }
}
.flash-active {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background-color: rgba(255, 255, 255, 0.95);
    z-index: 99999;
    pointer-events: none;
    animation: flash-animation 0.4s ease-out forwards;
}

/* ── Photostrip specific additions ── */
.strip-card {
    border-radius: 12px;
    border: 2.5px solid transparent;
    padding: 8px;
    text-align: center;
    background: rgba(255,255,255,0.03);
    transition: all .25s ease;
    cursor: pointer;
    margin-bottom: 4px;
}
.strip-card:hover {
    border-color: rgba(255,45,117,0.3);
    box-shadow: 0 0 10px rgba(255,45,117,0.2);
}
.strip-card.selected {
    border-color: #ff2d75;
    box-shadow: 0 0 18px rgba(255,45,117,0.5), inset 0 0 6px rgba(255,45,117,0.15);
}
.countdown-text {
    font-size: 3rem;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 800;
    text-align: center;
    background: linear-gradient(135deg, #ff2d75, #6c3bff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 10px 0;
}
.home-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 40px;
    text-align: center;
    transition: all 0.3s ease;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 15px;
    height: 100%;
}
.home-card:hover, [data-testid="column"]:hover .home-card {
    border-color: rgba(255,45,117,0.4);
    box-shadow: 0 10px 40px rgba(255,45,117,0.15);
    transform: translateY(-5px);
}
.home-card-icon {
    font-size: 4rem;
}
.home-card-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: #f0f0f5;
}
.home-card-desc {
    color: #a0a0b8;
    font-size: 1rem;
    line-height: 1.5;
}

</style>

<!-- Tech grid overlay -->
<div class="tech-grid"></div>

<!-- Animated scan line -->
<div class="scan-line"></div>

<!-- Circuit trace corners -->
<div class="circuit-corner circuit-tl">
  <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
    <path d="M0 40 H30 L40 30 V0" stroke="#ff2d75" stroke-width="1.5" fill="none"/>
    <path d="M0 60 H15 L25 50 V25 L35 15 H60" stroke="#6c3bff" stroke-width="1" fill="none"/>
    <circle cx="40" cy="0" r="2" fill="#ff2d75"/>
    <circle cx="60" cy="15" r="1.5" fill="#6c3bff"/>
    <circle cx="0" cy="40" r="2" fill="#ff2d75"/>
  </svg>
</div>
<div class="circuit-corner circuit-br">
  <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
    <path d="M0 40 H30 L40 30 V0" stroke="#ff2d75" stroke-width="1.5" fill="none"/>
    <path d="M0 60 H15 L25 50 V25 L35 15 H60" stroke="#6c3bff" stroke-width="1" fill="none"/>
    <circle cx="40" cy="0" r="2" fill="#ff2d75"/>
    <circle cx="60" cy="15" r="1.5" fill="#6c3bff"/>
    <circle cx="0" cy="40" r="2" fill="#ff2d75"/>
  </svg>
</div>

<!-- Floating emoji decorations -->
<div class="float-emoji" style="left:5%;animation-duration:22s;animation-delay:0s">📸</div>
<div class="float-emoji" style="left:15%;animation-duration:28s;animation-delay:-4s">✨</div>
<div class="float-emoji" style="left:30%;animation-duration:25s;animation-delay:-8s">🎭</div>
<div class="float-emoji" style="left:50%;animation-duration:20s;animation-delay:-2s">🎪</div>
<div class="float-emoji" style="left:70%;animation-duration:26s;animation-delay:-10s">🌟</div>
<div class="float-emoji" style="left:85%;animation-duration:23s;animation-delay:-6s">🎉</div>
<div class="float-emoji" style="left:92%;animation-duration:30s;animation-delay:-14s">💫</div>
""", unsafe_allow_html=True)
components.html("""
<script>
// Dispatch resize events so the browser recalculates the <video> element
// layout inside Streamlit's flexbox containers on first load.
setTimeout(function() { window.dispatchEvent(new Event('resize')); }, 500);
setTimeout(function() { window.dispatchEvent(new Event('resize')); }, 1200);
</script>
""", height=0)

# ─────────────────────────────────────────────────────────────────────────────
# AWS CLIENTS
# ─────────────────────────────────────────────────────────────────────────────

try:
    _KEY    = st.secrets["AWS_ACCESS_KEY_ID"]
    _SECRET = st.secrets["AWS_SECRET_ACCESS_KEY"]
    _REGION = st.secrets["AWS_DEFAULT_REGION"]
    S3_BUCKET = st.secrets["S3_BUCKET"]
except KeyError as e:
    st.error(f"Missing configuration in secrets: {e}. Please configure your .streamlit/secrets.toml file.")
    st.stop()

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
# GALLERY THUMBNAIL CACHE  (runs once per frame path — never again)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data
def get_gallery_thumbnail(path):
    """Load a frame PNG, shrink to thumbnail, composite on dark background.
    Cached so it runs exactly once per unique path across all reruns."""
    thumb = Image.open(path).convert("RGBA")
    thumb.thumbnail((120, 180), Image.Resampling.LANCZOS)
    bg = Image.new("RGB", thumb.size, (12, 12, 18))
    bg.paste(thumb, mask=thumb.split()[3])
    return bg

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

# Preview canvas width cap.  Balances quality vs. CPU cost.
#   frame-1  (408px wide)  → scale 0.70 → 285×428  (unchanged)
#   frame 2-6 (1024px wide) → scale 0.47 → 480×720  (was 717×1075 at 0.70)
# This gives a ~2.3× pixel reduction for the large frames while keeping
# the preview sharp enough for the display container.
MAX_PREVIEW_W = 500

def _preview_scale(frame_size):
    """Compute preview scale so canvas width never exceeds MAX_PREVIEW_W."""
    return min(0.70, MAX_PREVIEW_W / frame_size[0])


def build_preview_overlay(res: dict) -> tuple:
    """
    Pre-compute everything the VideoProcessor needs for one frame template.
    Returns (canvas_w, canvas_h, win_x, win_y, win_w, win_h, overlay_tuple)

    overlay_tuple is (frame_bgr_f32, alpha_f32, inv_alpha_f32) or None.

    IMPORTANT — channel order:
      PIL images are RGB.  OpenCV (and av.VideoFrame bgr24) is BGR.
      We store the overlay as BGRA so the numpy blend in recv() is correct.
    """
    fw, fh = res["frame_size"]
    win    = res["window"]

    scale = _preview_scale(res["frame_size"])

    cw = max(1, int(fw * scale))
    ch = max(1, int(fh * scale))

    wx = int(win["x"] * scale)
    wy = int(win["y"] * scale)
    ww = max(1, int(win["w"] * scale))
    wh = max(1, int(win["h"] * scale))

    if res["overlay"] is not None:
        # Resize overlay — BILINEAR is ~3× faster than LANCZOS and
        # visually identical at preview resolution
        ov_rgba = np.array(res["overlay"].resize((cw, ch), Image.BILINEAR))
        # Swap R↔B channels to match the BGR canvas in recv()
        ov_bgra = ov_rgba[:, :, [2, 1, 0, 3]].copy()

        # Pre-compute float values to avoid per-frame casts & divisions
        alpha_f = ov_bgra[:, :, 3:4].astype(np.float32) / 255.0
        inv_alpha_f = 1.0 - alpha_f
        frame_bgr = ov_bgra[:, :, :3].astype(np.float32)
        ov = (frame_bgr, alpha_f, inv_alpha_f)
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
        self._overlay   = None          # (frame_bgr, alpha_f, inv_alpha_f) or None
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
        feed_ratio = w / h
        if feed_ratio > ratio:
            crop_w = int(h * ratio)
            x1 = (w - crop_w) // 2
            portrait_bgr = img[:, x1: x1 + crop_w]
        else:
            crop_h = int(w / ratio)
            y1 = (h - crop_h) // 2
            portrait_bgr = img[y1: y1 + crop_h, :]

        self.portrait = portrait_bgr   # store full-res for capture

        # ── Build preview canvas ──────────────────────────────────────────
        canvas = np.full((ch, cw, 3), 255, dtype=np.uint8)
        thumb  = cv2.resize(portrait_bgr, (ww, wh), interpolation=cv2.INTER_LINEAR)

        y2 = min(wy + wh, ch)
        x2 = min(wx + ww, cw)
        canvas[wy:y2, wx:x2] = thumb[:y2 - wy, :x2 - wx]

        # ── Alpha-blend frame overlay ─────────────────────────────────────
        if overlay is not None:
            frame_bgr, alpha_f, inv_alpha_f = overlay
            canvas = (frame_bgr * alpha_f + canvas.astype(np.float32) * inv_alpha_f).astype(np.uint8)

        return av.VideoFrame.from_ndarray(canvas, format="bgr24")


# ─────────────────────────────────────────────────────────────────────────────
# MOBILE SHARE PAGE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

import urllib.parse as _urlparse

def generate_share_page(image_url: str, file_name: str) -> str:
    """
    Build a self-contained mobile-first HTML share page.
    The QR code points here instead of the raw S3 image URL.
    """
    enc      = _urlparse.quote(image_url, safe="")
    wa_url   = "https://wa.me/?text=Check%20out%20my%20AI%20Photo%20Booth%20snap!%20" + enc
    tg_url   = "https://t.me/share/url?url=" + enc + "&text=Check%20out%20my%20AI%20Photo%20Booth%20snap!"
    mail_url = "mailto:?subject=My%20AI%20Photo%20Booth%20Snap&body=" + enc

    html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<meta name="theme-color" content="#08080d">
<meta property="og:image" content="__IMG__">
<meta property="og:title" content="My AI Photo Booth Snap! 📸">
<meta property="og:description" content="Captured at AWS SBG AI Photo Booth ✨">
<title>AI Photo Booth</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{
  background:#08080d;color:#f5f5f7;
  font-family:'Space Grotesk',sans-serif;
  min-height:100vh;display:flex;flex-direction:column;
  align-items:center;overflow-x:hidden;
}
body::before{
  content:'';position:fixed;width:320px;height:320px;
  top:-60px;left:-60px;
  background:radial-gradient(circle,rgba(255,45,117,0.35) 0%,transparent 70%);
  border-radius:50%;filter:blur(90px);pointer-events:none;z-index:0;
  animation:orb 14s ease-in-out infinite alternate;
}
body::after{
  content:'';position:fixed;width:360px;height:360px;
  bottom:-80px;right:-60px;
  background:radial-gradient(circle,rgba(108,59,255,0.35) 0%,transparent 70%);
  border-radius:50%;filter:blur(90px);pointer-events:none;z-index:0;
  animation:orb 18s ease-in-out infinite alternate-reverse;
}
@keyframes orb{
  0%{transform:translate(0,0) scale(1);}
  100%{transform:translate(20px,-20px) scale(1.1);}
}
.container{
  position:relative;z-index:1;
  width:100%;max-width:480px;
  padding:28px 20px 52px;
  display:flex;flex-direction:column;
  align-items:center;gap:22px;
}
.header{text-align:center;}
.header h1{
  font-size:2rem;font-weight:800;letter-spacing:-0.04em;
  background:linear-gradient(135deg,#ff2d75,#ff6b6b,#6c3bff);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  filter:drop-shadow(0 0 22px rgba(255,45,117,0.3));
  margin-bottom:5px;
}
.header p{font-size:0.78rem;color:#555;letter-spacing:0.04em;}
.header p span{
  background:linear-gradient(135deg,#ff2d75,#6c3bff);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  font-weight:600;
}
.photo-wrap{
  width:100%;position:relative;
  border-radius:20px;overflow:hidden;
  box-shadow:0 0 60px rgba(255,45,117,0.12),0 24px 64px rgba(0,0,0,0.55);
  border:1.5px solid rgba(255,255,255,0.08);
}
.photo-wrap img{width:100%;display:block;}
.badge{
  position:absolute;top:12px;left:12px;
  background:rgba(8,8,13,0.82);backdrop-filter:blur(12px);
  border:1px solid rgba(255,45,117,0.35);border-radius:20px;
  padding:4px 12px;font-size:0.64rem;font-weight:700;
  color:#ff6b6b;letter-spacing:0.12em;text-transform:uppercase;
}
.btn-group{width:100%;display:flex;flex-direction:column;gap:12px;}
.btn{
  width:100%;padding:17px 24px;border-radius:16px;border:none;
  font-family:'Space Grotesk',sans-serif;font-size:1rem;font-weight:700;
  cursor:pointer;display:flex;align-items:center;justify-content:center;
  gap:10px;transition:all 0.3s cubic-bezier(0.34,1.56,0.64,1);
  color:white;text-decoration:none;
}
.btn:active{transform:scale(0.97);}
@keyframes shimmer{
  0%{background-position:0% 50%;}
  50%{background-position:100% 50%;}
  100%{background-position:0% 50%;}
}
.btn-share{
  background:linear-gradient(135deg,#ff2d75,#ff6b6b,#ff2d75);
  background-size:200% 200%;animation:shimmer 3s ease infinite;
  box-shadow:0 8px 32px rgba(255,45,117,0.4);
}
.btn-dl{
  background:linear-gradient(135deg,#6c3bff,#a855f7);
  box-shadow:0 8px 32px rgba(108,59,255,0.4);
}
.divider{
  display:flex;align-items:center;gap:12px;width:100%;
  color:#2d2d40;font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;
}
.divider::before,.divider::after{
  content:'';flex:1;height:1px;
  background:rgba(255,255,255,0.06);
}
.social-row{
  display:flex;gap:10px;width:100%;
  justify-content:center;flex-wrap:wrap;
}
.s-btn{
  flex:1;min-width:72px;max-width:110px;
  padding:14px 8px;border-radius:14px;
  border:1.5px solid rgba(255,255,255,0.06);
  background:rgba(255,255,255,0.025);
  color:#777;font-family:'Space Grotesk',sans-serif;
  font-size:0.7rem;font-weight:600;cursor:pointer;
  display:flex;flex-direction:column;align-items:center;gap:5px;
  text-decoration:none;transition:all 0.2s ease;
}
.s-btn:active{transform:scale(0.95);background:rgba(255,255,255,0.06);}
.s-btn .ic{font-size:1.45rem;}
.footer{
  text-align:center;font-size:0.68rem;
  color:#252535;padding-top:4px;line-height:1.6;
}
.footer strong{
  background:linear-gradient(135deg,#ff2d75,#6c3bff);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
.toast{
  position:fixed;bottom:28px;left:50%;transform:translateX(-50%);
  background:rgba(255,255,255,0.08);backdrop-filter:blur(20px);
  border:1px solid rgba(255,255,255,0.1);color:#f5f5f7;
  padding:12px 26px;border-radius:40px;
  font-size:0.85rem;font-weight:600;
  opacity:0;transition:opacity 0.35s;z-index:999;
  white-space:nowrap;pointer-events:none;
}
.toast.show{opacity:1;}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>AI Photo Booth <span style="-webkit-text-fill-color: initial;">📸</span></h1>
    <p>Crafted by <span>Ankitha Jade</span> and <span>Sadhana S</span></p>
  </div>

  <div class="photo-wrap">
    <img src="__IMG__" alt="Your AI Photo Booth Snap" />
    <div class="badge">✨ AI Captured</div>
  </div>

  <div class="btn-group">
    <button class="btn btn-share" onclick="sharePhoto()">🚀 Share Photo</button>
    <button class="btn btn-dl"    onclick="downloadPhoto()">⬇️ Save to Phone</button>
  </div>

  <div class="footer">
    Powered by <strong>AWS SBG AI Photo Booth</strong><br>
    AWS Rekognition · AI Personality Engine
  </div>

</div>
<div class="toast" id="toast"></div>

<script>
var IMG = "__IMG__";
var FN  = "__FN__";

function toast(msg) {
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(function(){ t.classList.remove('show'); }, 2800);
}

async function sharePhoto() {
  if (!navigator.share) { copyLink(); return; }
  try {
    var res  = await fetch(IMG);
    var blob = await res.blob();
    var file = new File([blob], FN, { type: 'image/png' });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({
        files: [file],
        title: 'My AI Photo Booth Snap! 📸',
        text:  'Check out my AI-analyzed photo from Vignanotsava! ✨'
      });
    } else {
      await navigator.share({
        title: 'My AI Photo Booth Snap! 📸',
        text:  'Check out my AI-analyzed photo from Vignanotsava! ✨',
        url:   IMG
      });
    }
  } catch(e) {
    if (e.name !== 'AbortError') copyLink();
  }
}

async function downloadPhoto() {
  try {
    var res  = await fetch(IMG);
    var blob = await res.blob();
    var url  = URL.createObjectURL(blob);
    var a    = document.createElement('a');
    a.href = url; a.download = FN;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast('✅ Saved to your photos!');
  } catch(e) {
    window.open(IMG, '_blank');
    toast('✅ Photo opened — save from here!');
  }
}

function copyLink() {
  var link = window.location.href;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(link).then(function() {
      toast('🔗 Link copied!');
    }).catch(function() {
      toast('Link: ' + link);
    });
  } else {
    toast('Link: ' + link);
  }
}
</script>
</body>
</html>
"""
    html = html.replace("__IMG__",  image_url)
    html = html.replace("__FN__",   file_name)
    html = html.replace("__WA__",   wa_url)
    html = html.replace("__TG__",   tg_url)
    html = html.replace("__MAIL__", mail_url)
    return html


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE  (initialised once)
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

def generate_photostrip_share_page(image_url: str) -> str:
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
    <h1><span style="-webkit-text-fill-color: initial;">&#128247;</span> Photostrip Saved!</h1>
    <p>Your photostrip memory is ready.</p>
    <div class="image-preview">
      <img id="booth-img" src="{image_url}" alt="Photostrip Capture">
    </div>
    <button class="btn btn-share" id="share-btn">&#128228; Share Photostrip</button>
    <a href="{image_url}" download="photostrip_capture.png" class="btn btn-download" id="download-btn">
      &#128229; Download Photostrip
    </a>
    <div class="footer">Crafted by <strong>Ankitha Jade</strong> and <strong>Sadhana S</strong></div>
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
    uid = uuid.uuid4().hex[:6]
    png_key  = f"photostrip_{int(time.time())}_{uid}.png"
    html_key = f"photostrip_{int(time.time())}_{uid}.html"

    try:
        # 1. Upload the PNG image
        s3.put_object(Bucket=S3_BUCKET, Key=png_key,
                      Body=img_bytes, ContentType="image/png")
        raw_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{png_key}"

        # 2. Generate and upload the HTML share page
        html_body = generate_photostrip_share_page(raw_url)
        s3.put_object(Bucket=S3_BUCKET, Key=html_key,
                      Body=html_body.encode("utf-8"), ContentType="text/html")

        return f"https://{S3_BUCKET}.s3.amazonaws.com/{html_key}", None

    except Exception as exc:
        traceback.print_exc()
        return "#", str(exc)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────


def _init_state():
    if "app_page" not in st.session_state:
        st.session_state.app_page = "home"
        
    # Photobooth defaults
    pb_defaults = {
        "captured":      False,
        "frame_id":      "frame1",      
        "camera_run_id": 0,
        "final_image":   None,          
        "image_bytes":   None,
        "file_name":     None,
        "photo_url":     None,
        "rek_faces":     [],            
    }
    for k, v in pb_defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
            
    # Photostrip defaults
    ps_defaults = {
        "ps_mode":            "capture",   
        "ps_captured_photos": [],          
        "ps_camera_run_id":   100, # Offset to avoid conflict with photobooth
        "ps_final_strip":     None,
        "ps_image_bytes":     None,
        "ps_file_name":       None,
        "ps_photo_url":       None,
        "ps_is_capturing":    False,
        "ps_selected_strip":  "strip-1",
        "ps_selected_filter": "color",
        "ps_upload_error":    None,
    }
    for k, v in ps_defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def _reset_ps_session():
    st.session_state.ps_camera_run_id += 1
    st.session_state.ps_mode = "capture"
    st.session_state.ps_captured_photos = []
    st.session_state.ps_final_strip = None
    st.session_state.ps_image_bytes = None
    st.session_state.ps_file_name = None
    st.session_state.ps_photo_url = None
    st.session_state.ps_is_capturing = False
    st.session_state.ps_upload_error = None


def render_home_page():
    st.markdown(
        "<div style='text-align:center; padding-top: 10px;'>"
        "<h1 style='"
        "font-family:Space Grotesk,sans-serif;"
        "font-size:3.5rem;font-weight:800;margin-bottom:0;"
        "letter-spacing:-0.04em;"
        "background:linear-gradient(135deg,#ff2d75 0%,#ff6b6b 40%,#6c3bff 100%);"
        "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
        "filter:drop-shadow(0 0 25px rgba(255,45,117,0.2));'>"
        "AI Photo Booth</h1>"
        "<p style='font-size:1.2rem; color:#a0a0b8; margin-top:5px; font-weight:500; font-family:Space Grotesk, sans-serif;'>"
        "AWS Student Builder Group, DBIT &nbsp;&bull;&nbsp; <span style='color:#ff6b6b;'>Vignanotsava 2k26</span>"
        "</p>"
        "<p style='font-size:0.9rem; color:#555; margin-top:4px; font-family:DM Sans, sans-serif;'>"
        "Crafted by <span style='background:linear-gradient(135deg,#ff2d75,#6c3bff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:600;'>Ankitha Jade</span>"
        " and <span style='background:linear-gradient(135deg,#ff2d75,#6c3bff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:600;'>Sadhana S</span>"
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<br><br>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([1, 4, 4, 1], gap="large")

    with col2:
        pb_clicked = st.button("Enter Photobooth", key="btn_go_pb", type="primary", use_container_width=True)
        st.markdown(
            "<div class='home-card'>"
            "<div class='home-card-icon'>&#128247;</div>"
            "<div class='home-card-title'>Photobooth</div>"
            "<div class='home-card-desc'>Single frame capture with AI Personality Analysis, Vibe Check, and custom event frames.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        if pb_clicked:
            st.session_state.app_page = "photobooth"
            st.rerun()

    with col3:
        ps_clicked = st.button("Enter Photostrip", key="btn_go_ps", type="primary", use_container_width=True)
        st.markdown(
            "<div class='home-card'>"
            "<div class='home-card-icon'>&#127902;</div>"
            "<div class='home-card-title'>Photostrip</div>"
            "<div class='home-card-desc'>Classic 4-photo strip capture with vintage/B&amp;W filters and printable layouts.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        if ps_clicked:
            st.session_state.app_page = "photostrip"
            st.rerun()

    # Hide the Streamlit buttons but keep them clickable via JS
    st.markdown("""
        <style>
        div[data-testid="column"] div.stButton,
        div[data-testid="column"] button {
            position: absolute !important;
            width: 0px !important;
            height: 0px !important;
            padding: 0 !important;
            margin: 0 !important;
            opacity: 0 !important;
            overflow: hidden !important;
            pointer-events: none !important;
            border: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    components.html("""
    <script>
    if (!window.parent.document.body.dataset.cardListenerAdded) {
        window.parent.document.body.addEventListener('click', function(e) {
            const card = e.target.closest('.home-card');
            if (card) {
                const col = card.closest('[data-testid="column"]');
                if (col) {
                    const btn = col.querySelector('button');
                    if (btn) btn.click();
                }
            }
        });
        window.parent.document.body.dataset.cardListenerAdded = 'true';
    }
    </script>
    """, height=0)


def render_photobooth_page():
    if not st.session_state.captured:
        # Title row: back button + title inline
        hdr_l, hdr_r = st.columns([1, 5], gap="small")
        with hdr_l:
            st.markdown('<div class="reset-btn" style="padding-top:6px;">', unsafe_allow_html=True)
            if st.button("← Home", key="pb_back"):
                st.session_state.app_page = "home"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with hdr_r:
            st.markdown(
                "<h1 style='"
                "font-family:Space Grotesk,sans-serif;"
                "font-size:2.2rem;font-weight:800;margin:0;"
                "letter-spacing:-0.04em;"
                "background:linear-gradient(135deg,#ff2d75 0%,#ff6b6b 40%,#6c3bff 100%);"
                "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
                "filter:drop-shadow(0 0 25px rgba(255,45,117,0.2));'>"
                "AI Photo Booth</h1>"
                "<p class='tagline' style='margin:2px 0 0;'>"
                "Crafted by <span>Ankitha Jade</span> and <span>Sadhana S</span>"
                "</p>",
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
            st.markdown("<p class='sec-label'>Live Camera</p>", unsafe_allow_html=True)
            st.markdown("<p class='sec-title'>📸 Strike a Pose!</p>", unsafe_allow_html=True)
    
            ctx = webrtc_streamer(
                key=f"booth_{st.session_state.camera_run_id}",
                desired_playing_state=True,
                mode=WebRtcMode.SENDRECV,
                video_processor_factory=VideoProcessor,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
                media_stream_constraints={
                    "video": {
                        "width": {"ideal": 1080},
                        "height": {"ideal": 1920},
                        "frameRate": {"ideal": 30}
                    },
                    "audio": False
                },
                async_processing=True,
                video_html_attrs=VideoHTMLAttributes(
                    autoPlay=True,
                    controls=False,
                    style={
                        "width": "80%",
                        "maxWidth": "275px",
                        "aspectRatio": "2 / 3",
                        "height": "auto",
                        "objectFit": "contain",
                        "borderRadius": "0px",
                        "background": "#0c0c14",
                        "display": "block",
                        "margin": "0 auto",
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
    
            # ── Capture button ────────────────────────────────────────────────
            capture_clicked = st.button(
                "📸  Capture Photo",
                key="capture",
                type="primary",
                use_container_width=True,
            )
    
            if capture_clicked:
                if not ctx.video_processor:
                    st.warning("⏳ Start the camera first, then click Capture.")
                elif ctx.video_processor.portrait is None:
                    st.warning("⏳ No frame captured yet — wait a moment and try again.")
                else:
                    # Trigger visual flash feedback
                    st.markdown("<div class='flash-active'></div>", unsafe_allow_html=True)
                    time.sleep(0.3)
    
                    with st.spinner("✨ Analyzing your photo with AI…"):
    
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
                        uid       = uuid.uuid4().hex[:6]
                        file_name = f"photo_{ts}_{uid}.png"
                        image_url = "#"   # raw image URL
                        photo_url = "#"   # share-page URL (used for QR)
                        try:
                            s3.put_object(
                                Bucket=S3_BUCKET, Key=file_name,
                                Body=img_bytes,   ContentType="image/png",
                            )
                            image_url = (
                                f"https://{S3_BUCKET}.s3.amazonaws.com/{file_name}"
                            )
                            # ── Generate & upload mobile share page ────────
                            share_html = generate_share_page(image_url, file_name)
                            share_key  = f"share_{ts}_{uid}.html"
                            s3.put_object(
                                Bucket=S3_BUCKET, Key=share_key,
                                Body=share_html.encode("utf-8"),
                                ContentType="text/html; charset=utf-8",
                            )
                            photo_url = (
                                f"https://{S3_BUCKET}.s3.amazonaws.com/{share_key}"
                            )
                        except Exception as e:
                            st.error(f"S3 upload error: {e}")
                            if image_url != "#":
                                photo_url = image_url  # fallback: QR → raw image
    
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
            st.markdown("<p class='sec-label'>Templates</p>", unsafe_allow_html=True)
            st.markdown("<p class='sec-title'>🖼️ Pick Your Frame</p>", unsafe_allow_html=True)
    
            # Render in a compact grid
            cols_per_row = 4
            for row_idx in range(0, len(FRAME_REGISTRY), cols_per_row):
                row_entries = FRAME_REGISTRY[row_idx : row_idx + cols_per_row]
                gallery_cols = st.columns(cols_per_row)
                for col_idx, entry in enumerate(row_entries):
                    with gallery_cols[col_idx]:
                        is_active = st.session_state.frame_id == entry["id"]
    
                        # Thumbnail (cached)
                        if entry["path"]:
                            thumb_img = get_gallery_thumbnail(entry["path"])
                            st.image(thumb_img, use_container_width=True)
                        else:
                            st.markdown(
                                "<div class='no-frame-ph'>✕</div>",
                                unsafe_allow_html=True,
                            )
    
                        # Select button
                        btn_class = "frame-active" if is_active else "frame-inactive"
                        btn_label = f"✓ {entry['label']}" if is_active else entry["label"]
                        st.markdown(f"<div class='{btn_class}'>", unsafe_allow_html=True)
                        if st.button(btn_label, key=f"frame_btn_{entry['id']}",
                                     use_container_width=True):
                            st.session_state.frame_id = entry["id"]
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
    
    
    # ─────────────────────────────────────────────────────────────────────────────
    # ══════════════════════  STATE 2 — AFTER CAPTURE  ════════════════════════════
    # ─────────────────────────────────────────────────────────────────────────────
    
    else:
        left, right = st.columns([2, 3], gap="large")
    
        # ── LEFT: final framed photo ───────────────────────────────────────────
        with left:
            st.markdown(
                "<h1 style='text-align:left;"
                "font-family:Space Grotesk,sans-serif;"
                "font-size:2.4rem;font-weight:800;margin-bottom:0;"
                "letter-spacing:-0.04em;"
                "background:linear-gradient(135deg,#ff2d75 0%,#ff6b6b 40%,#6c3bff 100%);"
                "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
                "filter:drop-shadow(0 0 25px rgba(255,45,117,0.2));'>"
                "AI Photo Booth</h1>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p class='tagline' style='text-align:left; margin-left:0; padding-left:0; margin-bottom: 0px;'>"
                "Crafted by <span>Ankitha Jade</span> and <span>Sadhana S</span>"
                "</p>",
                unsafe_allow_html=True,
            )
            st.divider()
    
            st.markdown("<p class='sec-label'>Result</p>", unsafe_allow_html=True)
            st.markdown("<p class='sec-title'>🎉 Looking Great!</p>", unsafe_allow_html=True)
            st.image(
                st.session_state.final_image,
                use_container_width=True,
            )
    
            # Reset button
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
            st.markdown("<p class='sec-label'>AI Insights</p>", unsafe_allow_html=True)
            st.markdown("<p class='sec-title'>🤖 Here's What AI Sees</p>", unsafe_allow_html=True)
    
            faces = st.session_state.rek_faces
    
            if not faces:
                st.info("🤷 No faces detected — try again with better lighting!")
            else:
                # ═════════════════════════════════════════════════════════════════
                # CASE A: TWO OR MORE PEOPLE DETECTED (SIDE-BY-SIDE COLUMNS)
                # ═════════════════════════════════════════════════════════════════
                if len(faces) >= 2:
                    # 1. Team Vibe & QR Code Side-by-Side
                    st.markdown("<p class='sec-label'>Team Chemistry & Share</p>", unsafe_allow_html=True)
                    vibe_col, qr_col = st.columns([3, 2], gap="medium")
                    with vibe_col:
                        group_vibe = ve.get_group_vibe(faces)
                        st.markdown(
                            f"<div class='ai-face-card' style='background: linear-gradient(135deg, rgba(108,59,255,0.08), rgba(255,45,117,0.08)); border-color: rgba(108,59,255,0.25); text-align: center; height: 130px; display: flex; flex-direction: column; justify-content: center; align-items: center; margin-bottom: 0px; padding: 15px; box-sizing: border-box;'>"
                            f"<p class='sec-label' style='color: #a855f7; margin-bottom: 4px; font-size: 0.65rem; text-transform: uppercase;'>Team Vibe</p>"
                            f"<h4 style='margin: 0; font-family: \"Space Grotesk\", sans-serif; font-weight: 700; color: #f0f0f5; font-size: 1.1rem;'>✨ {group_vibe}</h4>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with qr_col:
                        url = st.session_state.photo_url
                        if url and url != "#":
                            qr_pil = qrcode.make(url)
                            qr_buf = BytesIO()
                            qr_pil.save(qr_buf, format="PNG")
                            qr_b64 = base64.b64encode(qr_buf.getvalue()).decode("utf-8")
                            st.markdown(
                                f"<div style='display: flex; align-items: center; justify-content: center; height: 130px; box-sizing: border-box;'>"
                                f"<img src='data:image/png;base64,{qr_b64}' style='width: 130px; height: 130px; border-radius: 12px; border: 1.5px solid rgba(255,255,255,0.08);' />"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        else:
                            st.info("Photo URL not available.")
    
                    st.divider()
    
                    # 2. Extract Data for both people independently
                    f1_data = faces[0]
                    f2_data = faces[1]
    
                    p1_emotion = max(f1_data["Emotions"], key=lambda e: e["Confidence"])
                    p1_age_lo  = f1_data["AgeRange"]["Low"]
                    p1_age_hi  = f1_data["AgeRange"]["High"]
                    p1_personality = aip.get_personality(f1_data)
                    p1_caption = cg.get_caption(f1_data)
                    p1_badges = aip.get_badges(f1_data)
                    p1_vibes = ve.get_vibes(f1_data)
    
                    p2_emotion = max(f2_data["Emotions"], key=lambda e: e["Confidence"])
                    p2_age_lo  = f2_data["AgeRange"]["Low"]
                    p2_age_hi  = f2_data["AgeRange"]["High"]
                    p2_personality = aip.get_personality(f2_data)
                    p2_caption = cg.get_caption(f2_data)
                    p2_badges = aip.get_badges(f2_data)
                    p2_vibes = ve.get_vibes(f2_data)
    
                    # Emoji helper mapping
                    emoji_map = {
                        "HAPPY": "😄", "SAD": "😢", "ANGRY": "😠",
                        "CONFUSED": "🤔", "DISGUSTED": "🤢", "SURPRISED": "😲",
                        "CALM": "😌", "FEAR": "😰",
                    }
                    p1_emoji = emoji_map.get(p1_emotion["Type"], "🎭")
                    p2_emoji = emoji_map.get(p2_emotion["Type"], "🎭")
    
                    # 3. Two columns side-by-side
                    p1_col, p2_col = st.columns(2, gap="medium")
    
                    with p1_col:
                        st.markdown(
                            f"<div class='ai-face-card' style='margin-bottom: 12px;'>"
                            f"<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;'>"
                            f"<p class='ai-face-label' style='margin: 0;'>{p1_emoji} Person 1</p>"
                            f"<div style='display: flex; gap: 4px; align-items: center; flex-wrap: wrap;'>"
                            f"<span style='background: rgba(255,45,117,0.15); color: #ff6b6b; padding: 2px 6px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; font-family: \"Space Grotesk\"; border: 1px solid rgba(255,45,117,0.2);'>{p1_age_lo}–{p1_age_hi} yrs</span>"
                            f"<span style='background: rgba(108,59,255,0.15); color: #a855f7; padding: 2px 6px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; font-family: \"Space Grotesk\"; border: 1px solid rgba(108,59,255,0.2);'>{p1_emoji} {p1_emotion['Type'].capitalize()}</span>"
                            f"</div>"
                            f"</div>"
                            f"<p style='margin: 6px 0 0; font-size: 0.8rem; color: #a0a0b8; font-style: italic;'>\"{p1_caption}\"</p>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
    
                        st.markdown(
                            f"<div class='ai-insight-card' style='background: linear-gradient(135deg, rgba(255,45,117,0.05), rgba(108,59,255,0.05)); border: 1px solid rgba(255,45,117,0.15); border-radius: 12px; padding: 10px; margin-bottom: 10px; text-align: center;'>"
                            f"<p style='font-family: \"Space Grotesk\", sans-serif; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em; color: #ff6b6b; margin: 0 0 2px 0;'>AI Persona</p>"
                            f"<h3 style='font-family: \"Space Grotesk\", sans-serif; font-size: 0.95rem; font-weight: 700; background: linear-gradient(135deg, #00d4ff, #7b2fff, #e044ab); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;'>{p1_personality}</h3>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
    
                        p1_badge_html = "".join([
                            f"<span style='background: rgba(108,59,255,0.12); color: #a855f7; border: 1px solid rgba(108,59,255,0.2); padding: 3px 8px; border-radius: 20px; font-size: 0.65rem; font-weight: 600; font-family: \"DM Sans\";'>{badge}</span>"
                            for badge in p1_badges
                        ])
                        st.markdown(
                            f"<div style='display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; margin-bottom: 10px;'>{p1_badge_html}</div>",
                            unsafe_allow_html=True
                        )
    
                        for label, val in p1_vibes.items():
                            st.markdown(
                                f"<div style='display: flex; justify-content: space-between; font-size: 0.72rem; margin-bottom: 1px;'>"
                                f"<span style='color: #888; font-weight: 500;'>{label}</span>"
                                f"<span style='color: #00d4ff; font-weight: 600; font-family: Space Grotesk;'>{val}</span>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                            val_str = str(val)
                            if "MAX" in val_str:
                                progress_val = 100
                            elif "CRITICAL" in val_str:
                                progress_val = 15
                            else:
                                try:
                                    progress_val = int(val_str.replace("%", ""))
                                except ValueError:
                                    progress_val = 50
                            st.progress(progress_val)
    
                        # Move Full Breakdown under Person 1 column
                        with st.expander("Person 1 Full Breakdown"):
                            for e in sorted(
                                f1_data["Emotions"],
                                key=lambda x: x["Confidence"], reverse=True,
                            ):
                                st.progress(
                                    min(int(e["Confidence"]), 100),
                                    text=f"{e['Type'].capitalize()} ({e['Confidence']:.1f}%)"
                                )
    
                    with p2_col:
                        st.markdown(
                            f"<div class='ai-face-card' style='margin-bottom: 12px;'>"
                            f"<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;'>"
                            f"<p class='ai-face-label' style='margin: 0;'>{p2_emoji} Person 2</p>"
                            f"<div style='display: flex; gap: 4px; align-items: center; flex-wrap: wrap;'>"
                            f"<span style='background: rgba(255,45,117,0.15); color: #ff6b6b; padding: 2px 6px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; font-family: \"Space Grotesk\"; border: 1px solid rgba(255,45,117,0.2);'>{p2_age_lo}–{p2_age_hi} yrs</span>"
                            f"<span style='background: rgba(108,59,255,0.15); color: #a855f7; padding: 2px 6px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; font-family: \"Space Grotesk\"; border: 1px solid rgba(108,59,255,0.2);'>{p2_emoji} {p2_emotion['Type'].capitalize()}</span>"
                            f"</div>"
                            f"</div>"
                            f"<p style='margin: 6px 0 0; font-size: 0.8rem; color: #a0a0b8; font-style: italic;'>\"{p2_caption}\"</p>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
    
                        st.markdown(
                            f"<div class='ai-insight-card' style='background: linear-gradient(135deg, rgba(255,45,117,0.05), rgba(108,59,255,0.05)); border: 1px solid rgba(255,45,117,0.15); border-radius: 12px; padding: 10px; margin-bottom: 10px; text-align: center;'>"
                            f"<p style='font-family: \"Space Grotesk\", sans-serif; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em; color: #ff6b6b; margin: 0 0 2px 0;'>AI Persona</p>"
                            f"<h3 style='font-family: \"Space Grotesk\", sans-serif; font-size: 0.95rem; font-weight: 700; background: linear-gradient(135deg, #00d4ff, #7b2fff, #e044ab); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;'>{p2_personality}</h3>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
    
                        p2_badge_html = "".join([
                            f"<span style='background: rgba(108,59,255,0.12); color: #a855f7; border: 1px solid rgba(108,59,255,0.2); padding: 3px 8px; border-radius: 20px; font-size: 0.65rem; font-weight: 600; font-family: \"DM Sans\";'>{badge}</span>"
                            for badge in p2_badges
                        ])
                        st.markdown(
                            f"<div style='display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; margin-bottom: 10px;'>{p2_badge_html}</div>",
                            unsafe_allow_html=True
                        )
    
                        for label, val in p2_vibes.items():
                            st.markdown(
                                f"<div style='display: flex; justify-content: space-between; font-size: 0.72rem; margin-bottom: 1px;'>"
                                f"<span style='color: #888; font-weight: 500;'>{label}</span>"
                                f"<span style='color: #00d4ff; font-weight: 600; font-family: Space Grotesk;'>{val}</span>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                            val_str = str(val)
                            if "MAX" in val_str:
                                progress_val = 100
                            elif "CRITICAL" in val_str:
                                progress_val = 15
                            else:
                                try:
                                    progress_val = int(val_str.replace("%", ""))
                                except ValueError:
                                    progress_val = 50
                            st.progress(progress_val)
    
                        # Move Full Breakdown under Person 2 column
                        with st.expander("Person 2 Full Breakdown"):
                            for e in sorted(
                                f2_data["Emotions"],
                                key=lambda x: x["Confidence"], reverse=True,
                            ):
                                st.progress(
                                    min(int(e["Confidence"]), 100),
                                    text=f"{e['Type'].capitalize()} ({e['Confidence']:.1f}%)"
                                )
    
                # ═════════════════════════════════════════════════════════════════
                # CASE B: ONE PERSON DETECTED
                # ═════════════════════════════════════════════════════════════════
                else:
                    face_data = faces[0]
                    top_emotion = max(face_data["Emotions"], key=lambda e: e["Confidence"])
                    age_lo      = face_data["AgeRange"]["Low"]
                    age_hi      = face_data["AgeRange"]["High"]
    
                    personality = aip.get_personality(face_data)
                    caption = cg.get_caption(face_data)
                    badges = aip.get_badges(face_data)
                    vibes = ve.get_vibes(face_data)
    
                    # Emoji for top emotion
                    emoji_map = {
                        "HAPPY": "😄", "SAD": "😢", "ANGRY": "😠",
                        "CONFUSED": "🤔", "DISGUSTED": "🤢", "SURPRISED": "😲",
                        "CALM": "😌", "FEAR": "😰",
                    }
                    emotion_emoji = emoji_map.get(top_emotion["Type"], "🎭")
    
                    # 1. Main Face Card: Shows Age, Emotion, & Funny Caption
                    st.markdown(
                        f"<div class='ai-face-card' style='margin-bottom: 12px;'>"
                        f"<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;'>"
                        f"<p class='ai-face-label' style='margin: 0;'>{emotion_emoji} Detected Face</p>"
                        f"<div style='display: flex; gap: 6px; align-items: center;'>"
                        f"<span style='background: rgba(255,45,117,0.15); color: #ff6b6b; padding: 4px 10px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; font-family: \"Space Grotesk\"; border: 1px solid rgba(255,45,117,0.2);'>{age_lo}–{age_hi} yrs</span>"
                        f"<span style='background: rgba(108,59,255,0.15); color: #a855f7; padding: 4px 10px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; font-family: \"Space Grotesk\"; border: 1px solid rgba(108,59,255,0.2);'>{emotion_emoji} {top_emotion['Type'].capitalize()}</span>"
                        f"</div>"
                        f"</div>"
                        f"<p style='margin: 6px 0 0; font-size: 0.85rem; color: #a0a0b8; font-style: italic;'>\"{caption}\"</p>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
    
                    # 2. Side-by-Side: AI Persona + Badges (left) and QR code (right)
                    persona_col, qr_col = st.columns([3, 2], gap="medium")
                    with persona_col:
                        st.markdown(
                            f"<div class='ai-insight-card' style='background: linear-gradient(135deg, rgba(255,45,117,0.05), rgba(108,59,255,0.05)); border: 1px solid rgba(255,45,117,0.15); border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 8px;'>"
                            f"<p style='font-family: \"Space Grotesk\", sans-serif; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: #ff6b6b; margin: 0 0 4px 0;'>AI Persona</p>"
                            f"<h3 style='font-family: \"Space Grotesk\", sans-serif; font-size: 1.1rem; font-weight: 700; background: linear-gradient(135deg, #00d4ff, #7b2fff, #e044ab); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;'>{personality}</h3>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        badge_html = "".join([
                            f"<span style='background: rgba(108,59,255,0.12); color: #a855f7; border: 1px solid rgba(108,59,255,0.2); padding: 4px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; font-family: \"DM Sans\";'>{badge}</span>"
                            for badge in badges
                        ])
                        st.markdown(
                            f"<div style='display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; margin-bottom: 0px;'>{badge_html}</div>",
                            unsafe_allow_html=True
                        )
                    with qr_col:
                        url = st.session_state.photo_url
                        if url and url != "#":
                            qr_pil = qrcode.make(url)
                            qr_buf = BytesIO()
                            qr_pil.save(qr_buf, format="PNG")
                            qr_b64 = base64.b64encode(qr_buf.getvalue()).decode("utf-8")
                            st.markdown(
                                f"<div style='display: flex; align-items: center; justify-content: center; height: 100%; min-height: 120px; box-sizing: border-box;'>"
                                f"<img src='data:image/png;base64,{qr_b64}' style='width: 115px; height: 115px; border-radius: 12px; border: 1.5px solid rgba(255,255,255,0.08);' />"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        else:
                            st.info("Photo URL not available.")
    
                    # 4. Gaming-style vibe statistics
                    st.markdown("<p style='font-family: \"Space Grotesk\", sans-serif; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em; color: #666; margin: 0 0 6px 0; text-align: center;'>Vibe Statistics</p>", unsafe_allow_html=True)
                    for label, val in vibes.items():
                        st.markdown(
                            f"<div style='display: flex; justify-content: space-between; font-size: 0.76rem; margin-bottom: 1px;'>"
                            f"<span style='color: #888; font-weight: 500;'>{label}</span>"
                            f"<span style='color: #00d4ff; font-weight: 600; font-family: Space Grotesk;'>{val}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        val_str = str(val)
                        if "MAX" in val_str:
                            progress_val = 100
                        elif "CRITICAL" in val_str:
                            progress_val = 15
                        else:
                            try:
                                progress_val = int(val_str.replace("%", ""))
                            except ValueError:
                                progress_val = 50
                        st.progress(progress_val)
    
                    # 5. Full breakdown (Clean white labels)
                    with st.expander("Person 1 Full Breakdown"):
                        for e in sorted(
                            face_data["Emotions"],
                            key=lambda x: x["Confidence"], reverse=True,
                        ):
                            st.progress(
                                min(int(e["Confidence"]), 100),
                                text=f"{e['Type'].capitalize()}  "
                                     f"({e['Confidence']:.1f}%)",
                            )

def render_photostrip_page():
    # Title row: back button + title inline
    hdr_l, hdr_r = st.columns([1, 5], gap="small")
    with hdr_l:
        st.markdown('<div class="reset-btn" style="padding-top:6px;">', unsafe_allow_html=True)
        if st.button("← Home", key="ps_back"):
            st.session_state.app_page = "home"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with hdr_r:
        st.markdown(
            "<h1 style='"
            "font-family:Space Grotesk,sans-serif;"
            "font-size:2.2rem;font-weight:800;margin:0;"
            "letter-spacing:-0.04em;"
            "background:linear-gradient(135deg,#ff2d75 0%,#ff6b6b 40%,#6c3bff 100%);"
            "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
            "filter:drop-shadow(0 0 25px rgba(255,45,117,0.2));'>"
            "Photostrip Booth</h1>"
            "<p style='color:#555;margin-top:4px;font-size:.9rem;font-family:DM Sans,sans-serif;'>"
            "Crafted by <span style='background:linear-gradient(135deg,#ff2d75,#6c3bff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:600;'>Ankitha Jade</span>"
            " and <span style='background:linear-gradient(135deg,#ff2d75,#6c3bff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:600;'>Sadhana S</span></p>",
            unsafe_allow_html=True,
        )
    st.divider()
    
    # ═════════════════════════════════════════════════════════════════════════════
    #  STATE 1 — BEFORE CAPTURE
    # ═════════════════════════════════════════════════════════════════════════════
    
    if st.session_state.ps_mode == "capture":
        left, right = st.columns([3, 2], gap="large")
    
        # ── LEFT: Live Camera Feed ─────────────────────────────────────────────
        with left:
            st.markdown("#### 📷 Live Preview")
            ctx = webrtc_streamer(
                key=f"booth_{st.session_state.ps_camera_run_id}",
                desired_playing_state=True,
                mode=WebRtcMode.SENDRECV,
                video_processor_factory=StripVideoProcessor,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
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
                ctx.video_processor.filter_mode = st.session_state.ps_selected_filter
    
            st.divider()
    
            capture_ph = st.empty()
            status_ph  = st.empty()
    
            start_clicked = capture_ph.button(
                "Start Photostrip",
                key="start_capture", type="primary",
                use_container_width=True,
                disabled=st.session_state.ps_is_capturing,
            )
    
            if start_clicked:
                if not ctx.video_processor:
                    st.warning("Start the camera first!")
                elif ctx.video_processor.frame_bgr is None:
                    st.warning("Waiting for camera feed…")
                else:
                    st.session_state.ps_is_capturing = True
                    st.session_state.ps_captured_photos = []
                    st.rerun()
    
            # ── Capture sequence (blocking in main thread) ─────────────────────
            if st.session_state.ps_is_capturing:
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
                        "<div class='countdown-text'><span style='-webkit-text-fill-color: initial;'>📸</span>!</div>",
                        unsafe_allow_html=True,
                    )
    
                    # Grab frame
                    with ctx.video_processor._lock:
                        frame_bgr = ctx.video_processor.frame_bgr.copy()
                    frame_pil = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
                    st.session_state.ps_captured_photos.append(frame_pil)
                    time.sleep(0.5)
    
                status_ph.markdown(
                    "<div class='countdown-text' style='color:#38ef7d;'>Processing…</div>",
                    unsafe_allow_html=True,
                )
    
                # Composite the photostrip
                final_strip = create_photostrip(
                    st.session_state.ps_captured_photos,
                    st.session_state.ps_selected_strip,
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
                st.session_state.ps_final_strip  = final_strip
                st.session_state.ps_image_bytes  = img_bytes
                st.session_state.ps_file_name    = f"photostrip_{int(time.time())}.png"
                st.session_state.ps_photo_url    = photo_url
                st.session_state.ps_upload_error = upload_err
                st.session_state.ps_mode         = "result"
                st.session_state.ps_is_capturing = False
                st.rerun()
    
        # ── RIGHT: Strip Gallery + Capture Controls ────────────────────────────
        with right:
            st.markdown("#### 🎞️ Choose Your Strip")
    
            # Thumbnail gallery — 3 columns
            gallery_cols = st.columns(3)
            for idx, (strip_id, info) in enumerate(STRIP_TEMPLATES.items()):
                with gallery_cols[idx]:
                    is_active = (st.session_state.ps_selected_strip == strip_id)
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
                        st.session_state.ps_selected_strip = strip_id
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
                    is_sel = (st.session_state.ps_selected_filter == f_id)
                    if st.button(f_name, key=f"btn_flt_{f_id}", type="primary" if is_sel else "secondary", use_container_width=True):
                        st.session_state.ps_selected_filter = f_id
                        st.rerun()
    
            st.divider()
            st.markdown("#### 🚀 Ready to Shoot?")
            st.info("This will take **4 photos** in a row with the selected strip template.")
    
    
    
    # ═════════════════════════════════════════════════════════════════════════════
    #  STATE 2 — AFTER CAPTURE (Result Screen)
    # ═════════════════════════════════════════════════════════════════════════════
    
    elif st.session_state.ps_mode == "result":
        left, right = st.columns([2, 3], gap="large")
    
        # ── LEFT: Final Photostrip Preview ─────────────────────────────────────
        with left:
            st.markdown("#### 🎞️ Your Photostrip")
            # Display at 400px width — balanced size for laptop without overflow
            st.image(st.session_state.ps_final_strip, width=400)
    
        # ── RIGHT: QR Code + Retake ────────────────────────────────────────────
        with right:
            url = st.session_state.ps_photo_url
            if url and url != "#":
                st.markdown("#### 📱 Scan to Share & Download")
                qr_img = qrcode.make(url)
                qr_buf = BytesIO()
                qr_img.save(qr_buf, format="PNG")
                
                qr_b64 = base64.b64encode(qr_buf.getvalue()).decode("utf-8")
                st.markdown(
                    f"<div style='display: flex; align-items: center; justify-content: center; height: 300px; box-sizing: border-box;'>"
                    f"<img src='data:image/png;base64,{qr_b64}' style='width: 280px; height: 280px; border-radius: 12px; border: 2px solid rgba(255,45,117,0.3); box-shadow: 0 0 20px rgba(255,45,117,0.15);' />"
                    f"</div>",
                    unsafe_allow_html=True
                )
    
                st.caption("Scan with your phone to share or download your photostrip!")
            else:
                st.info("Photo URL not available (S3 upload may have failed).")
                if st.session_state.ps_upload_error:
                    st.error(f"Error: {st.session_state.ps_upload_error}")
    
            st.divider()
    
            # Retake button — positioned below QR in the right panel
            st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
            if st.button("🔄  Take Another Photo", key="reset", use_container_width=True):
                _reset_ps_session()
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

def main():
    _init_state()
    
    if st.session_state.app_page == "home":
        render_home_page()
    elif st.session_state.app_page == "photobooth":
        render_photobooth_page()
    elif st.session_state.app_page == "photostrip":
        render_photostrip_page()

if __name__ == "__main__":
    main()
