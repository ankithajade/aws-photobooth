"""
AFTER HOURS 1.0 — Standalone Photostrip Experience
===================================================
An Inter-College 24-Hour Technical Hackathon
Organized by: Department of CSE, DBIT × AWS Student Builder Group DBIT
Powered by Unstop | Co-powered by Tridha

Features:
  - Live webcam feed with WebRTC (4:3 ratio, selfie-mirrored)
  - 4 selectable photostrip templates including the official After Hours 1.0 frame
  - Real-time filters: Color, Black & White, Vintage/Retro
  - 4-photo capture sequence with animated countdown and screen flash effect
  - Precise layering of photographs beneath transparent PNG templates
  - Final photostrip generation and local PNG download
  - AWS S3 upload (supporting Streamlit secrets, environment variables, IAM roles)
  - Mobile QR code destination leading to an interactive responsive share page
  - Clean session reset and retake capability
"""

import base64
import os
import threading
import time
import uuid
import traceback
from io import BytesIO

import av
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, BotoCoreError
import cv2
import numpy as np
import qrcode
import streamlit as st
from PIL import Image
from streamlit_webrtc import WebRtcMode, webrtc_streamer, VideoHTMLAttributes

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION (Must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="After Hours 1.0 — Photostrip Booth",
    page_icon="🎞️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# VISUAL THEME & CSS — AFTER HOURS 1.0 (Dark Tech + Radiant Neon Orange)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

/* Base reset & typography */
html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
    color: #F1F5F9;
}

.stApp {
    background: #08090D;
    overflow-x: hidden;
}

/* Background tech grid overlay */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        linear-gradient(rgba(255, 85, 0, 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 85, 0, 0.025) 1px, transparent 1px);
    background-size: 50px 50px;
    pointer-events: none;
    z-index: 0;
}

/* Ambient glow orbs */
.glow-orb-top {
    position: fixed;
    width: 600px; height: 600px;
    top: -150px; right: -100px;
    background: radial-gradient(circle, rgba(255, 85, 0, 0.12) 0%, transparent 70%);
    border-radius: 50%;
    filter: blur(100px);
    pointer-events: none;
    z-index: 0;
}

.glow-orb-bottom {
    position: fixed;
    width: 500px; height: 500px;
    bottom: -150px; left: -100px;
    background: radial-gradient(circle, rgba(255, 120, 0, 0.08) 0%, transparent 70%);
    border-radius: 50%;
    filter: blur(120px);
    pointer-events: none;
    z-index: 0;
}

/* Top container breathing space */
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1300px;
}

/* Flash overlay on photo capture */
@keyframes flash-animation {
    0%   { opacity: 0; }
    15%  { opacity: 0.95; }
    100% { opacity: 0; }
}
.flash-active {
    position: fixed;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    background-color: #FFFFFF;
    z-index: 999999;
    pointer-events: none;
    animation: flash-animation 0.45s ease-out forwards;
}

/* Video element wrapper */
video {
    border-radius: 14px !important;
    border: 1px solid rgba(255, 85, 0, 0.3) !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6), 0 0 20px rgba(255, 85, 0, 0.15) !important;
    max-height: 420px;
    width: 100% !important;
    object-fit: contain;
    background: #000;
}

/* Global button styling */
.stButton > button {
    border-radius: 10px;
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    letter-spacing: 0.02em;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(255, 85, 0, 0.3);
}

/* Primary Action Button (High-Energy Cyber Orange) */
button[kind="primary"], .primary-btn button {
    background: linear-gradient(135deg, #FF4500 0%, #FF6A00 50%, #FFA000 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    padding: 0.8rem 1.4rem !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 18px rgba(255, 69, 0, 0.4) !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

button[kind="primary"]:hover, .primary-btn button:hover {
    background: linear-gradient(135deg, #FF5500 0%, #FF7B00 50%, #FFB000 100%) !important;
    box-shadow: 0 8px 28px rgba(255, 85, 0, 0.55) !important;
    transform: translateY(-2px) scale(1.01);
}

/* Secondary & Reset button */
.reset-btn > button, button[kind="secondary"] {
    background: rgba(22, 24, 34, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    color: #CBD5E1 !important;
}

.reset-btn > button:hover, button[kind="secondary"]:hover {
    border-color: #FF5500 !important;
    color: #FFFFFF !important;
    background: rgba(30, 33, 48, 0.9) !important;
}

/* Strip gallery card */
.strip-card {
    border-radius: 12px;
    border: 2px solid rgba(255, 255, 255, 0.08);
    padding: 6px;
    text-align: center;
    background: rgba(18, 20, 28, 0.7);
    backdrop-filter: blur(12px);
    transition: all 0.25s ease;
    cursor: pointer;
    margin-bottom: 6px;
}

.strip-card:hover {
    border-color: rgba(255, 85, 0, 0.5);
    box-shadow: 0 4px 18px rgba(255, 85, 0, 0.2);
    transform: translateY(-2px);
}

.strip-card.selected {
    border-color: #FF5500 !important;
    box-shadow: 0 0 20px rgba(255, 85, 0, 0.45), inset 0 0 10px rgba(255, 85, 0, 0.15) !important;
    background: rgba(30, 25, 25, 0.85);
}

/* Countdown & Capture feedback */
.countdown-box {
    background: rgba(18, 20, 28, 0.9);
    border: 1px solid rgba(255, 85, 0, 0.4);
    border-radius: 14px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
    margin: 12px 0;
}

.countdown-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.2rem;
    font-weight: 700;
    color: #FF8800;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.countdown-number {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 3.6rem;
    font-weight: 900;
    color: #FFFFFF;
    line-height: 1;
    margin: 6px 0;
    text-shadow: 0 0 20px rgba(255, 85, 0, 0.7);
}

/* Event Header Container */
.event-header {
    background: rgba(16, 18, 26, 0.85);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 85, 0, 0.25);
    border-radius: 16px;
    padding: 16px 24px;
    margin-bottom: 20px;
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.4);
}

/* Event Organizers Pill */
.org-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255, 85, 0, 0.12);
    border: 1px solid rgba(255, 85, 0, 0.3);
    padding: 4px 12px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    color: #FFA000;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

/* Event Title */
.event-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.2rem;
    font-weight: 900;
    margin: 6px 0 2px 0;
    letter-spacing: -0.02em;
    line-height: 1.15;
}

.event-title-highlight {
    background: linear-gradient(135deg, #FF4500 0%, #FF7B00 60%, #FFAA00 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 20px rgba(255, 85, 0, 0.35));
}

.event-subtitle {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.88rem;
    color: #94A3B8;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* Glass Card containers for content sections */
.glass-panel {
    background: rgba(16, 18, 26, 0.75);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 18px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    margin-bottom: 16px;
}

/* QR Code Card container */
.qr-card {
    background: #FFFFFF;
    border-radius: 18px;
    padding: 18px;
    display: inline-block;
    box-shadow: 0 15px 40px rgba(0, 0, 0, 0.5), 0 0 25px rgba(255, 85, 0, 0.2);
    border: 3px solid #FF5500;
}

/* Camera Live Indicator */
.camera-status-live {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    color: #22C55E;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.live-dot {
    width: 8px; height: 8px;
    background-color: #22C55E;
    border-radius: 50%;
    box-shadow: 0 0 10px #22C55E;
    animation: pulse 1.8s infinite;
}

@keyframes pulse {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
    70% { transform: scale(1.15); box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
}

hr {
    border-color: rgba(255, 255, 255, 0.08) !important;
}
</style>

<div class="glow-orb-top"></div>
<div class="glow-orb-bottom"></div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# AWS & S3 INTEGRATION HELPER
#
# Constraints honored:
#   - No hardcoded credentials in source code.
#   - Safe retrieval from st.secrets or os.environ.
#   - Supports AWS_SESSION_TOKEN for temporary credentials.
#   - Generates presigned URLs for private S3 buckets without making them public.
#   - Gracefully degrades without crashing if AWS is not configured.
# ─────────────────────────────────────────────────────────────────────────────

def get_s3_config():
    """Retrieve S3 credentials and settings from secrets or environment."""
    key = None
    secret = None
    token = None
    region = "ap-south-1"
    bucket = ""
    use_public = False

    # 1. Check Streamlit secrets
    if hasattr(st, "secrets"):
        try:
            key = st.secrets.get("AWS_ACCESS_KEY_ID")
            secret = st.secrets.get("AWS_SECRET_ACCESS_KEY")
            token = st.secrets.get("AWS_SESSION_TOKEN")
            region = st.secrets.get("AWS_DEFAULT_REGION", st.secrets.get("AWS_REGION", "ap-south-1"))
            bucket = st.secrets.get("S3_BUCKET", "")
            use_public = st.secrets.get("S3_USE_PUBLIC_URLS", False)
        except Exception:
            pass

    # 2. Check environment variables as fallback
    if not key:
        key = os.environ.get("AWS_ACCESS_KEY_ID")
    if not secret:
        secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not token:
        token = os.environ.get("AWS_SESSION_TOKEN")
    if not bucket:
        bucket = os.environ.get("S3_BUCKET", "")
    if os.environ.get("AWS_DEFAULT_REGION"):
        region = os.environ.get("AWS_DEFAULT_REGION")
    elif os.environ.get("AWS_REGION"):
        region = os.environ.get("AWS_REGION")

    return {
        "access_key": key,
        "secret_key": secret,
        "token": token,
        "region": region,
        "bucket": bucket,
        "use_public_urls": use_public,
    }


def get_s3_client():
    """Initialize a boto3 S3 client safely without logging sensitive info."""
    cfg = get_s3_config()
    region = cfg["region"] or "ap-south-1"

    # Regional endpoint and SigV4 configuration are essential for non-us-east-1 buckets
    # to avoid 'SignatureDoesNotMatch' / 'AuthorizationQueryParametersError' caused by
    # default global s3.amazonaws.com virtual host routing.
    s3_config = Config(
        region_name=region,
        signature_version="s3v4",
        s3={"addressing_style": "virtual"},
    )
    endpoint_url = f"https://s3.{region}.amazonaws.com"

    if cfg["access_key"] and cfg["secret_key"]:
        kwargs = {
            "service_name": "s3",
            "aws_access_key_id": cfg["access_key"],
            "aws_secret_access_key": cfg["secret_key"],
            "region_name": region,
            "endpoint_url": endpoint_url,
            "config": s3_config,
        }
        if cfg["token"]:
            kwargs["aws_session_token"] = cfg["token"]
        try:
            return boto3.client(**kwargs), cfg["bucket"], region, cfg["use_public_urls"]
        except Exception:
            return None, cfg["bucket"], region, cfg["use_public_urls"]

    # Fallback to AWS default credentials chain (IAM Role, ECS task, ~/.aws/credentials)
    try:
        return (
            boto3.client("s3", region_name=region, endpoint_url=endpoint_url, config=s3_config),
            cfg["bucket"],
            region,
            cfg["use_public_urls"],
        )
    except Exception:
        return None, cfg["bucket"], region, cfg["use_public_urls"]


# ─────────────────────────────────────────────────────────────────────────────
# STRIP TEMPLATE REGISTRY
#
# Dimensions: 736 × 1308 canvas
# Includes the official After Hours 1.0 template and 3 legacy templates.
# ─────────────────────────────────────────────────────────────────────────────

STRIP_TEMPLATES = {
    "strip-afterhours": {
        "name": "After Hours (Official)",
        "path": "assets/strip-afterhours.png",
        "slots": [
            {"x": 175, "y": 80,  "w": 386, "h": 260},
            {"x": 175, "y": 370, "w": 386, "h": 260},
            {"x": 175, "y": 660, "w": 386, "h": 260},
            {"x": 175, "y": 950, "w": 386, "h": 260},
        ],
    },
    "strip-1": {
        "name": "Retro Event",
        "path": "assets/strip-1.png",
        "slots": [
            {"x": 186, "y":  27, "w": 373, "h": 289},
            {"x": 183, "y": 329, "w": 376, "h": 291},
            {"x": 182, "y": 633, "w": 377, "h": 296},
            {"x": 179, "y": 942, "w": 380, "h": 296},
        ],
    },
    "strip-2": {
        "name": "Neon Party",
        "path": "assets/strip-2.png",
        "slots": [
            {"x": 180, "y":  41, "w": 376, "h": 280},
            {"x": 180, "y": 354, "w": 376, "h": 281},
            {"x": 179, "y": 670, "w": 375, "h": 281},
            {"x": 180, "y": 983, "w": 376, "h": 281},
        ],
    },
    "strip-3": {
        "name": "Classic Film",
        "path": "assets/strip-3.png",
        "slots": [
            {"x": 206, "y":  60, "w": 357, "h": 246},
            {"x": 206, "y": 319, "w": 357, "h": 246},
            {"x": 207, "y": 575, "w": 356, "h": 264},
            {"x": 207, "y": 852, "w": 357, "h": 237},
        ],
    },
}

TARGET_RATIO = 4 / 3  # Standard landscape 4:3 webcam aspect ratio

# ─────────────────────────────────────────────────────────────────────────────
# IMAGE FILTERS
# ─────────────────────────────────────────────────────────────────────────────

def apply_bw_filter(img: np.ndarray) -> np.ndarray:
    """High-contrast grayscale filter."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=1.15, beta=-5)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


# Precompute lookup table for Vintage / Retro filter for 0 latency
_VINTAGE_LUT = np.zeros((256, 1, 3), dtype=np.uint8)
for i in range(256):
    val = (i * 0.9) + 15
    b = min(255, max(0, val * 0.8))   # Reduced blue
    g = min(255, max(0, val * 1.0))   # Balanced green
    r = min(255, max(0, val * 1.2))   # Warm amber/red boost
    _VINTAGE_LUT[i, 0, 0] = int(b)
    _VINTAGE_LUT[i, 0, 1] = int(g)
    _VINTAGE_LUT[i, 0, 2] = int(r)


def apply_vintage_filter(img: np.ndarray) -> np.ndarray:
    """Warm nostalgic film look using precomputed LUT."""
    return cv2.LUT(img, _VINTAGE_LUT)


# ─────────────────────────────────────────────────────────────────────────────
# WEBRTC VIDEO PROCESSOR
# Crops webcam feed to 4:3 landscape, selfie-mirrors, and applies live filters.
# ─────────────────────────────────────────────────────────────────────────────

class StripVideoProcessor:
    def __init__(self):
        self.frame_bgr = None
        self._lock = threading.Lock()
        self.filter_mode = "color"

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)  # Selfie mirror
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

        # Real-time filter application
        mode = getattr(self, "filter_mode", "color")
        if mode == "bw":
            cropped = apply_bw_filter(cropped)
        elif mode == "vintage":
            cropped = apply_vintage_filter(cropped)

        with self._lock:
            self.frame_bgr = cropped

        return av.VideoFrame.from_ndarray(cropped, format="bgr24")


# ─────────────────────────────────────────────────────────────────────────────
# COMPOSITING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def fit_cover(image: Image.Image, tw: int, th: int) -> Image.Image:
    """Scale + center-crop image to exactly (tw × th) maintaining aspect ratio."""
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
    """Cache-load strip template PNG to optimize memory and disk I/O."""
    return Image.open(template_path).convert("RGBA")


@st.cache_resource
def _load_gallery_thumb(path: str) -> Image.Image:
    """Cache-load and downscale template thumbnail for the gallery."""
    thumb = Image.open(path).convert("RGBA")
    thumb.thumbnail((140, 240), Image.Resampling.LANCZOS)
    return thumb


def create_photostrip(photos: list, template_id: str) -> Image.Image:
    """
    Compositing pipeline:
      1. Create canvas matching template dimensions with solid dark base.
      2. Paste the 4 captured photos into each defined slot using fit_cover.
      3. Alpha-composite the transparent PNG template on top.
    """
    cfg = STRIP_TEMPLATES.get(template_id, STRIP_TEMPLATES["strip-afterhours"])
    template_img = _load_template(cfg["path"])
    tw, th = template_img.size

    canvas = Image.new("RGBA", (tw, th), (14, 15, 20, 255))

    for i, photo in enumerate(photos):
        if i >= len(cfg["slots"]):
            break
        s = cfg["slots"][i]
        fitted = fit_cover(photo, s["w"], s["h"])
        canvas.paste(fitted.convert("RGB"), (s["x"], s["y"]))

    return Image.alpha_composite(canvas, template_img)


# ─────────────────────────────────────────────────────────────────────────────
# MOBILE SHARE PAGE GENERATOR (Themed for AFTER HOURS 1.0)
# ─────────────────────────────────────────────────────────────────────────────

def generate_share_page(image_url: str) -> str:
    """Generate mobile-friendly HTML landing page matching the hackathon theme."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AFTER HOURS 1.0 — Photostrip Memory</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&family=Space+Grotesk:wght@600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #08090D;
      color: #F1F5F9;
      font-family: 'Outfit', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 20px 16px;
      position: relative;
      overflow-x: hidden;
    }}
    body::before {{
      content: '';
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background-image:
        linear-gradient(rgba(255, 85, 0, 0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 85, 0, 0.04) 1px, transparent 1px);
      background-size: 32px 32px;
      pointer-events: none;
      z-index: 0;
    }}
    .glow-blob {{
      position: fixed;
      border-radius: 50%;
      filter: blur(80px);
      opacity: 0.25;
      pointer-events: none;
      z-index: 0;
    }}
    .blob-1 {{ width: 320px; height: 320px; top: -50px; right: -50px; background: #FF4500; }}
    .blob-2 {{ width: 300px; height: 300px; bottom: -50px; left: -50px; background: #FF8800; }}
    .container {{
      max-width: 440px;
      width: 100%;
      background: rgba(16, 18, 26, 0.88);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 85, 0, 0.3);
      border-radius: 24px;
      padding: 24px 20px;
      text-align: center;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7), 0 0 30px rgba(255, 85, 0, 0.15);
      position: relative;
      z-index: 1;
    }}
    .badge {{
      display: inline-block;
      background: rgba(255, 85, 0, 0.15);
      border: 1px solid rgba(255, 85, 0, 0.4);
      padding: 4px 12px;
      border-radius: 20px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      font-weight: 700;
      color: #FFA000;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    h1 {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1.8rem;
      font-weight: 900;
      letter-spacing: -0.02em;
      color: #FFFFFF;
      margin-bottom: 4px;
    }}
    h1 span {{
      background: linear-gradient(135deg, #FF4500, #FFA000);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    p.subtitle {{
      font-family: 'JetBrains Mono', monospace;
      color: #94A3B8;
      font-size: 0.8rem;
      letter-spacing: 0.06em;
      margin-bottom: 20px;
      text-transform: uppercase;
    }}
    .image-preview {{
      width: 100%;
      border-radius: 16px;
      overflow: hidden;
      margin-bottom: 20px;
      background: #000;
      border: 2px solid rgba(255, 85, 0, 0.35);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
      display: flex;
      justify-content: center;
    }}
    .image-preview img {{
      max-height: 52vh;
      width: auto;
      object-fit: contain;
      display: block;
    }}
    .btn {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      width: 100%;
      padding: 15px;
      border-radius: 12px;
      font-size: 1rem;
      font-weight: 700;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      cursor: pointer;
      text-decoration: none;
      box-sizing: border-box;
      margin-bottom: 10px;
      transition: all 0.2s ease;
      border: none;
    }}
    .btn-share {{
      background: linear-gradient(135deg, #FF4500 0%, #FF6A00 50%, #FFA000 100%);
      color: #FFFFFF;
      box-shadow: 0 4px 18px rgba(255, 69, 0, 0.4);
    }}
    .btn-share:active {{ transform: scale(0.98); opacity: 0.9; }}
    .btn-download {{
      background: rgba(26, 30, 42, 0.9);
      color: #F1F5F9;
      border: 1px solid rgba(255, 255, 255, 0.15);
    }}
    .btn-download:active {{ transform: scale(0.98); }}
    .footer {{
      margin-top: 18px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      color: #64748B;
      letter-spacing: 0.04em;
    }}
    .footer-highlight {{ color: #FF8800; }}
  </style>
</head>
<body>
  <div class="glow-blob blob-1"></div>
  <div class="glow-blob blob-2"></div>
  <div class="container">
    <div class="badge">DBIT × AWS SBG</div>
    <h1>AFTER <span>HOURS 1.0</span></h1>
    <p class="subtitle">Code Beyond The Clock • 2026</p>
    <div class="image-preview">
      <img id="strip-img" src="{image_url}" alt="After Hours Photostrip">
    </div>
    <button class="btn btn-share" id="share-btn">📤 Share Photostrip</button>
    <a href="{image_url}" download="afterhours_photostrip.png" class="btn btn-download" id="download-btn">
      📥 Download Photostrip
    </a>
    <div class="footer">
      Dept of CSE, DBIT × <span class="footer-highlight">AWS Student Builder Group</span>
    </div>
  </div>
  <script>
    const shareBtn = document.getElementById('share-btn');
    const imageUrl = "{image_url}";
    shareBtn.addEventListener('click', async () => {{
      if (navigator.share) {{
        try {{
          const response = await fetch(imageUrl);
          const blob = await response.blob();
          const file = new File([blob], 'afterhours_photostrip.png', {{ type: 'image/png' }});
          if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
            await navigator.share({{
              files: [file],
              title: 'AFTER HOURS 1.0 Photostrip',
              text: 'Captured at After Hours 1.0 Hackathon! #AfterHours #AWSSBG #DBIT',
            }});
            return;
          }}
        }} catch (err) {{
          console.warn("Direct file share fallback:", err);
        }}
        try {{
          await navigator.share({{
            title: 'AFTER HOURS 1.0 Photostrip',
            text: 'Captured at After Hours 1.0 Hackathon! #AfterHours #AWSSBG #DBIT',
            url: window.location.href,
          }});
        }} catch (err) {{
          console.warn("URL share failed:", err);
        }}
      }} else {{
        alert("Native share is not available on this browser. Use the Download button to save your strip!");
      }}
    }});
  </script>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# S3 UPLOAD HELPER
#
# Generates presigned URLs if direct public read access is not configured.
# ─────────────────────────────────────────────────────────────────────────────

def upload_to_s3(img_bytes: bytes) -> tuple[str | None, str | None]:
    """
    Upload photostrip PNG and responsive companion HTML page to S3.

    Returns:
        (share_url, error_message)
    """
    s3_client, bucket, region, use_public = get_s3_client()

    if not s3_client:
        return None, "AWS S3 client could not be initialized. Please configure credentials in .streamlit/secrets.toml."

    if not bucket:
        return None, "S3_BUCKET is not set in .streamlit/secrets.toml or environment variables."

    ts = int(time.time())
    uid = uuid.uuid4().hex[:6]
    png_key = f"photostrips/strip_{ts}_{uid}.png"
    html_key = f"photostrips/strip_{ts}_{uid}.html"

    try:
        # 1. Upload the PNG image
        s3_client.put_object(
            Bucket=bucket,
            Key=png_key,
            Body=img_bytes,
            ContentType="image/png",
        )

        # 2. Determine image access URL for the HTML page
        if use_public:
            img_view_url = f"https://{bucket}.s3.{region}.amazonaws.com/{png_key}"
        else:
            # Presigned URL (valid for 48 hours for hackathon duration)
            img_view_url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": png_key},
                ExpiresIn=172800,  # 48 hours
            )

        # 3. Generate and upload the companion HTML share page
        html_content = generate_share_page(img_view_url)
        s3_client.put_object(
            Bucket=bucket,
            Key=html_key,
            Body=html_content.encode("utf-8"),
            ContentType="text/html",
        )

        # 4. Determine share destination URL (Presigned or direct public)
        if use_public:
            share_url = f"https://{bucket}.s3.{region}.amazonaws.com/{html_key}"
        else:
            share_url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": html_key},
                ExpiresIn=172800,  # 48 hours
            )

        return share_url, None

    except (ClientError, BotoCoreError) as exc:
        err_msg = str(exc)
        # Avoid leaking full raw credentials in UI
        if "AccessDenied" in err_msg or "403" in err_msg:
            return None, "S3 Access Denied: Check bucket permissions or IAM policy for PutObject."
        elif "NoSuchBucket" in err_msg or "404" in err_msg:
            return None, f"S3 Bucket '{bucket}' was not found. Please verify S3_BUCKET in secrets."
        return None, f"S3 Upload failed: {err_msg}"
    except Exception as exc:
        return None, f"Unexpected error during upload: {str(exc)}"


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULTS = {
    "mode":            "capture",          # "capture" | "result"
    "captured_photos": [],                 # list[PIL.Image]
    "camera_run_id":   0,                  # int incremented on reset
    "final_strip":     None,               # PIL.Image
    "image_bytes":     None,               # bytes
    "file_name":       None,               # str
    "photo_url":       None,               # str or None
    "is_capturing":    False,              # bool
    "selected_strip":  "strip-afterhours", # default template
    "selected_filter": "color",            # "color" | "bw" | "vintage"
    "upload_error":    None,               # str or None
}

for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# Module-level static WebRTC configuration (avoids object reference churn across reruns)
RTC_CONFIGURATION = {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
MEDIA_STREAM_CONSTRAINTS = {
    "video": {
        "width": {"ideal": 1280},
        "height": {"ideal": 720},
        "frameRate": {"ideal": 30},
    },
    "audio": False,
}


def _reset_session(new_camera_session: bool = False):
    """Reset capture state for a clean new strip session while keeping camera stable."""
    if new_camera_session:
        # Gracefully stop existing worker before starting a new camera session
        old_key = f"photostrip_cam_{st.session_state.camera_run_id}"
        if old_key in st.session_state:
            old_ctx = st.session_state[old_key]
            if hasattr(old_ctx, "_get_worker"):
                worker = old_ctx._get_worker()
                if worker:
                    try:
                        worker.stop()
                    except Exception:
                        pass
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
# TOP BRANDING & EVENT HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="event-header">
  <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
    <div>
      <div class="org-pill">
        <span>Department of CSE, DBIT</span>
        <span>×</span>
        <span>AWS Student Builder Group DBIT</span>
      </div>
      <div class="event-title">
        AFTER <span class="event-title-highlight">HOURS 1.0</span>
      </div>
      <div class="event-subtitle">
        Code Beyond The Clock &nbsp;•&nbsp; 24-Hour Inter-College Hackathon &nbsp;•&nbsp; 30–31 October 2026
      </div>
    </div>
    <div style="text-align: right; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #64748B; padding-top: 6px;">
      <div>POWERED BY <strong style="color: #F1F5F9;">UNSTOP</strong></div>
      <div>CO-POWERED BY <strong style="color: #FFA000;">TRIDHA</strong></div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
#  STATE 1 — BEFORE & DURING CAPTURE
# ═════════════════════════════════════════════════════════════════════════════

if st.session_state.mode == "capture":
    col_left, col_right = st.columns([3, 2], gap="large")

    # ── LEFT PANEL: Live Camera Feed & Capture Trigger ──────────────────────
    with col_left:
        # Camera streamer with stable key and no auto-reconnect infinite loop
        cam_key = f"photostrip_cam_{st.session_state.camera_run_id}"

        ctx = webrtc_streamer(
            key=cam_key,
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=StripVideoProcessor,
            rtc_configuration=RTC_CONFIGURATION,
            media_stream_constraints=MEDIA_STREAM_CONSTRAINTS,
            async_processing=True,
            video_html_attrs=VideoHTMLAttributes(
                autoPlay=True,
                controls=False,
                style={
                    "maxHeight": "420px",
                    "width": "100%",
                    "maxWidth": "100%",
                    "borderRadius": "14px",
                    "background": "#000",
                    "display": "block",
                    "margin": "0 auto",
                },
                muted=True,
                playsInline=True,
            ),
        )

        is_cam_active = bool(ctx.state and ctx.state.playing)
        status_html = (
            '<span class="camera-status-live"><span class="live-dot"></span> LIVE 4:3 FEED</span>'
            if is_cam_active
            else '<span style="color:#94A3B8; font-family:\'JetBrains Mono\',monospace; font-size:0.75rem;">● CLICK START TO OPEN CAMERA</span>'
        )

        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <h4 style="margin:0; font-family:'Space Grotesk',sans-serif; color:#F8FAFC;">📷 Live Camera</h4>
          {status_html}
        </div>
        """, unsafe_allow_html=True)

        # Synchronize live filter on video processor
        if ctx.video_processor:
            ctx.video_processor.filter_mode = st.session_state.selected_filter

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        capture_btn_placeholder = st.empty()
        status_placeholder = st.empty()

        start_clicked = capture_btn_placeholder.button(
            "🚀 Start Photostrip (4 Photos)",
            key="start_capture",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.is_capturing,
        )

        if start_clicked:
            if not ctx.state.playing or not ctx.video_processor:
                st.warning("⚠️ Please start your camera by clicking 'START' above first.")
            elif ctx.video_processor.frame_bgr is None:
                st.warning("⏳ Waiting for camera feed to initialize...")
            else:
                st.session_state.is_capturing = True
                st.session_state.captured_photos = []
                st.rerun()

        # ── Capture sequence execution ─────────────────────────────────────
        if st.session_state.is_capturing:
            capture_btn_placeholder.empty()

            for photo_num in range(1, 5):
                # 3-second countdown
                for countdown in range(3, 0, -1):
                    status_placeholder.markdown(
                        f"""
                        <div class="countdown-box">
                          <div class="countdown-title">Capturing Photo {photo_num} of 4</div>
                          <div class="countdown-number">{countdown}</div>
                          <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#94A3B8;">GET READY & SMILE!</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    time.sleep(1.0)

                # Flash visual effect
                st.markdown("<div class='flash-active'></div>", unsafe_allow_html=True)
                status_placeholder.markdown(
                    f"""
                    <div class="countdown-box" style="border-color:#FFFFFF;">
                      <div class="countdown-title" style="color:#FFFFFF;">Photo {photo_num}/4</div>
                      <div class="countdown-number" style="color:#FF5500;">📸</div>
                      <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#22C55E;">CAPTURED!</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Capture current frame securely from lock
                with ctx.video_processor._lock:
                    frame_bgr = ctx.video_processor.frame_bgr.copy()

                frame_pil = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
                st.session_state.captured_photos.append(frame_pil)
                time.sleep(0.5)

            status_placeholder.markdown(
                """
                <div class="countdown-box" style="border-color:#FF8800;">
                  <div class="countdown-title" style="color:#FF8800;">Compositing Photostrip...</div>
                  <div class="countdown-number" style="font-size:2rem; margin:10px 0;">⚡</div>
                  <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#CBD5E1;">Layering photos onto template</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Composite the 4 photos into the selected template
            final_strip = create_photostrip(
                st.session_state.captured_photos,
                st.session_state.selected_strip,
            )

            # Export to PNG bytes
            buf = BytesIO()
            final_strip.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            # Upload to S3 (if configured)
            photo_url, upload_err = upload_to_s3(img_bytes)

            # Save results into session state
            st.session_state.final_strip = final_strip
            st.session_state.image_bytes = img_bytes
            st.session_state.file_name = f"afterhours_photostrip_{int(time.time())}.png"
            st.session_state.photo_url = photo_url
            st.session_state.upload_error = upload_err
            st.session_state.mode = "result"
            st.session_state.is_capturing = False
            st.rerun()

    # ── RIGHT PANEL: Template Gallery & Filter Selection ───────────────────
    with col_right:
        st.markdown("""
        <h4 style="margin:0 0 10px 0; font-family:'Space Grotesk',sans-serif; color:#F8FAFC;">
          🎞️ Select Strip Template
        </h4>
        """, unsafe_allow_html=True)

        gallery_cols = st.columns(4)
        for idx, (strip_id, info) in enumerate(STRIP_TEMPLATES.items()):
            with gallery_cols[idx]:
                is_active = (st.session_state.selected_strip == strip_id)
                card_css = "selected" if is_active else ""

                # Load cached thumbnail
                thumb = _load_gallery_thumb(info["path"])
                t_buf = BytesIO()
                thumb.save(t_buf, format="PNG")
                t_b64 = base64.b64encode(t_buf.getvalue()).decode("utf-8")

                st.markdown(
                    f"""
                    <div class="strip-card {card_css}">
                      <img src="data:image/png;base64,{t_b64}" style="width:100%; border-radius:6px; display:block;">
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                btn_label = f"✓ {info['name']}" if is_active else info["name"]
                if st.button(btn_label, key=f"sel_{strip_id}", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.selected_strip = strip_id
                    st.rerun()

        st.markdown("<hr style='margin: 18px 0;'>", unsafe_allow_html=True)

        st.markdown("""
        <h4 style="margin:0 0 10px 0; font-family:'Space Grotesk',sans-serif; color:#F8FAFC;">
          🎨 Select Photo Filter
        </h4>
        """, unsafe_allow_html=True)

        filter_cols = st.columns(3)
        filters = [
            ("color", "🎨 Color"),
            ("bw", "🖤 B&W"),
            ("vintage", "📼 Vintage"),
        ]

        for idx, (f_id, f_label) in enumerate(filters):
            with filter_cols[idx]:
                is_sel = (st.session_state.selected_filter == f_id)
                if st.button(
                    f_label,
                    key=f"flt_{f_id}",
                    type="primary" if is_sel else "secondary",
                    use_container_width=True,
                ):
                    st.session_state.selected_filter = f_id
                    st.rerun()

        st.markdown("<hr style='margin: 18px 0;'>", unsafe_allow_html=True)

        # Experience instructions
        st.markdown("""
        <div class="glass-panel" style="padding: 14px 16px;">
          <div style="font-family:'Space Grotesk',sans-serif; font-weight:700; color:#FF8800; font-size:0.95rem; margin-bottom:6px;">
            ⚡ HOW IT WORKS
          </div>
          <ol style="margin:0 0 0 18px; padding:0; font-size:0.85rem; color:#94A3B8; line-height:1.6;">
            <li>Pick your preferred <strong>template</strong> and <strong>filter</strong>.</li>
            <li>Click <strong>Start Photostrip</strong> to begin the 4-shot sequence.</li>
            <li>Each photo has a 3-second countdown with screen flash feedback.</li>
            <li>Get a finished strip with QR code to save & share on your phone!</li>
          </ol>
        </div>
        """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
#  STATE 2 — RESULT & SHARING SCREEN
# ═════════════════════════════════════════════════════════════════════════════

elif st.session_state.mode == "result":
    res_left, res_right = st.columns([1, 1], gap="large")

    # ── LEFT: Finished Photostrip Preview ──────────────────────────────────
    with res_left:
        st.markdown("""
        <h4 style="margin:0 0 12px 0; font-family:'Space Grotesk',sans-serif; color:#F8FAFC;">
          🎞️ Your Hackathon Photostrip
        </h4>
        """, unsafe_allow_html=True)

        if st.session_state.final_strip:
            st.image(
                st.session_state.final_strip,
                width=380,
                caption="AFTER HOURS 1.0 • DBIT × AWS SBG",
            )

    # ── RIGHT: QR Code, Direct Download & Retake Controls ──────────────────
    with res_right:
        url = st.session_state.photo_url

        if url:
            st.markdown("""
            <h4 style="margin:0 0 6px 0; font-family:'Space Grotesk',sans-serif; color:#F8FAFC;">
              📱 Scan with Your Phone
            </h4>
            <p style="color:#94A3B8; font-size:0.88rem; margin-bottom:14px;">
              Scan the QR code to open your mobile share page, download, or share with friends!
            </p>
            """, unsafe_allow_html=True)

            # Generate high-contrast QR Code with clean white container
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="#000000", back_color="#FFFFFF")

            qr_buf = BytesIO()
            qr_img.save(qr_buf, format="PNG")

            st.markdown('<div class="qr-card">', unsafe_allow_html=True)
            st.image(qr_buf.getvalue(), width=240)
            st.markdown('</div>', unsafe_allow_html=True)

            st.link_button("🔗 Open Mobile Share Page", url, use_container_width=True)

        else:
            # Informational card when S3 is unavailable or failed
            st.markdown("""
            <div class="glass-panel" style="border-color: rgba(255, 170, 0, 0.4);">
              <h4 style="margin:0 0 6px 0; color:#FFA000; font-family:'Space Grotesk',sans-serif;">
                💾 Cloud Storage Status
              </h4>
              <p style="font-size:0.88rem; color:#CBD5E1; margin-bottom:8px;">
                Your photostrip was successfully generated! Cloud QR sharing is currently inactive.
              </p>
            """, unsafe_allow_html=True)

            if st.session_state.upload_error:
                st.caption(f"Details: {st.session_state.upload_error}")
            else:
                st.caption("To enable QR phone scanning, add S3 credentials to .streamlit/secrets.toml.")

            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr style='margin: 18px 0;'>", unsafe_allow_html=True)

        # Direct Local Download Button (always available regardless of S3 status)
        if st.session_state.image_bytes:
            st.download_button(
                label="📥 Download Photostrip (PNG)",
                data=st.session_state.image_bytes,
                file_name=st.session_state.file_name or "afterhours_photostrip.png",
                mime="image/png",
                type="primary",
                use_container_width=True,
            )

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        # Retake / Take another strip button
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("🔄 Take Another Strip", key="reset_btn", use_container_width=True):
            _reset_session()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
