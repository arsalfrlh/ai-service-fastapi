from pydantic import BaseModel, Field

class TextToImageRequest(BaseModel):
    prompt: str = Field(min=1, description="Prompt untuk mengahsilkan gambar") #Apa yang harus digambar?
    negative_prompt: str | None = None #Apa yang sebaiknya dihindari?
    width: int = Field(default=512,ge=256,le=768) #lebar image
    height: int = Field(default=512,ge=256,le=768) #tinggi image
    num_inference_steps: int = Field(default=20, ge=1, le=50) #Berapa banyak tahapan pengerjaan.
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0) #Seberapa keras pelukis harus mengikuti instruksi.
    seed: int | None = None #Kondisi/random awal sebelum mulai melukis.
    #Scheduler: Metode/cara pelukis mengubah sketsa awal menjadi lukisan akhir.
    #Strength: Seberapa jauh gambar asli diubah