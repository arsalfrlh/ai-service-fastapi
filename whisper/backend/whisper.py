from faster_whisper import WhisperModel

print("Loading...")

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

print("Model berhasil dimuat")

segments, info = model.transcribe(
    "voice.wav",
    beam_size=5
    # language="id"
)

print("===>Hasil<===")
for segment in segments:
    print(f"Teks: {segment.text}\n")
    print(f"Bahasa: {info.language} | Durasi: {info.duration}")