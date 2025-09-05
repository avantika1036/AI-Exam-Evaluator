import pytesseract
from PIL import Image

# If needed, specify exact exe path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

img = Image.open("test.jpg")  # replace with your image file
text = pytesseract.image_to_string(img)

print("✅ OCR Extracted Text:\n", text)
