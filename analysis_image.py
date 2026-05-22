import os
from PIL import Image, ImageDraw, ImageFont
from pilmoji import Pilmoji

def get_font(size=14, style="regular"):
    """
    Get a system font safely with fallbacks.
    Styles: 'regular', 'bold', 'italic'
    """
    font_files = {
        "regular": ["arial.ttf", "segoeui.ttf", "tahoma.ttf"],
        "bold":    ["arialbd.ttf", "segoeuib.ttf", "tahomabd.ttf"],
        "italic":  ["ariali.ttf", "segoeuii.ttf", "tahomai.ttf"]
    }

    # Try preferred files
    for name in font_files.get(style, font_files["regular"]):
        try:
            return ImageFont.truetype(name, size)
        except IOError:
            continue

    # Try direct paths on Windows
    windir = os.environ.get("WINDIR", "C:\\Windows")
    for name in font_files.get(style, font_files["regular"]):
        path = os.path.join(windir, "Fonts", name)
        try:
            return ImageFont.truetype(path, size)
        except IOError:
            continue

    # Fallback to default
    return ImageFont.load_default()


def get_text_size(text, font):
    """Safe text dimensions helper that works across Pillow versions."""
    if hasattr(font, 'getbbox'):
        bbox = font.getbbox(text)
        w = int(bbox[2] - bbox[0])
        h = int(bbox[3] - bbox[1])
        return w, h
    else:
        w, h = font.getsize(text)
        return int(w), int(h)


def wrap_text(text, font, max_width):
    """Splits text into lines that fit within a maximum width."""
    if not text:
        return []
    words = text.split(' ')
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        line_str = ' '.join(current_line)
        w, _ = get_text_size(line_str, font)
        if w > max_width:
            if len(current_line) == 1:
                lines.append(line_str)
                current_line = []
            else:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    return lines


def draw_rounded_card(draw, x0, y0, x1, y1, border_color, fill_color, radius=16, border_width=2):
    """Draws a beautiful rounded card with custom borders."""
    x0, y0, x1, y1, radius = int(x0), int(y0), int(x1), int(y1), int(radius)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill_color)
    if border_color:
        draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=border_color, width=int(border_width))


def draw_progress_bar(draw, x, y, w, h, percentage, bar_color, bg_color):
    """Draws a sleek, capsule-style gaming progress bar."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=bg_color)
    if percentage > 0:
        fill_w = max(h, int(w * (min(percentage, 100) / 100.0)))
        draw.rounded_rectangle([x, y, x + fill_w, y + h], radius=h // 2, fill=bar_color)


def draw_elegant_corners(draw, w, h, color_pink, color_purple):
    """Draws sleek minimalist corner accents matching the light UI theme."""
    # Top-Left corner
    draw.arc([(20, 20), (60, 60)], start=180, end=270, fill=color_pink, width=3)
    draw.line([(40, 20), (80, 20)], fill=color_pink, width=3)
    draw.line([(20, 40), (20, 80)], fill=color_pink, width=3)

    # Bottom-Right corner
    draw.arc([(w - 60, h - 60), (w - 20, h - 20)], start=0, end=90, fill=color_purple, width=3)
    draw.line([(w - 80, h - 20), (w - 40, h - 20)], fill=color_purple, width=3)
    draw.line([(w - 20, h - 80), (w - 20, h - 40)], fill=color_purple, width=3)


def draw_background_grid(img, w, h, step=30):
    """
    Draw a very faint coordinate dot-grid across the entire canvas.
    Uses a separate RGBA overlay to keep the opacity controllable without
    touching the base background colour.
    """
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    dot_color = (100, 100, 160, 18)   # very transparent indigo dots
    r = 1  # dot radius in pixels
    for x in range(0, w, step):
        for y in range(0, h, step):
            od.ellipse((x - r, y - r, x + r, y + r), fill=dot_color)
    # alpha-composite the grid onto the base image
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"), (0, 0))


def draw_ambient_glow_blob(img, cx, cy, radius, color_rgba):
    """
    Draw a large, soft radial-glow blob using a Gaussian-blurred filled ellipse.
    *color_rgba* should be an (R,G,B,A) tuple where A controls max opacity.
    """
    blob_size = radius * 2
    blob = Image.new("RGBA", (blob_size, blob_size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blob)
    # Draw concentric ellipses that fade outwards
    steps = 10
    r, g, b, a = color_rgba
    for i in range(steps, 0, -1):
        frac = i / steps
        ellipse_r = int(radius * frac)
        alpha = int(a * frac * 0.6)
        bd.ellipse(
            (radius - ellipse_r, radius - ellipse_r,
             radius + ellipse_r, radius + ellipse_r),
            fill=(r, g, b, alpha)
        )
    # Paste with alpha blending
    paste_x = cx - radius
    paste_y = cy - radius
    # Clamp to canvas
    ox = max(0, -paste_x)
    oy = max(0, -paste_y)
    px = max(0, paste_x)
    py = max(0, paste_y)
    cropped = blob.crop((ox, oy, blob_size - max(0, (paste_x + blob_size) - img.width),
                                blob_size - max(0, (paste_y + blob_size) - img.height)))
    base = img.convert("RGBA")
    base.paste(cropped, (px, py), cropped)
    img.paste(base.convert("RGB"), (0, 0))


def draw_sparkle_accent(draw, cx, cy, size, color, alpha_img=None):
    """
    Draw a classic four-pointed star (✦) at (cx, cy) using four diamond lines.
    Works directly on a Pillow Draw object.
    """
    cx, cy, s = int(cx), int(cy), int(size)
    half = s // 2
    quarter = s // 4
    # Long arms (top-bottom, left-right)
    draw.line([(cx, cy - half), (cx, cy + half)], fill=color, width=max(1, s // 10))
    draw.line([(cx - half, cy), (cx + half, cy)], fill=color, width=max(1, s // 10))
    # Short diagonal arms
    d = quarter
    draw.line([(cx - d, cy - d), (cx + d, cy + d)], fill=color, width=max(1, s // 14))
    draw.line([(cx + d, cy - d), (cx - d, cy + d)], fill=color, width=max(1, s // 14))


def draw_card_shadow(img, x0, y0, x1, y1, radius=16, shadow_color=(150, 130, 200, 50)):
    """
    Draw a soft drop-shadow beneath a card by compositing a blurred
    filled rectangle on a transparent layer.
    """
    pad = 12  # shadow spread
    shadow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_layer)
    sd.rounded_rectangle(
        (int(x0) - pad // 2, int(y0) + 6,
         int(x1) + pad // 2, int(y1) + 14),
        radius=int(radius) + 4,
        fill=shadow_color
    )
    # Simple box-blur approximation (3 passes for softness)
    from PIL import ImageFilter
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=8))
    base = img.convert("RGBA")
    base = Image.alpha_composite(base, shadow_layer)
    img.paste(base.convert("RGB"), (0, 0))


def generate_analysis_image(analysis_results, group_vibe=""):
    """
    Generate an 800 x 1000 beautiful graphic of the AI analysis.
    Theme: sleek dark-cyber mode.
    Uses Pilmoji for all text so emojis render correctly.
    """
    # 1. Initialize image & canvas
    bg_color    = (246, 243, 250)    # Light background #f6f3fa
    card_color  = (255, 255, 255)    # Inner cards
    bar_bg      = (230, 230, 240)    # Progress bar background

    # UI Accents
    accent_pink   = (255, 90, 223)   # Soft Pink #ff5adf
    accent_purple = (126, 162, 255)  # Light Blue/Purple #7ea2ff
    cyan_text     = (211, 108, 255)  # Bright Purple
    white_text    = (26, 26, 46)     # Dark text #1a1a2e (Replaces white_text for light mode)
    gray_text     = (74, 74, 104)    # Gray text #4a4a68

    w, h = 800, 1000
    img  = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(img)

    # 2a. Poster-style ambient glow blobs (drawn before everything else)
    draw_ambient_glow_blob(img, cx=650, cy=200, radius=220, color_rgba=(255, 90, 223, 55))
    draw_ambient_glow_blob(img, cx=150, cy=800, radius=200, color_rgba=(126, 162, 255, 50))

    # Refresh draw handle after pixel-level operations
    draw = ImageDraw.Draw(img)

    # 2b. Subtle dot-grid overlay
    draw_background_grid(img, w, h, step=30)
    draw = ImageDraw.Draw(img)

    # 2c. Draw Decorative Tech Elements (corner arcs)
    draw_elegant_corners(draw, w, h, accent_pink, accent_purple)

    # 2d. Sparkle / star accents (drawn after grid, before text)
    sparkle_pink   = (255, 90, 223, 200)
    sparkle_purple = (126, 162, 255, 200)
    # Corner sparkles
    draw_sparkle_accent(draw, 110, 200, 18, accent_purple)
    draw_sparkle_accent(draw, 690, 200, 14, accent_pink)
    draw_sparkle_accent(draw, 130, 870, 12, accent_pink)
    draw_sparkle_accent(draw, 670, 870, 16, accent_purple)
    # Mid-edge sparkles
    draw_sparkle_accent(draw, 50,  500, 10, (200, 180, 255))
    draw_sparkle_accent(draw, 750, 500, 10, (255, 180, 240))

    # ---------------------------------------------------------------
    # All text rendering below uses Pilmoji so emojis display properly
    # ---------------------------------------------------------------
    with Pilmoji(img) as pj:

        # 3. Header Section (y = 0 to 140)
        font_brand = get_font(12, "bold")
        font_title = get_font(28, "bold")

        brand_t1 = "AWS STUDENT BUILDER GROUP, DBIT"
        brand_t2 = "VIGNANOTSAVA 2K26"
        title_t  = "✨ AI  SNAPSHOT"

        # Centering headers
        bw1, _ = get_text_size(brand_t1, font_brand)
        pj.text((int((w - bw1) // 2), 30), brand_t1, fill=gray_text, font=font_brand)

        bw2, _ = get_text_size(brand_t2, font_brand)
        pj.text((int((w - bw2) // 2), 50), brand_t2, fill=accent_pink, font=font_brand)

        tw, _ = get_text_size(title_t, font_title)
        pj.text((int((w - tw) // 2), 80), title_t, fill=white_text, font=font_title)

        # Gradient line separator (shape – use draw directly)
        draw.line([(100, 130), (700, 130)], fill=accent_purple, width=2)

        # 4. Content Logic
        num_faces = len(analysis_results)

        # ── Case 0: No face ──────────────────────────────────────────
        if num_faces == 0:
            font_msg = get_font(18, "regular")
            draw_card_shadow(img, 100, 380, 700, 620)
            draw = ImageDraw.Draw(img)
            draw_rounded_card(draw, 100, 380, 700, 620, accent_pink, card_color)

            msg_t = "No face detected, but the moment is still captured."
            mw, mh = get_text_size(msg_t, font_msg)
            pj.text((int((w - mw) // 2), int(500 - mh // 2)), msg_t,
                    fill=white_text, font=font_msg)

        # ── Case 1: Single person ─────────────────────────────────────
        elif num_faces == 1:
            info = analysis_results[0]

            card_x0, card_x1 = 150, 650
            card_y0, card_y1 = 180, 920
            draw_card_shadow(img, card_x0, card_y0, card_x1, card_y1)
            draw = ImageDraw.Draw(img)
            draw_rounded_card(draw, card_x0, card_y0, card_x1, card_y1, accent_purple, card_color)

            # Detected Face Label
            font_lbl = get_font(18, "bold")
            pj.text((int(card_x0 + 40), int(card_y0 + 35)),
                    "😄  Detected Face Summary", fill=accent_pink, font=font_lbl)

            # Age & Emotion Capsules
            font_pill = get_font(13, "bold")
            age_str = f"Age: {info['age_range']}"
            emo_str = f"Emotion: {info['emotion'].capitalize()}"

            # Age pill
            apw, aph = get_text_size(age_str, font_pill)
            draw_rounded_card(draw,
                              card_x0 + 40, card_y0 + 75,
                              card_x0 + 40 + apw + 24, card_y0 + 75 + aph + 10,
                              accent_pink, (255, 240, 250), radius=10, border_width=1)
            pj.text((int(card_x0 + 52), int(card_y0 + 80)),
                    age_str, fill=white_text, font=font_pill)

            # Emotion pill
            epw, eph = get_text_size(emo_str, font_pill)
            draw_rounded_card(draw,
                              card_x0 + 40 + apw + 40, card_y0 + 75,
                              card_x0 + 40 + apw + 40 + epw + 24, card_y0 + 75 + eph + 10,
                              accent_purple, (245, 240, 255), radius=10, border_width=1)
            pj.text((int(card_x0 + 40 + apw + 52), int(card_y0 + 80)),
                    emo_str, fill=white_text, font=font_pill)

            # Caption / Quote Box
            font_quote = get_font(14, "italic")
            lines = wrap_text(f"\"{info['caption']}\"", font_quote, 420)
            curr_y = int(card_y0 + 130)
            for line in lines:
                lw, _ = get_text_size(line, font_quote)
                pj.text((int(card_x0 + (500 - lw) // 2), int(curr_y)),
                        line, fill=gray_text, font=font_quote)
                curr_y += 20

            # AI Persona Banner
            font_pers_lbl = get_font(11, "bold")
            font_pers_val = get_font(20, "bold")

            banner_y = int(card_y0 + 185)
            draw_rounded_card(draw,
                              card_x0 + 30, banner_y, card_x1 - 30, banner_y + 70,
                              accent_pink, (255, 245, 255), radius=12, border_width=2)

            plw, _ = get_text_size("AI PERSONA", font_pers_lbl)
            pj.text((int(card_x0 + (500 - plw) // 2), int(banner_y + 10)),
                    "AI PERSONA", fill=accent_pink, font=font_pers_lbl)

            pvw, _ = get_text_size(info['personality'], font_pers_val)
            pj.text((int(card_x0 + (500 - pvw) // 2), int(banner_y + 30)),
                    info['personality'], fill=cyan_text, font=font_pers_val)

            # Badges
            font_badge   = get_font(11, "bold")
            badge_y      = banner_y + 88
            curr_badge_x = card_x0 + 40
            for badge in info['badges']:
                bw, bh = get_text_size(badge, font_badge)
                if curr_badge_x + bw + 20 > card_x1 - 20:
                    break
                draw_rounded_card(draw,
                                  curr_badge_x, badge_y,
                                  curr_badge_x + bw + 16, badge_y + bh + 8,
                                  accent_purple, (245, 245, 255), radius=10, border_width=1)
                pj.text((int(curr_badge_x + 8), int(badge_y + 4)),
                        badge, fill=white_text, font=font_badge)
                curr_badge_x += bw + 26

            # Vibe Stats header
            font_stat_hdr = get_font(11, "bold")
            shw, _ = get_text_size("VIBE STATISTICS", font_stat_hdr)
            stat_y = int(badge_y + 45)
            pj.text((int(card_x0 + (500 - shw) // 2), stat_y),
                    "VIBE STATISTICS", fill=gray_text, font=font_stat_hdr)

            # Vibe stats progress bars
            font_stat_lbl = get_font(12, "bold")
            font_stat_val = get_font(12, "bold")

            bar_y = int(stat_y + 25)
            for label, val in info['vibes'].items():
                pj.text((int(card_x0 + 40), int(bar_y)),
                        label, fill=gray_text, font=font_stat_lbl)

                val_str = str(val)
                pj.text((int(card_x1 - 40 - get_text_size(val_str, font_stat_val)[0]), int(bar_y)),
                        val_str, fill=cyan_text, font=font_stat_val)

                if "MAX" in val_str:
                    pct = 100
                elif "CRITICAL" in val_str:
                    pct = 15
                else:
                    try:
                        pct = int(val_str.replace("%", ""))
                    except ValueError:
                        pct = 50

                draw_progress_bar(draw, card_x0 + 170, bar_y + 4, 180, 8,
                                  pct, accent_pink, bar_bg)
                bar_y += 28

        # ── Case 2: Multi-person ──────────────────────────────────────
        else:
            # Group Vibe Banner
            banner_y0, banner_y1 = 155, 215
            draw_rounded_card(draw, 40, banner_y0, 760, banner_y1,
                              accent_purple, (255, 255, 255), radius=12, border_width=2)

            font_vibe_lbl = get_font(10, "bold")
            font_vibe_val = get_font(16, "bold")

            v_lbl = "TEAM CHEMISTRY / VIBE"
            v_val = f"✨  {group_vibe}"

            v_lbl_w, _ = get_text_size(v_lbl, font_vibe_lbl)
            pj.text((int((w - v_lbl_w) // 2), int(banner_y0 + 8)),
                    v_lbl, fill=accent_pink, font=font_vibe_lbl)

            v_val_w, _ = get_text_size(v_val, font_vibe_val)
            pj.text((int((w - v_val_w) // 2), int(banner_y0 + 26)),
                    v_val, fill=white_text, font=font_vibe_val)

            # Two-column layout
            cols_cfg = [
                {"x0": 40,  "x1": 380, "info": analysis_results[0], "title": "👤  Person 1"},
                {"x0": 420, "x1": 760, "info": analysis_results[1], "title": "👤  Person 2"},
            ]

            font_lbl      = get_font(15, "bold")
            font_pill     = get_font(11, "bold")
            font_quote    = get_font(12, "italic")
            font_pers_lbl = get_font(10, "bold")
            font_pers_val = get_font(16, "bold")
            font_badge    = get_font(10, "bold")
            font_stat_lbl = get_font(11, "bold")
            font_stat_val = get_font(11, "bold")

            for col in cols_cfg:
                cx0, cx1 = col["x0"], col["x1"]
                cy0, cy1 = 240, 940
                c_info   = col["info"]

                draw_card_shadow(img, cx0, cy0, cx1, cy1)
                draw = ImageDraw.Draw(img)
                draw_rounded_card(draw, cx0, cy0, cx1, cy1, accent_purple, card_color)

                # Person title
                pj.text((int(cx0 + 25), int(cy0 + 25)),
                        col["title"], fill=accent_pink, font=font_lbl)

                # Age & Emotion pills
                age_s = f"{c_info['age_range']}"
                emo_s = f"{c_info['emotion'].capitalize()}"

                apw, aph = get_text_size(age_s, font_pill)
                draw_rounded_card(draw,
                                  cx0 + 25, cy0 + 55,
                                  cx0 + 25 + apw + 14, cy0 + 55 + aph + 6,
                                  accent_pink, (255, 240, 250), radius=8, border_width=1)
                pj.text((int(cx0 + 32), int(cy0 + 58)),
                        age_s, fill=white_text, font=font_pill)

                epw, eph = get_text_size(emo_s, font_pill)
                draw_rounded_card(draw,
                                  cx0 + 25 + apw + 20, cy0 + 55,
                                  cx0 + 25 + apw + 20 + epw + 14, cy0 + 55 + eph + 6,
                                  accent_purple, (245, 240, 255), radius=8, border_width=1)
                pj.text((int(cx0 + 25 + apw + 27), int(cy0 + 58)),
                        emo_s, fill=white_text, font=font_pill)

                # Caption Quote
                q_lines = wrap_text(f"\"{c_info['caption']}\"", font_quote, 290)
                curr_y  = int(cy0 + 100)
                for line in q_lines:
                    lw, _ = get_text_size(line, font_quote)
                    pj.text((int(cx0 + (340 - lw) // 2), int(curr_y)),
                            line, fill=gray_text, font=font_quote)
                    curr_y += 18

                # AI Persona Card
                pers_y = int(cy0 + 155)
                draw_rounded_card(draw,
                                  cx0 + 20, pers_y, cx1 - 20, pers_y + 60,
                                  accent_pink, (255, 245, 255), radius=10, border_width=1)

                plw, _ = get_text_size("AI PERSONA", font_pers_lbl)
                pj.text((int(cx0 + (340 - plw) // 2), int(pers_y + 8)),
                        "AI PERSONA", fill=accent_pink, font=font_pers_lbl)

                pvw, _ = get_text_size(c_info['personality'], font_pers_val)
                pj.text((int(cx0 + (340 - pvw) // 2), int(pers_y + 26)),
                        c_info['personality'], fill=cyan_text, font=font_pers_val)

                # Badges
                badge_y      = int(pers_y + 75)
                curr_badge_x = int(cx0 + 25)
                for badge in c_info['badges']:
                    bw, bh = get_text_size(badge, font_badge)
                    if curr_badge_x + bw + 14 > cx1 - 15:
                        break
                    draw_rounded_card(draw,
                                      curr_badge_x, badge_y,
                                      curr_badge_x + bw + 12, badge_y + bh + 6,
                                      accent_purple, (245, 245, 255), radius=8, border_width=1)
                    pj.text((int(curr_badge_x + 6), int(badge_y + 3)),
                            badge, fill=white_text, font=font_badge)
                    curr_badge_x += bw + 18

                # Vibe Stats header
                v_hdr_y = int(badge_y + 40)
                pj.text((int(cx0 + 25), int(v_hdr_y)),
                        "VIBE STATISTICS", fill=gray_text, font=font_pers_lbl)

                # Vibe stats progress bars
                bar_y = int(v_hdr_y + 20)
                for label, val in c_info['vibes'].items():
                    pj.text((int(cx0 + 25), int(bar_y)),
                            label, fill=gray_text, font=font_stat_lbl)

                    val_str = str(val)
                    vw, _   = get_text_size(val_str, font_stat_val)
                    pj.text((int(cx1 - 25 - vw), int(bar_y)),
                            val_str, fill=cyan_text, font=font_stat_val)

                    if "MAX" in val_str:
                        pct = 100
                    elif "CRITICAL" in val_str:
                        pct = 15
                    else:
                        try:
                            pct = int(val_str.replace("%", ""))
                        except ValueError:
                            pct = 50

                    draw_progress_bar(draw, cx0 + 145, bar_y + 4, 115, 6,
                                      pct, accent_pink, bar_bg)
                    bar_y += 24

        # 5. Footer
        font_foot = get_font(10, "regular")
        foot_text = "POWERED BY AWS REKOGNITION · AI PERSONALITY ENGINE"
        fw_w, _   = get_text_size(foot_text, font_foot)
        pj.text((int((w - fw_w) // 2), 960), foot_text,
                fill=gray_text, font=font_foot)

    return img
