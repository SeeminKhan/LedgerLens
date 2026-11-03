from pathlib import Path
from paddleocr import PaddleOCR

image_path = Path("data/raw/images.png")

print("Initializing OCR...")
ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    device="cpu",
    engine="paddle_dynamic",
    enable_mkldnn=False,
    cpu_threads=1,
)

print("Starting prediction...")
result = ocr.predict(input=str(image_path))

print("Prediction completed!")

for page in result:
    data = page.json
    if callable(data):
        data = data()
    res = data.get("res", data)
    print("Detected regions:", len(res.get("rec_texts", [])))