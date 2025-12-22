"""Example Flux-Schnell image generation app using Jarvis SDK."""

import jarvis
from pydantic import BaseModel
import base64
from io import BytesIO
import torch
from diffusers import FluxPipeline


class PromptInput(BaseModel):
    """Input model for the image generation endpoint."""
    prompt: str
    width: int = 512
    height: int = 512


class PromptOutput(BaseModel):
    """Output model for the prompt endpoint."""
    image_base64: str
    format: str = "png"


@jarvis.app(requirements=["diffusers", 
                          "transformers", 
                          "accelerate", 
                          "protobuf", 
                          "sentencepiece"])
class FluxSchnell:
    """Flux-Schnell image generation model.

    This demonstrates:
    - Loading a model once in setup()
    - Generating images from text prompts
    - Returning base64 encoded images
    """

    def setup(self):
        """Initialize the Flux-Schnell model. Called once on app startup."""
        self.pipe = FluxPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-schnell",
            torch_dtype=torch.bfloat16,
        ).to("cuda")
        

    @jarvis.endpoint()
    def generate(self, input: PromptInput) -> PromptOutput:
        """Generate an image from a text prompt."""
        # Generate image using Flux-Schnell pipeline
        image = self.pipe(
            input.prompt,
            width=input.width,
            height=input.height,
            num_inference_steps=4  # Schnell is optimized for 1-4 steps
        ).images[0]

        # Convert PIL Image to base64
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        # Add data URI prefix for direct HTML embedding
        data_uri = f"data:image/png;base64,{img_base64}"

        return PromptOutput(image_base64=data_uri, format="png")
