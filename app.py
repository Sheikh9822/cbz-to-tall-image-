from flask import Flask, request, send_file, render_template_string
import os, zipfile, shutil
from PIL import Image
from datetime import datetime
from math import ceil

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("cbz")
        if not file or not file.filename.endswith(".cbz"):
            return "<h3>❌ Please upload a valid .cbz file.</h3>"

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        session_dir = os.path.join(UPLOAD_FOLDER, f"session_{timestamp}")
        os.makedirs(session_dir, exist_ok=True)

        cbz_path = os.path.join(session_dir, "input.cbz")
        file.save(cbz_path)

        extract_dir = os.path.join(session_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(cbz_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        image_files = sorted([
            f for f in os.listdir(extract_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
        ])
        if not image_files:
            return "<h3>❌ No valid image files found in CBZ.</h3>"

        images = [Image.open(os.path.join(extract_dir, f)).convert("RGB") for f in image_files]
        margin = 20
        images_per_group = 10
        total_groups = ceil(len(images) / images_per_group)

        tall_outputs = []
        for i in range(total_groups):
            group = images[i * images_per_group:(i + 1) * images_per_group]
            max_width = max(img.width for img in group)
            total_height = sum(img.height for img in group) + margin * (len(group) - 1)

            tall_image = Image.new("RGB", (max_width, total_height), (255, 255, 255))
            y_offset = 0
            for img in group:
                tall_image.paste(img, (0, y_offset))
                y_offset += img.height + margin

            out_name = f"tall_{i+1:03}.jpg"
            out_path = os.path.join(session_dir, out_name)
            tall_image.save(out_path, quality=100, subsampling=0)
            tall_outputs.append((out_name, out_path))

        # Save ZIP and CBZ
        zip_basename = f"output_{timestamp}"
        zip_path = os.path.join(OUTPUT_FOLDER, f"{zip_basename}.zip")
        cbz_path = os.path.join(OUTPUT_FOLDER, f"{zip_basename}.cbz")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for name, path in tall_outputs:
                zipf.write(path, arcname=name)

        shutil.copy(zip_path, cbz_path)

        # Show download links
        return render_template_string(f"""
        <h2>✅ Done! Your files are ready:</h2>
        <p><a href="/download/{zip_basename}.zip">📦 Download ZIP</a></p>
        <p><a href="/download/{zip_basename}.cbz">📘 Download CBZ</a></p>
        """)

    return open("index.html", "r", encoding="utf-8").read()

@app.route("/download/<filename>")
def download_file(filename):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "❌ File not found", 404