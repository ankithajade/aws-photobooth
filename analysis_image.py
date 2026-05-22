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


def draw_cyber_corners(draw, w, h, color_pink, color_purple):
    """Draws sleek circuit-like corner decorations matching the UI theme."""
    # Top-Left corner circuit lines
    draw.line([(0, 40), (30, 40), (40, 30), (40, 0)], fill=color_pink, width=2)
    draw.line([(0, 60), (15, 60), (25, 50), (25, 25), (35, 15), (60, 15)], fill=color_purple, width=1)
    # End node circles
    draw.ellipse((38, 0, 42, 4), fill=color_pink)
    draw.ellipse((58, 13, 62, 17), fill=color_purple)
    draw.ellipse((0, 38, 4, 42), fill=color_pink)

    # Bottom-Right corner circuit lines (mirrored)
    draw.line([(w - 40, h), (w - 40, h - 30), (w - 30, h - 40), (w, h - 40)], fill=color_pink, width=2)
    draw.line([(w - 60, h - 15), (w - 35, h - 15), (w - 25, h - 25), (w - 25, h - 50), (w - 15, h - 60), (w, h - 60)], fill=color_purple, width=1)
    # End node circles
    draw.ellipse((w - 42, h - 4, w - 38, h), fill=color_pink)
    draw.ellipse((w - 62, h - 17, w - 58, h - 13), fill=color_purple)
    draw.ellipse((w - 4, h - 42, w, h - 38), fill=color_pink)


def generate_analysis_image(analysis_results, group_vibe=""):
    """
    Generate an 800 x 1000 beautiful graphic of the AI analysis.
    Theme: sleek dark-cyber mode.
    Uses Pilmoji for all text so emojis render correctly.
    """
    # 1. Initialize image & canvas
    bg_color    = (8, 8, 13)         # Dark background #08080d
    card_color  = (18, 18, 28)       # Inner cards #12121c
    bar_bg      = (30, 30, 45)       # Progress bar background

    # UI Accents
    accent_pink   = (255, 45, 117)   # Pink  #ff2d75
    accent_purple = (108, 59, 255)   # Purple #6c3bff
    cyan_text     = (0, 212, 255)    # Cyan  #00d4ff
    white_text    = (245, 245, 247)  # Primary text
    gray_text     = (140, 140, 160)  # Subtext

    w, h = 800, 1000
    img  = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(img)

    # 2. Draw Decorative Tech Elements (shapes only – no emoji involved)
    draw_cyber_corners(draw, w, h, accent_pink, accent_purple)

    # ---------------------------------------------------------------
    # All text rendering below uses Pilmoji so emojis display properly
    # ---------------------------------------------------------------
    with Pilmoji(img) as pj:

        # 3. Header Section (y = 0 to 140)
        font_brand = get_font(12, "bold")
        font_title = get_font(28, "bold")

        brand_t1 = "AWS STUDENT BUILDER GROUP, DBIT"
        brand_t2 = "VIGNANOTSAVA 2K26"
        title_t  = "🤖  AI  ANALYSIS"

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
                              accent_pink, (40, 20, 30), radius=10, border_width=1)
            pj.text((int(card_x0 + 52), int(card_y0 + 80)),
                    age_str, fill=white_text, font=font_pill)

            # Emotion pill
            epw, eph = get_text_size(emo_str, font_pill)
            draw_rounded_card(draw,
                              card_x0 + 40 + apw + 40, card_y0 + 75,
                              card_x0 + 40 + apw + 40 + epw + 24, card_y0 + 75 + eph + 10,
                              accent_purple, (30, 20, 45), radius=10, border_width=1)
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
                              accent_pink, (24, 18, 25), radius=12, border_width=2)

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
                                  accent_purple, (25, 25, 40), radius=10, border_width=1)
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
                              accent_purple, (16, 16, 32), radius=12, border_width=2)

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
                                  accent_pink, (40, 20, 30), radius=8, border_width=1)
                pj.text((int(cx0 + 32), int(cy0 + 58)),
                        age_s, fill=white_text, font=font_pill)

                epw, eph = get_text_size(emo_s, font_pill)
                draw_rounded_card(draw,
                                  cx0 + 25 + apw + 20, cy0 + 55,
                                  cx0 + 25 + apw + 20 + epw + 14, cy0 + 55 + eph + 6,
                                  accent_purple, (30, 20, 45), radius=8, border_width=1)
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
                                  accent_pink, (24, 18, 25), radius=10, border_width=1)

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
                                      accent_purple, (25, 25, 40), radius=8, border_width=1)
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
