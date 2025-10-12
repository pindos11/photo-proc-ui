from flask import Flask, render_template, request, send_from_directory
import os, cv2
import numpy as np
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')


def apply_enhancements(img, options, brightness_val=25, contrast_val=25, sharpen_val=25):
    # Always 8-bit, 3-channel
    img = cv2.convertScaleAbs(img).astype(np.float32) / 255.0

    b_factor = 1.0 + (brightness_val - 50) / 200.0   # ±25 %
    c_factor = 1.0 + (contrast_val - 50) / 200.0
    s_strength = sharpen_val / 100.0

    # --- LIGHT DENOISE (skip full NLM) ---
    if "denoise" in options:
        # gentle bilateral filter keeps edges & gradients
        img = cv2.bilateralFilter(img, d=0, sigmaColor=0.02, sigmaSpace=5)

    if "brightness" in options or "contrast" in options:
        # Work in float space for smooth tone mapping
        # Brightness shifts (additive), contrast stretches (around 0.5 mid gray)
        brightness_shift = (b_factor - 1.0) * 0.25  # roughly ±0.25 range
        img = np.clip((img - 0.5) * c_factor + 0.5 + brightness_shift, 0, 1)

    # --- SHARPEN (very mild unsharp mask) ---
    if "sharpen" in options and s_strength > 0:
        blur = cv2.GaussianBlur(img, (0, 0), 2)
        img = cv2.addWeighted(img, 1.0 + 0.5 * s_strength, blur, -0.5 * s_strength, 0)

    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def add_logo(base_path, logo_path, position, opacity=0.8, scale=0.25):
    base = Image.open(base_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    # Resize logo by relative scale
    bw, bh = base.size
    lw = int(bw * scale)
    lh = int(logo.height * (bw * scale / logo.width))
    logo = logo.resize((lw, lh), Image.LANCZOS)

    # Apply overall opacity only once
    if opacity < 1.0:
        alpha = logo.split()[3]
        alpha = alpha.point(lambda p: int(p * opacity))
        logo.putalpha(alpha)

    # Determine position
    if position == "bottom-right":
        pos = (bw - lw - 20, bh - lh - 20)
    elif position == "bottom-left":
        pos = (20, bh - lh - 20)
    elif position == "top-left":
        pos = (20, 20)
    elif position == "center":
        pos = ((bw - lw) // 2, (bh - lh) // 2)
    else:  # top-right
        pos = (bw - lw - 20, 20)

    base.alpha_composite(logo, dest=pos)

    # Save as PNG with minimal compression (preserve gradients)
    base.save(base_path, "PNG", compress_level=0)


@app.route('/process', methods=['POST'])
def process_images():
    brightness_val = int(request.form.get('brightness_val', 25))
    contrast_val = int(request.form.get('contrast_val', 25))
    sharpen_val = int(request.form.get('sharpen_val', 25))

    # Get files and parameters
    files = request.files.getlist('images')
    logo = request.files.get('logo')
    options = request.form.getlist('options')
    position = request.form.get('position')
    opacity = float(request.form.get('opacity', 0.8))
    scale = float(request.form.get('scale', 0.25))

    print(f"DEBUG: got {len(files)} image(s)")
    print(f"DEBUG: logo present: {bool(logo)}")

    # Save logo if provided
    logo_path = None
    if logo and logo.filename:
        logo_path = os.path.join(UPLOAD_FOLDER, logo.filename)
        logo.save(logo_path)

    processed_files = []

    for file in files:
        if not file or not file.filename:
            continue

        img_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(img_path)

        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            try:
                # Convert HEIC → PNG
                im = Image.open(img_path).convert("RGB")
                heic_temp = os.path.join(
                    UPLOAD_FOLDER, os.path.splitext(file.filename)[0] + ".png"
                )
                im.save(heic_temp, "PNG", compress_level=1)
                img = cv2.imread(heic_temp, cv2.IMREAD_UNCHANGED)
                print(f"Converted {file.filename} → {os.path.basename(heic_temp)}")
            except Exception as e:
                print(f"❌ Could not convert {file.filename}: {e}")
                continue

        if img is None:
            print(f"⚠️ Could not read {file.filename}")
            continue

        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        img = cv2.convertScaleAbs(img)

        img = apply_enhancements(img, options, brightness_val, contrast_val, sharpen_val)

        base_name = os.path.splitext(file.filename)[0]
        out_filename = base_name + ".png"
        out_path = os.path.join(PROCESSED_FOLDER, out_filename)
        cv2.imwrite(out_path, img, [int(cv2.IMWRITE_PNG_COMPRESSION), 0])  # near-lossless PNG

        if logo_path:
            add_logo(out_path, logo_path, position, opacity, scale)

        processed_files.append(out_filename)

    print("DEBUG: processed files:", processed_files)

    return {'processed': processed_files}


@app.route('/processed/<filename>')
def download_file(filename):
    return send_from_directory(PROCESSED_FOLDER, filename)


if __name__ == '__main__':
    app.run(debug=True)
