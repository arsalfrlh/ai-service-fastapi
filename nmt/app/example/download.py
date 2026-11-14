from huggingface_hub import snapshot_download

MODEL_ID = "cstr/madlad400-3b-ct2-int8"

MODEL_DIR = r"E:\model\nmt"

print("Downloading MADLAD-400 CT2 INT8...")

path = snapshot_download(
    repo_id=MODEL_ID,
    local_dir=MODEL_DIR
)

print("Download completed!")
print("Location:", path)
