import torch
from diffusers import StableDiffusionPipeline


MODEL_PATH = (
    r"F:\model\diffusion"
    r"\v1-5-pruned-emaonly.safetensors"
)

print("Loading model...")

pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH,
    torch_dtype=torch.float32,
)

pipe = pipe.to("cpu")

print("Model loaded.")

result = pipe(
    prompt="a photo of a cat",
    negative_prompt="",
    width=512,
    height=512,
    num_inference_steps=5,
    guidance_scale=7.0,
)

image = result.images[0]
image.save("cpu_test.png")

print("Saved cpu_test.png")