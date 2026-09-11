"""Example SD-Turbo image generation app using JLServe.

The small model used for the first serverless proof of concept: about 5 GB,
one denoising step, fits comfortably on an L4. Same shape as flux-schnell.py
with a different model id, one step instead of four, bounded image sizes, and
the deploy settings declared on the decorator.
"""

import base64
from io import BytesIO

import jlserve
from pydantic import BaseModel, Field


class PromptInput(BaseModel):
    """Input model for the image generation endpoint."""
    prompt: str = Field(min_length=1, max_length=1000)
    # Bounded so a caller cannot request an image that runs the GPU out of
    # memory. Multiples of 8 are what the VAE expects.
    width: int = Field(default=512, ge=256, le=768, multiple_of=8)
    height: int = Field(default=512, ge=256, le=768, multiple_of=8)


class PromptOutput(BaseModel):
    """Output model for the prompt endpoint."""
    image_base64: str
    format: str = "png"


@jlserve.app(
    requirements=["diffusers", "transformers", "accelerate"],
    weights=["stabilityai/sd-turbo"],
    gpu="L4",
    gpus_per_worker=1,
    min_workers=0,
    max_workers=1,
    idle_timeout=300,
)
class SDTurbo:
    """SD-Turbo image generation model.

    This demonstrates:
    - Loading a model once in setup()
    - Generating images from text prompts in a single step
    - Bounded inputs so a request cannot exhaust GPU memory
    - Deploy settings declared next to the code, including the weights the
      platform must place on the worker before it starts (workers have no
      internet; the id here matches the one in setup())
    """

    def setup(self):
        """Initialize the SD-Turbo pipeline. Called once on app startup."""
        import torch
        from diffusers import AutoPipelineForText2Image

        self.pipe = AutoPipelineForText2Image.from_pretrained(
            "stabilityai/sd-turbo",
            torch_dtype=torch.float16,
            variant="fp16",
        ).to("cuda")

    @jlserve.endpoint()
    def generate(self, input: PromptInput) -> PromptOutput:
        """Generate an image from a text prompt."""
        image = self.pipe(
            input.prompt,
            width=input.width,
            height=input.height,
            num_inference_steps=1,  # SD-Turbo is trained for a single step
            guidance_scale=0.0,     # and does not use classifier-free guidance
        ).images[0]

        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return PromptOutput(image_base64=f"data:image/png;base64,{img_base64}", format="png")
