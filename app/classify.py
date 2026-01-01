import torch
from PIL import Image
from io import BytesIO
from transformers import CLIPProcessor, CLIPModel

# Load model and processor (CPU version)
MODEL_ID = "openai/clip-vit-base-patch32"
model = CLIPModel.from_pretrained(MODEL_ID)
processor = CLIPProcessor.from_pretrained(MODEL_ID, use_fast=True)

# Default rooms, but you can override these via API
DEFAULT_ROOMS = ["kitchen", "living room", "bedroom", "bathroom", "dining room", "office"]

def classify_image_bytes(image_bytes, labels=None):
    labels = labels or DEFAULT_ROOMS
    image = Image.open(BytesIO(image_bytes)).convert("RGB")

    # CLIP processes images and text labels simultaneously
    inputs = processor(text=labels, images=image, return_tensors="pt", padding=True)

    with torch.no_grad():
        outputs = model(**inputs)
    
    # Calculate probabilities (softmax)
    logits_per_image = outputs.logits_per_image
    probs = logits_per_image.softmax(dim=1).flatten()

    # Build sorted results
    results = [
        {"tag": labels[i], "confidence": round(float(probs[i]), 4)}
        for i in range(len(labels))
    ]
    return sorted(results, key=lambda x: x["confidence"], reverse=True)