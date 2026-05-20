import os

with open('app.py', 'r', encoding='utf-8') as f:
    app_lines = f.readlines()

with open('photostrip.py', 'r', encoding='utf-8') as f:
    strip_lines = f.readlines()

def get_block(lines, start_str, end_str=None, include_end=False):
    start_idx = -1
    for i, l in enumerate(lines):
        if l.startswith(start_str):
            start_idx = i
            break
    if start_idx == -1: return []
    
    if end_str is None:
        return lines[start_idx:]
        
    end_idx = -1
    for i in range(start_idx + 1, len(lines)):
        if lines[i].startswith(end_str):
            end_idx = i
            break
            
    if end_idx == -1: return lines[start_idx:]
    return lines[start_idx:end_idx + (1 if include_end else 0)]

# 1. Imports from both
imports = """import base64
import threading
import time
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

"""

# 2. Page Config
page_config = """st.set_page_config(
    page_title="AI Photo Booth ✨",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="collapsed",
)
"""

# 3. CSS & Global HTML (from app.py) + added photostrip CSS classes
app_css_block_start = [i for i, l in enumerate(app_lines) if l.startswith('st.markdown("""')][0]
app_css_block_end = [i for i, l in enumerate(app_lines) if l.startswith('""", unsafe_allow_html=True)')][0]
css_and_html = "".join(app_lines[app_css_block_start:app_css_block_end])

photostrip_extra_css = """
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
.home-card:hover {
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
"""

css_and_html = css_and_html.replace("</style>", photostrip_extra_css + "\n</style>") + '""", unsafe_allow_html=True)\n'

# 4. JS layout fix, AWS Clients, and common helpers (from app.py)
js_start = [i for i, l in enumerate(app_lines) if "components.html" in l][0]
aws_start = [i for i, l in enumerate(app_lines) if l.startswith('_KEY    = ')][0]
generate_share_start = [i for i, l in enumerate(app_lines) if l.startswith('def generate_share_page(')][0]
init_state_start = [i for i, l in enumerate(app_lines) if l.startswith('def _init_state():')][0]

app_backend_logic = "".join(app_lines[js_start:init_state_start])

# 5. Backend Logic from photostrip.py (Templates, Filters, Processor, upload)
strip_templates_start = [i for i, l in enumerate(strip_lines) if l.startswith('STRIP_TEMPLATES = {')][0]
strip_state_start = [i for i, l in enumerate(strip_lines) if l.startswith('_DEFAULTS = {')][0]

strip_backend = "".join(strip_lines[strip_templates_start:strip_state_start])
# Rename generate_share_page in photostrip backend
strip_backend = strip_backend.replace("def generate_share_page(", "def generate_photostrip_share_page(")
strip_backend = strip_backend.replace("html_body = generate_share_page(raw_url)", "html_body = generate_photostrip_share_page(raw_url)")

# 6. Combined State Initialization
combined_init_state = """
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

"""

# 7. Render Home Page
home_page = """
def render_home_page():
    st.markdown(
        "<h1 style='text-align:center;"
        "font-family:Space Grotesk,sans-serif;"
        "font-size:3.5rem;font-weight:800;margin-bottom:0;"
        "letter-spacing:-0.04em;"
        "background:linear-gradient(135deg,#ff2d75 0%,#ff6b6b 40%,#6c3bff 100%);"
        "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
        "filter:drop-shadow(0 0 25px rgba(255,45,117,0.2));'>"
        "AI Photo Booth</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; font-size:1.2rem; color:#a0a0b8; margin-top:5px; font-weight:500; font-family:Space Grotesk, sans-serif;'>"
        "AWS Student Builder Group, DBIT &nbsp;•&nbsp; <span style='color:#ff6b6b;'>Vignanotsava 2k26</span>"
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([1, 4, 4, 1], gap="large")
    
    with col2:
        st.markdown('<div class="home-card">', unsafe_allow_html=True)
        st.markdown('<div class="home-card-icon">📸</div>', unsafe_allow_html=True)
        st.markdown('<div class="home-card-title">Photobooth</div>', unsafe_allow_html=True)
        st.markdown('<div class="home-card-desc">Single frame capture with AI Personality Analysis, Vibe Check, and custom event frames.</div>', unsafe_allow_html=True)
        if st.button("Enter Photobooth", key="btn_go_pb", type="primary", use_container_width=True):
            st.session_state.app_page = "photobooth"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col3:
        st.markdown('<div class="home-card">', unsafe_allow_html=True)
        st.markdown('<div class="home-card-icon">🎞️</div>', unsafe_allow_html=True)
        st.markdown('<div class="home-card-title">Photostrip</div>', unsafe_allow_html=True)
        st.markdown('<div class="home-card-desc">Classic 4-photo strip capture with vintage/B&W filters and printable layouts.</div>', unsafe_allow_html=True)
        if st.button("Enter Photostrip", key="btn_go_ps", type="primary", use_container_width=True):
            st.session_state.app_page = "photostrip"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

"""

# 8. Render Photobooth Page
# We extract the UI from app.py. It starts after _init_state()
app_ui_start = [i for i, l in enumerate(app_lines) if l.startswith('if not st.session_state.captured:')][0]

app_ui = "".join(app_lines[app_ui_start:])
# Add back button and indentation
app_ui = app_ui.replace("\\n", "\\\\n") # escape newlines just in case, wait, join handles it.
app_ui = "\n".join("    " + line for line in app_ui.splitlines())

photobooth_page = f"""
def render_photobooth_page():
    # Back button
    st.markdown('<div class="reset-btn" style="margin-bottom: 20px;">', unsafe_allow_html=True)
    if st.button("⬅️ Back to Home", key="pb_back"):
        st.session_state.app_page = "home"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

{app_ui}
"""

# 9. Render Photostrip Page
# Extract UI from photostrip.py. It starts with HEADER
strip_ui_start = [i for i, l in enumerate(strip_lines) if l.startswith('st.markdown(') and 'Photostrip Booth' in "".join(strip_lines[i:i+5])][0]

strip_ui = "".join(strip_lines[strip_ui_start:])
# Replace session state variables with ps_ prefix for specific ones
strip_ui = strip_ui.replace("st.session_state.mode", "st.session_state.ps_mode")
strip_ui = strip_ui.replace("st.session_state.camera_run_id", "st.session_state.ps_camera_run_id")
strip_ui = strip_ui.replace("st.session_state.captured_photos", "st.session_state.ps_captured_photos")
strip_ui = strip_ui.replace("st.session_state.final_strip", "st.session_state.ps_final_strip")
strip_ui = strip_ui.replace("st.session_state.image_bytes", "st.session_state.ps_image_bytes")
strip_ui = strip_ui.replace("st.session_state.file_name", "st.session_state.ps_file_name")
strip_ui = strip_ui.replace("st.session_state.photo_url", "st.session_state.ps_photo_url")
strip_ui = strip_ui.replace("st.session_state.is_capturing", "st.session_state.ps_is_capturing")
strip_ui = strip_ui.replace("st.session_state.selected_strip", "st.session_state.ps_selected_strip")
strip_ui = strip_ui.replace("st.session_state.selected_filter", "st.session_state.ps_selected_filter")
strip_ui = strip_ui.replace("st.session_state.upload_error", "st.session_state.ps_upload_error")
strip_ui = strip_ui.replace("_reset_session()", "_reset_ps_session()")

# Ensure QR Result Page uses the main theme style for the qr code section
# We'll replace the block that renders the QR code with a stylized version
old_qr = 'st.image(qr_buf.getvalue(), width=280)'
new_qr = '''
            qr_b64 = base64.b64encode(qr_buf.getvalue()).decode("utf-8")
            st.markdown(
                f"<div style='display: flex; align-items: center; justify-content: center; height: 300px; box-sizing: border-box;'>"
                f"<img src='data:image/png;base64,{qr_b64}' style='width: 280px; height: 280px; border-radius: 12px; border: 2px solid rgba(255,45,117,0.3); box-shadow: 0 0 20px rgba(255,45,117,0.15);' />"
                f"</div>",
                unsafe_allow_html=True
            )
'''
strip_ui = strip_ui.replace(old_qr, new_qr)

strip_ui = "\n".join("    " + line for line in strip_ui.splitlines())

photostrip_page = f"""
def render_photostrip_page():
    # Back button
    st.markdown('<div class="reset-btn" style="margin-bottom: 20px;">', unsafe_allow_html=True)
    if st.button("⬅️ Back to Home", key="ps_back"):
        st.session_state.app_page = "home"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

{strip_ui}
"""

# 10. Main Execution
main_exec = """
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
"""

with open('app_new.py', 'w', encoding='utf-8') as f:
    f.write(imports)
    f.write(page_config)
    f.write(css_and_html)
    f.write(app_backend_logic)
    f.write(strip_backend)
    f.write(combined_init_state)
    f.write(home_page)
    f.write(photobooth_page)
    f.write(photostrip_page)
    f.write(main_exec)

print("Created app_new.py!")
