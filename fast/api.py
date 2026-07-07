from fastapi import FastAPI #import dari library
from pydantic import BaseModel
import httpx

app = FastAPI() #buat variabel fast apinya

class ChatRequest(BaseModel): #class dengan isi parameter BaseModel(ini dari library pydantic)
    message: str #deklarasi variabel | parameter yg akan dibutuhkan saat menggunakan class ChatRequest ini
    
@app.post("/chat") #variabel app itu FastAPI dan juga ini endpoint api nya
async def sendMessage(data: ChatRequest): #function async bisa menggunakan await
    async with httpx.AsyncClient(timeout=120) as http: #library httpx di deklarasikan sebagai variabel http dan timeout itu 2mnt| async with ini khusus async untuk library
        response = await http.post("http://localhost:11434/api/chat", json={ #json itu body request| buat variabel response dan kirim await request post dengan library httpx dan program bisa menunggu response dari ollama karena await
            "model": "qwen3.5:4b",
            "stream": False,
            "messages": [
                {
                    "role": "user",
                    "content": data.message
                }
            ]
        })
        
        return response.json() #return dan decode hasil response dari api ollama
    return{
        "message": "Terjadi kesalahan",
        "success": False
    }
    
class ProductRequest(BaseModel):
    id: int
    product_name: str
    description: str
    
@app.post("/products")
async def storeProduct(data: ProductRequest):
    text = f"{data.product_name} {data.description}"
    async with httpx.AsyncClient(timeout=120) as http:
        response = await http.post("http://localhost:11434/api/embeddings", json={
            "model": "mxbai-embed-large",
            "prompt": text
        })
        
        embedding = response.json()['embedding']
    async with httpx.AsyncClient(timeout=60) as http:
        response = await http.put("http://localhost:6333/collections/products/points", json={
            "points": [
                {
                    "id": data.id,
                    "vector": embedding,
                    "payload": {
                        "product_name": data.product_name,
                        "description": data.description
                    }
                }
            ]
        })
        
        return {
            "message": "Produk berhasil ditambahkan",
            "success": True
        }
    return{
        "message": "Gagal menambahkan product",
        "success": False
    }
        
@app.get("/products")
async def searchProduct(query: str):
    async with httpx.AsyncClient(timeout=120) as http:
        response = await http.post("http://localhost:11434/api/embeddings", json={
            "model": "mxbai-embed-large",
            "prompt": query
        })

        embedding = response.json()['embedding']

        search = await http.post("http://localhost:6333/collections/products/points/search", json={
            "vector": embedding,
            "limit": 3,
            "with_payload": True
        })
        return search.json()['result']
    
    return{
        "message": "Gagal mencari product",
        "success": False
    }