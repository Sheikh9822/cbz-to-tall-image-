import cv2
import pytesseract
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

# --- Configuration ---
# Path to your Tesseract executable (only needed for Windows if not in PATH)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Path to the input image
INPUT_IMAGE_PATH = '001.png'  # Replace with your image file
OUTPUT_IMAGE_PATH = 'translated_manga_page.png'

# Dictionary mapping original Russian text to translated English text
# This needs to be manually created or obtained from an OCR process
TEXT_MAPPINGS = {
    "ЗАПЕЧАТАННАЯ ПЕЩЕРА, САМАЯ ГЛУБОКАЯ ЧАСТЬ": "SEALED CAVE, THE DEEPEST PART",
    "НЕВОЛЬНО ВСПОМИНАЕТСЯ… ЭТО МЕСТО…": "IT'S UNWILLINGLY REMEMBERED... THIS PLACE...",
    "ЭТО МЕСТО – НАЧАЛО НАШЕЙ ИСТОРИИ.": "THIS PLACE IS THE BEGINNING OF OUR STORY.",
    "КСТАТИ, ПО ДНЕВНИКУ ЭТО 90-Й ДЕНЬ ПОСЛЕ ПЕРЕ-\nРОЖДЕНИЯ.": "BY THE WAY, ACCORDING TO THE DIARY, THIS IS THE 90TH DAY AFTER REBIRTH.",
    "КАК ЖЕ Я ЭТОГО ЖДАЛ, РИМУРУ!": "HOW I WAITED FOR THIS, RIMURU!",
    "ВЕЛЬДОРА.": "VELDO RA.",
    "XM!": "HM!",
    "LIVE": "LIVE",
    "ВЫ ВЕДЬ СОВЕРШИЛИ ПЛОХОЕ, И ПОЭТОМУ БЫЛИ ЗАПЕЧАТАНЫ НА 300 ЛЕТ.": "YOU DID SOMETHING BAD, AND THEREFORE YOU WERE SEALED FOR 300 YEARS.",
    "БУДТО Я СОВЕРШИЛ ЧТО-ТО ПЛОХОЕ И БЫЛ ЗАКЛЮЧЁН В ТЮРЬМУ.": "AS IF I DID SOMETHING BAD AND WAS IMPRISONED.",
    "Ха-\nХа-\nХа": "Ha-\nHa-\nHa",
    "ПОЗДРАВЛЯЮ\nВЕЛЬДОРА": "CONGRATULATIONS\nVELDO RA",
    "ОСВО-\nБОЖДЕНИЕ\nЗВУЧИТ\nКАК-ТО\nГРУБО.": "LIBERATION\nSOUNDS\nRATHER\nROUGH.",
    "С ОСВО-\nБОЖДЕНИЕМ,\nГОСПОДИН\nВЕЛЬДОРА!": "CONGRATULATIONS ON YOUR LIBERATION, LORD VELDO RA!"
}

# Font path for rendering the new text. You might need to download a suitable font.
# Common fonts: Arial, Times New Roman, or custom fonts.
# Example: Download a font like "Roboto-Regular.ttf" and place it in the same directory
# or provide the full path.
DEFAULT_FONT_PATH = 'arial.ttf' # Replace with a valid font path if arial.ttf is not available

# --- Helper Functions ---

def find_text_boxes(image_path, lang='rus'):
    """
    Detects text boxes in the image using Tesseract's page segmentation mode (PSM 6).
    Returns a list of dictionaries, each containing 'text', 'box' (coordinates), and 'confidence'.
    """
    try:
        # Load image with OpenCV
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Could not load image from {image_path}")
            return []

        # Ensure image is in RGB format for Pillow if needed later
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Use Tesseract to get data that includes bounding boxes
        # --psm 6 assumes a single uniform block of text.
        # --psm 7 treats the image as a single text line.
        # --psm 11 sparse text. Find as much text as possible in no particular order.
        # --psm 12 sparse text with Find as much text as possible in no particular order.
        # Let's try a more general approach that captures individual text blocks.
        # We'll use PSM 3 (Default, based on page layout) and then process blocks.
        # For manga, it might be better to use PSM 6 or 11/12 if blocks are distinct.
        # For complex layouts, more advanced detection like EAST or YOLO might be needed.

        # Tesseract's output_type='dict' gives us detailed information including boxes
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)

        detected_texts = []
        n_boxes = len(data['level'])
        for i in range(n_boxes):
            # Filter for meaningful text blocks (level 5 is word level)
            if data['level'][i] == 5:
                text = data['text'][i].strip()
                if text: # Only consider if there's actual text
                    (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                    confidence = int(data['conf'][i])
                    # We might want to filter by confidence if there are many false positives
                    if confidence > 50: # Adjust confidence threshold as needed
                        detected_texts.append({
                            'text': text,
                            'box': (x, y, x + w, y + h), # (x1, y1, x2, y2)
                            'confidence': confidence
                        })
        return detected_texts

    except pytesseract.TesseractNotFoundError:
        print("Tesseract is not installed or not in your PATH. Please install it.")
        return []
    except Exception as e:
        print(f"An error occurred during text detection: {e}")
        return []

def get_best_matching_text(detected_text, text_mappings):
    """
    Finds the best match for detected text in the provided mappings.
    This is a simplified matching. For real-world use, you might need fuzzy matching
    or a more robust comparison.
    """
    # Exact match first
    if detected_text in text_mappings:
        return text_mappings[detected_text]

    # More flexible matching: check if detected text is a substring of a mapped key
    # or vice versa. This is prone to errors in complex cases.
    # A better approach would be to align the OCR output with the expected dialogues.
    for original, translated in text_mappings.items():
        if detected_text in original or original in detected_text:
            # Check if this is a better fit than current best match
            # This simple approach just returns the first plausible match found
            return translated
    return None

def fill_background(image_pil, box):
    """
    Fills the area defined by the box with a background color.
    This is a simple fill. For better results, you'd want to sample surrounding pixels.
    """
    draw = ImageDraw.Draw(image_pil)
    # You can try to sample a background color from the vicinity of the box
    # For simplicity, let's assume a white background for now if the text is black.
    # In manga, backgrounds can be varied (halftones, gradients, solid colors).
    # A more sophisticated approach would be to find the dominant color around the box.

    # Simple approach: Fill with white if the text is generally dark.
    # This is a very basic assumption.
    # A better method: analyze pixels around the box.
    # Let's try to get a sample color from the top-left corner of the box
    # If the image is loaded as RGB, use image_pil.
    x1, y1, x2, y2 = box
    if x1 < 0: x1 = 0
    if y1 < 0: y1 = 0
    if x2 > image_pil.width: x2 = image_pil.width
    if y2 > image_pil.height: y2 = image_pil.height

    # A crude way to get background color: take a pixel from just above the box
    sample_x = x1 + (x2 - x1) // 2
    sample_y = y1 - 5 # 5 pixels above
    if sample_y < 0: sample_y = y1 # Fallback if box is at the very top

    try:
        background_color = image_pil.getpixel((sample_x, sample_y))
    except IndexError: # Handle cases where sample_y is out of bounds
        background_color = (255, 255, 255) # Default to white if sampling fails

    draw.rectangle(box, fill=background_color)
    return image_pil

def render_text_with_outline(draw, text, position, font, text_color=(0,0,0), outline_color=(255,255,255), outline_width=1):
    """
    Renders text with an outline for better visibility on busy backgrounds.
    """
    x, y = position
    # Draw outline for each character
    for i in range(len(text)):
        char = text[i]
        if char == '\n': # Handle newlines
            # Calculate the y offset for the next line
            # This requires font metrics, which Pillow's default draw doesn't easily expose
            # For simplicity, we'll assume a fixed line spacing or rely on Pillow's textwrap later
            continue

        # Get bounding box for the character to draw the outline around it
        # This is complex with Pillow's basic draw. A more robust solution
        # would be to render the text to an intermediate surface and then dilate it.
        # For simplicity, we'll simulate an outline by drawing around the text.

        # Outline effect: Draw the text multiple times shifted slightly.
        # This is a common technique.
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx == 0 and dy == 0: continue # Skip the center
                if abs(dx) + abs(dy) > outline_width: continue # Limit to a square/diamond shape
                draw.text((x + dx, y + dy), char, font=font, fill=outline_color)

    # Draw the main text
    draw.text(position, text, font=font, fill=text_color)

def get_font(font_path, font_size):
    """Loads a font with a given size."""
    if not os.path.exists(font_path):
        print(f"Warning: Font not found at {font_path}. Using default Pillow font (may not support Cyrillic).")
        # Fallback if font not found, though this might not render Cyrillic well.
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(font_path, font_size)
    except IOError:
        print(f"Error loading font from {font_path}. Ensure it's a valid .ttf or .otf file.")
        return ImageFont.load_default()

def main():
    print("Starting text replacement process...")

    # Load the original image
    try:
        img_cv = cv2.imread(INPUT_IMAGE_PATH)
        if img_cv is None:
            print(f"Error: Could not load image from {INPUT_IMAGE_PATH}")
            return
        img_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
    except Exception as e:
        print(f"Error loading image: {e}")
        return

    # Get detected text and their bounding boxes
    # Try Russian first, then English if Russian isn't found for the original text.
    # The input image is Russian, so we primarily need Russian OCR.
    detected_texts_rus = find_text_boxes(INPUT_IMAGE_PATH, lang='rus')

    if not detected_texts_rus:
        print("No Russian text detected. Trying with English OCR (might not be accurate for original text).")
        detected_texts_eng = find_text_boxes(INPUT_IMAGE_PATH, lang='eng')
        detected_texts = detected_texts_eng # Use English detection if Russian fails
    else:
        detected_texts = detected_texts_rus

    if not detected_texts:
        print("No text detected in the image. Exiting.")
        return

    print(f"Detected {len(detected_texts)} text blocks.")

    draw = ImageDraw.Draw(img_pil)

    # Process each detected text block
    for detected in detected_texts:
        original_text = detected['text']
        box = detected['box'] # (x1, y1, x2, y2)

        # Try to find a translation for this detected text
        # This matching is crucial and can be tricky.
        # The TEXT_MAPPINGS is pre-defined. In a real application, you'd want
        # a robust way to link OCR output to these mappings.
        # For this example, we assume the detected_text.strip() is a good key.
        translated_text = None
        if original_text in TEXT_MAPPINGS:
            translated_text = TEXT_MAPPINGS[original_text]
        else:
            # Fallback to a simple substring check (less reliable)
            for key, value in TEXT_MAPPINGS.items():
                if original_text in key:
                    translated_text = value
                    print(f"Found partial match for '{original_text}': using '{translated_text}'")
                    break
                if key in original_text:
                    translated_text = value
                    print(f"Found partial match for '{original_text}': using '{translated_text}'")
                    break

        if translated_text:
            print(f"Replacing: '{original_text}' with '{translated_text}'")

            # 1. Fill the background of the original text
            img_pil = fill_background(img_pil, box)

            # 2. Render the translated text
            x1, y1, x2, y2 = box
            text_width = x2 - x1
            text_height = y2 - y1

            # Estimate font size based on the original text's bounding box height
            # This is an approximation. A more accurate way would be to measure text width/height.
            font_size = int(text_height * 0.8) # Adjust multiplier as needed
            if font_size <= 0: font_size = 12 # Minimum font size

            # Load font
            font = get_font(DEFAULT_FONT_PATH, font_size)

            # Handle multi-line text if necessary.
            # Pillow's draw.text doesn't automatically wrap. We need to split lines.
            lines = translated_text.split('\n')
            current_y = y1
            for line in lines:
                if not line.strip(): continue # Skip empty lines

                # Get the size of the text line with the current font
                try:
                    # Pillow 10+ uses textbbox. Older versions used textsize.
                    if hasattr(font, 'getbbox'): # Pillow 10+
                        line_bbox = font.getbbox(line)
                        line_width = line_bbox[2] - line_bbox[0]
                        line_height = line_bbox[3] - line_bbox[1]
                    else: # Older Pillow versions
                        line_width, line_height = draw.textlength(line, font=font), font.getsize(line)[1] # Deprecated
                        # Fallback for truly old versions where getsize might be the only option
                        # if hasattr(font, 'getsize'):
                        #     line_width, line_height = font.getsize(line)
                        # else:
                        #     # Very old Pillow or custom font might not have these
                        #     print(f"Warning: Cannot get text size for '{line}'. Assuming default height.")
                        #     line_height = font_size # Approximation

                    # Center the text horizontally within the original box
                    padding_x = (text_width - line_width) / 2
                    render_x = x1 + padding_x

                    # Center the text vertically within the original box if it's the first line
                    # and there's space. For multi-line, adjust line spacing.
                    if len(lines) == 1:
                        padding_y = (text_height - line_height) / 2
                        render_y = y1 + padding_y
                    else:
                        render_y = current_y
                        # Add some line spacing
                        current_y += line_height + (text_height / len(lines) * 0.2) # Adjust spacing

                    # Render the text with a simple outline for better visibility
                    render_text_with_outline(
                        draw,
                        line,
                        (render_x, render_y),
                        font,
                        text_color=(0, 0, 0), # Black text
                        outline_color=(255, 255, 255), # White outline
                        outline_width=1 # Outline thickness
                    )
                except Exception as e:
                    print(f"Error rendering line '{line}': {e}")

    # Save the modified image
    try:
        img_pil.save(OUTPUT_IMAGE_PATH)
        print(f"Successfully saved translated image to {OUTPUT_IMAGE_PATH}")
    except Exception as e:
        print(f"Error saving image: {e}")

if __name__ == "__main__":
    # Create dummy font file if it doesn't exist, so the script can run without immediate font error
    # You MUST replace this with a real font that supports Cyrillic if you want correct rendering.
    if not os.path.exists(DEFAULT_FONT_PATH):
        print(f"'{DEFAULT_FONT_PATH}' not found. Creating a dummy file. Please replace it with a real font (e.g., Arial, Roboto) that supports Cyrillic for proper rendering.")
        try:
            # Create an empty file as a placeholder
            with open(DEFAULT_FONT_PATH, 'w') as f:
                pass
        except IOError as e:
            print(f"Could not create dummy font file: {e}")

    main()
