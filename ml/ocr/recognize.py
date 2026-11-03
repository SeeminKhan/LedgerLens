
import json
from pathlib import Path

from paddleocr import PaddleOCR

# Project paths
ML_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = ML_DIR / "data" / "raw"
OUTPUT_DIR = ML_DIR / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_text(image_path: Path) -> list[dict]:
    """Run OCR and return detected text, confidence, and bounding boxes."""

    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )

    result = ocr.predict(input=str(image_path))

    extracted = []

    for page in result:
        data = page.json
        if callable(data):
            data = data()

        res = data.get("res", data)

        texts = res.get("rec_texts", [])
        scores = res.get("rec_scores", [])
        boxes = res.get("rec_polys", [])

        for text, score, box in zip(texts, scores, boxes):
            extracted.append({
                "text": text,
                "confidence": float(score),
                "bounding_box": box.tolist() if hasattr(box, "tolist") else box,
            })

    return extracted


if __name__ == "__main__":
    images = [
        path for path in INPUT_DIR.iterdir()
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]

    if not images:
        raise FileNotFoundError(f"No invoice images found in {INPUT_DIR}")

    image_path = images[0]
    print(f"Processing: {image_path.name}")

    results = extract_text(image_path)

    output_path = OUTPUT_DIR / f"{image_path.stem}_ocr.json"
    output_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Detected {len(results)} text regions")
    print(f"Saved OCR output to: {output_path}")
