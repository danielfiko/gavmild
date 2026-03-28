import base64
import os

from openai import OpenAI
from PIL import Image
from io import BytesIO

from flask import current_app


prompt = """A flat, minimal illustration representing:
"[PRODUCT_NAME]". [DESCRIPTION].

Style: flat design, simple geometric shapes,
limited color palette of 3-5 soft harmonious colors,
clean white or light background, no text, no labels,
no shadows, icon-like composition, centered subject.
Suitable as a product placeholder in a modern wishlist app.
"""


def generate_image(product_name: str, description: str) -> str:
    client = OpenAI(api_key=current_app.config["OPENAI_TOKEN"])
    folder_path = os.path.join(
        current_app.root_path, "static", "img", "generated_images"
    )
    os.makedirs(folder_path, exist_ok=True)
    response = client.images.generate(
        prompt=prompt.replace("[PRODUCT_NAME]", product_name).replace(
            "[DESCRIPTION]", description
        ),
        model="gpt-image-1-mini",
        output_format="webp",
        quality="medium",
        size="1024x1024",
    )

    if (
        response.data is None
        or len(response.data) == 0
        or response.data[0].b64_json is None
    ):
        raise ValueError("No image data received from OpenAI API")

    image_data = response.data[0].b64_json
    image_bytes = base64.b64decode(image_data)
    image = Image.open(BytesIO(image_bytes))
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in product_name)[
        :60
    ]
    while True:
        filename = f"{safe_name}_{os.urandom(4).hex()}.webp"
        file_path = os.path.join(folder_path, filename)
        if not os.path.exists(file_path):
            break
    image.save(file_path)
    return file_path
