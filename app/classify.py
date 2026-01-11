import torch
from PIL import Image
from io import BytesIO
from transformers import CLIPProcessor, CLIPModel

# Load model and processor (CPU version)
MODEL_ID = "openai/clip-vit-base-patch32"
model = CLIPModel.from_pretrained(MODEL_ID)
processor = CLIPProcessor.from_pretrained(MODEL_ID, use_fast=True)

def coenter_crop_image(image: Image.Image, size: int = 224) -> Image.Image:
    """Center crop the image to a square of given size."""
    width, height = image.size
    min_dim = min(width, height)
    left = (width - min_dim) / 2
    top = (height - min_dim) / 2
    right = left + min_dim
    bottom = top + min_dim

    image = image.crop((left, top, right, bottom))
    image = image.resize((size, size))
    return image

def classify_image_bytes(image_bytes: bytes, labels: list[str], threshold: float = 0.5) -> list[dict]:
    if labels is None or len(labels) == 0:
        return []

    image = Image.open(BytesIO(image_bytes)).convert("RGB")

    image = coenter_crop_image(image, size=224)

    inputs = processor(text=labels, images=image, return_tensors="pt", padding=True)

    with torch.no_grad():
        outputs = model(**inputs)
    
    # Calculate probabilities (softmax)
    logits_per_image = outputs.logits_per_image
    probs = logits_per_image.softmax(dim=1).flatten()

    results_with_conf = [(labels[i], float(probs[i])) for i in range(len(labels)) if float(probs[i]) >= threshold]
    results_with_conf.sort(key=lambda x: x[1], reverse=True)

    return [tag for tag, conf in results_with_conf]