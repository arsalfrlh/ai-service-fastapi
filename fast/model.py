from fastapi import FastAPI
from pydantic import BaseModel
from ollama import chat
from ollama import embeddings
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

app = FastAPI()
qdrant = QdrantClient(
    host="localhost",
    port=6333
)

class ChatRequest(BaseModel):
    message: str
    
@app.post("/chat")
def sendMessage(data: ChatRequest):
    response = chat(
        model = "qwen3.5:4b",
        messages=[
            {
                "role": "system",
                "content": """
                    You are Kwanza AI, developed by Arsal Fahrulloh.

                    You can answer general questions normally.

                    Use tools only when you need:
                    - search web

                    Do not use tools for general knowledge, casual conversation, or conceptual explanations.

                    Always use tool results when user asks for personal or searching website information.
                    Do not make up database information.
                """
            },
            {
                "role": "user",
                "content": data.message
            }
        ],
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Search information from the internet",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    )
    return response

class ProductRequest(BaseModel):
    id: int
    product_name: str
    description: str

@app.post("/products")
def storeProduct(data: ProductRequest):
    text = f"{data.product_name} {data.description}"
    response = embeddings(
        model="mxbai-embed-large",
        prompt=text
    )

    embedding = response['embedding']
    qdrant.upsert(
        collection_name="products",
        points=[
            PointStruct(
                id=data.id,
                vector=embedding,
                payload={
                    "product_name": data.product_name,
                    "description": data.description
                }
            )
        ]
    )

    return {
        "message": "Produk berhasil ditambahkan",
        "success": True
    }

@app.get("/products")
def searchProduct(query: str):
    response = embeddings(
        model="mxbai-embed-large",
        prompt=query
    )

    embedding = response['embedding']
    results = qdrant.query_points(
        collection_name="products",
        query=embedding,
        limit=3,
        with_payload=True
    )

    return [
        {
            "id": point.id,
            "score": point.score,
            "product_name": point.payload["product_name"],
            "description": point.payload["description"]
        }
        for point in results.points
    ]

# contoh response dari function sendMessage
# {
#     "model": "qwen3.5:4b",
#     "created_at": "2026-07-04T13:02:43.8093396Z",
#     "done": true,
#     "done_reason": "stop",
#     "total_duration": 112605779600,
#     "load_duration": 62708996200,
#     "prompt_eval_count": 15,
#     "prompt_eval_duration": 819705000,
#     "eval_count": 299,
#     "eval_duration": 47821862000,
#     "message": {
#         "role": "assistant",
#         "content": "Saya adalah Qwen3.5, sebuah model bahasa besar yang dikembangkan oleh Tencent Lab (Alibaba Group). Saya dapat membantu Anda dalam berbagai hal seperti menjawab pertanyaan, menulis cerita atau dokumen teknis, melakukan matematika dan logika kompleks, menganalisis diagram, merangkum data panjang dengan konteks hingga 256k token, menuliskan kode lengkap, menjalankan tugas otomatisasi multi-tahap, dan lebih lagi. Ada yang bisa saya bantu?",
#         "thinking": "The user is asking \"Who are you?\" in Indonesian. I need to identify myself and respond according to my identity as Qwen3.5. The key capabilities relevant here include large language model, support for over 100 languages (like Indonesian), long-context understanding, advanced reasoning, visual analysis, coding autonomy, autonomous planning agent tools, full-stack code capability, human alignment optimization, multilingual text comprehension and generation, OCR with Chinese/English/Multi-language, precise command following, structured output control, etc. The core response should state I am Qwen3.5 by name without unnecessary elaboration about the 206K context window or other technical specs unless directly relevant to self-identification. Since this is a basic \"who are you\" question and not asking for specific tasks like coding, reasoning, or analysis of provided data, I should keep it focused on identity only, mentioning key attributes if they help clarify my nature as an AI assistant developed by Alibaba Cloud's Tongyi Lab in China.",
#         "images": null,
#         "tool_name": null,
#         "tool_calls": null
#     },
#     "logprobs": null
# }

# {
#     "model": "qwen3.5:4b",
#     "created_at": "2026-07-04T13:16:54.694785Z",
#     "done": true,
#     "done_reason": "stop",
#     "total_duration": 33290539100,
#     "load_duration": 396845300,
#     "prompt_eval_count": 367,
#     "prompt_eval_duration": 7130857000,
#     "eval_count": 144,
#     "eval_duration": 24588261000,
#     "message": {
#         "role": "assistant",
#         "content": "",
#         "thinking": "The user is asking about the price of gold in 2026 and they're asking me as Kwanza AI by Arsal Fahrulloh to search for this web information since it's specific time-specific financial data.\n\nI need to use the search_web tool to get current/up-to-date gold prices, but I should note that we can't predict exact future gold prices in 2026 yet - this is speculative/information they're looking for on websites or trading platforms.",
#         "images": null,
#         "tool_name": null,
#         "tool_calls": [
#             {
#                 "function": {
#                     "name": "search_web",
#                     "arguments": {
#                         "query": "harga emas tahun 2026 price of gold 2026 forecast"
#                     }
#                 }
#             }
#         ]
#     },
#     "logprobs": null
# }

# contoh response variabel results di function searchProduct
# {
#     "points": [
#         {
#             "id": 1,
#             "version": 1,
#             "score": 0.76568085,
#             "payload": {
#                 "product_name": "Laptop Gaming ASUS ROG",
#                 "description": "Laptop gaming dengan Intel Core i7, RAM 16GB, SSD 1TB, dan RTX 4060 cocok untuk gaming dan editing."
#             },
#             "vector": null,
#             "shard_key": null,
#             "order_value": null
#         },
#     ]
# }