# utils/embed_image.py
import os, io, time
from PIL import Image, ImageDraw, ImageFont

AVATAR_SIZE = (207, 207)
AVATAR_POSITION = (62, 137)

CHECKMARK_PATH = "real_bot/real_bot/checkmark.png"
TEMPLATE_PATH  = "real_bot/real_bot/emblem.png"
DEFAULT_AVATAR = "real_bot/real_bot/default_avatar.png"
FONT_BOLD      = "real_bot/real_bot/utils/fonts/arialbd.ttf"
FONT_REGULAR   = "real_bot/real_bot/utils/fonts/arial.ttf"

def wrap_text(text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test_line = f"{current} {word}".strip()
        if font.getlength(test_line) <= max_width:
            current = test_line
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

async def create_embed_image(user, avatar_bytes, title, elapsed, timestamp, mode):
    try:
        template = Image.open(TEMPLATE_PATH).convert("RGBA")
    except Exception as e:
        print("[ERROR - embed] Template load error:", e)
        return None

    try:
        title_font  = ImageFont.truetype(FONT_BOLD, 28)
        sub_font    = ImageFont.truetype(FONT_REGULAR, 20)
        footer_font = ImageFont.truetype(FONT_BOLD, 28)
    except Exception as e:
        print("[ERROR - embed] Font load error:", e)
        return None

    draw = ImageDraw.Draw(template)

    # avatar
    try:
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize(AVATAR_SIZE)
    except Exception:
        try:
            avatar = Image.open(DEFAULT_AVATAR).convert("RGBA").resize(AVATAR_SIZE)
        except Exception as e:
            print("[ERROR - embed] Default avatar load failed:", e)
            avatar = Image.new("RGBA", AVATAR_SIZE, (0, 0, 0, 0))
            m = Image.new("L", AVATAR_SIZE, 0)
            ImageDraw.Draw(m).ellipse((0,0,*AVATAR_SIZE), fill=255)
            avatar.putalpha(m)

    mask = Image.new("L", AVATAR_SIZE, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, *AVATAR_SIZE), fill=255)
    template.paste(avatar, AVATAR_POSITION, mask)

    # title
    y = 180
    for line in wrap_text(title, title_font, 470):
        draw.text((380, y), line, font=title_font, fill="white")
        y += title_font.size + 8

    # check
    try:
        checkmark = Image.open(CHECKMARK_PATH).convert("RGBA").resize((42, 42))
        template.paste(checkmark, (330, 180), checkmark)
    except Exception as e:
        print("[ERROR - embed] Checkmark icon failed:", e)

    # elapsed
    if elapsed:
        draw.text((320, y + 10), f"Downloaded in {elapsed:.2f}s", font=sub_font, fill="white")

    # footer (no timestamp)
    draw.text((100, 400), f"Requested by {user}", font=footer_font, fill="white")

    # return as bytes
    buf = io.BytesIO()
    template.save(buf, format="PNG")
    buf.seek(0)
    return buf
