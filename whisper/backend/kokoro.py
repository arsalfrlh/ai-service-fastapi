# https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
import soundfile as sf
from kokoro_onnx import Kokoro

print("Loading model...")

kokoro = Kokoro(
    model_path="models/kokoro-v1.0.int8.onnx",
    voices_path="models/voices-v1.0.bin"
)

print("Model berhasil dimuat.")

text = input("Masukkan teks : ")

audio, sample_rate = kokoro.create(
    text=text,
    voice="af_sarah",
    speed=1.0,
    lang="en-us"
)

sf.write("output.wav", audio, sample_rate)

print("Selesai!")
print("File disimpan : output.wav")