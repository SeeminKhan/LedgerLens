
import json
import re
from pathlib import Path

ML_DIR = Path(__file__).resolve().parent.parent
OCR_FILE = ML_DIR / "outputs" / "sample_invoice_ocr.json"

# Manually verified text from our sample invoice.
EXPECTED_TEXT = """
INVOICE
LedgerLens
#LL-2025-1047
Smarter Document Intelligence
Bill To:
Date:
Oct 28, 2025
Due Date:
Nov 11, 2025
Acme Corp
Payment Terms: Net 15
123 Business Avenue,
Mumbai, Maharashtra - 400001
India
Description
Qty
Unit Price (INR)
Total (INR)
Enterprise Plan – Annual
1
50,000.00
50,000.00
Setup & Onboarding
1
5,000.00
5,000.00
Priority Support
1
3,000.00
3,000.00
Subtotal:
58,000.00
GST (18%):
10,440.00
Total:
₹68,440.00
Notes:
Thank you for your business!
For any queries, contact us at support@ledgerlens.com
support@ledgerlens.com
www.ledgerlens.com
Mumbai, India
Build. Organize. Grow.
"""


def levenshtein_distance(reference: str, prediction: str) -> int:
    """Calculate minimum edits needed to transform one string into another."""

    previous = list(range(len(prediction) + 1))

    for i, ref_char in enumerate(reference, start=1):
        current = [i]

        for j, pred_char in enumerate(prediction, start=1):
            insertion = current[j - 1] + 1
            deletion = previous[j] + 1
            substitution = previous[j - 1] + (ref_char != pred_char)

            current.append(min(insertion, deletion, substitution))

        previous = current

    return previous[-1]


def normalize(text: str) -> str:
    """Normalize whitespace and case for evaluation."""
    return re.sub(r"\s+", " ", text).strip().lower()


def main():
    with OCR_FILE.open(encoding="utf-8") as file:
        results = json.load(file)

    predicted_text = " ".join(item["text"] for item in results)

    reference = normalize(EXPECTED_TEXT)
    prediction = normalize(predicted_text)

    char_errors = levenshtein_distance(reference, prediction)
    word_errors = levenshtein_distance(
        reference.split(),
        prediction.split()
    )

    cer = char_errors / len(reference) if reference else 0
    wer = word_errors / len(reference.split()) if reference else 0

    confidences = [item["confidence"] for item in results]

    print("\nOCR EVALUATION RESULTS")
    print("-" * 35)
    print(f"Text regions detected: {len(results)}")
    print(f"Reference characters: {len(reference)}")
    print(f"Reference words: {len(reference.split())}")
    print(f"Character Error Rate: {cer:.2%}")
    print(f"Word Error Rate: {wer:.2%}")
    print(f"Average OCR confidence: {sum(confidences) / len(confidences):.2%}")


if __name__ == "__main__":
    main()
