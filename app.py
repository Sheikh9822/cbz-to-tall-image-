import zipfile
import os
from PIL import Image
from math import ceil

# === CONFIGURATION ===
zip_path = "test.zip"          # Path to input zip
temp_dir = "temp_images"
output_dir = "output_pages"
final_zip = "output_pages.zip"
page_quality = 100                    # Max image quality
margin = 20                           # Margin in pixels between images

# === UNZIP IMAGES ===
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(temp_dir)

# === LOAD IMAGES ===
image_files = sorted([
    f for f in os.listdir(temp_dir)
    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
])

os.makedirs(output_dir, exist_ok=True)

# === PAGE GENERATOR ===
def create_custom_page(img_paths, page_num):
    # Load images or use blank filler
    images = [Image.open(os.path.join(temp_dir, path)).convert('RGB') for path in img_paths]
    while len(images) < 4:
        images.append(Image.new('RGB', (1, 1), (255, 255, 255)))

    # Calculate dimensions with margins
    w_left = max(images[2].width, images[3].width)
    w_right = max(images[0].width, images[1].width)
    h_top = max(images[2].height, images[0].height)
    h_bottom = max(images[3].height, images[1].height)

    total_width = w_left + w_right + margin
    total_height = h_top + h_bottom + margin

    canvas = Image.new('RGB', (total_width, total_height), (255, 255, 255))

    # Positions based on your layout
    positions = {
        0: (w_left + margin, 0),           # Image 1 → top-right
        1: (w_left + margin, h_top + margin),  # Image 2 → bottom-right
        2: (0, 0),                         # Image 3 → top-left
        3: (0, h_top + margin),           # Image 4 → bottom-left
    }

    for i, img in enumerate(images):
        x, y = positions[i]
        canvas.paste(img, (x, y))

    # Save with high quality
    out_path = os.path.join(output_dir, f"page_{page_num:03d}.jpg")
    canvas.save(out_path, quality=page_quality, subsampling=0)

# === PROCESS IN GROUPS OF 4 ===
total_pages = ceil(len(image_files) / 4)
for i in range(total_pages):
    chunk = image_files[i*4:(i+1)*4]
    create_custom_page(chunk, i+1)

# === ZIP OUTPUT PAGES ===
with zipfile.ZipFile(final_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for file_name in sorted(os.listdir(output_dir)):
        file_path = os.path.join(output_dir, file_name)
        zipf.write(file_path, arcname=file_name)

print(f"✅ All {total_pages} pages saved and zipped as '{final_zip}'!")
