from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from ollama import chat
import json

app = FastAPI()

@app.exception_handler(RequestValidationError)
def validator_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "message": exc.errors(),
            "success": False
        }
    )

class WebsocketManager:
    def __init__(self):
        self.websocket: WebSocket | None = None

    async def connect(self, websocket: WebSocket):
        self.websocket = websocket
        await websocket.accept()
        await websocket.send_json({
            "event": "server-connected",
            "data": {
                "info": "Websocket connected"
            }
        })

    async def broadcast_message(self, message: dict, action: str):
        if self.websocket:
            await self.websocket.send_json({
                "event": "chatUpdate",
                "data": {
                    "action": action,
                    "message": message
                }
            })

    async def broadcast_response_ai(self, content: str, is_done: bool):
        if self.websocket:
            await self.websocket.send_json({
                "event": "responseAI",
                "data": {
                    "content": content,
                    "is_done": is_done
                }
            })

    async def broadcast_tool_calls(self, tool_name: str | None):
        if self.websocket:
            await self.websocket.send_json({
                "event": "toolCalls",
                "data": {
                    "tool_name": tool_name
                }
            })

manager = WebsocketManager()

@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await manager.connect(websocket)

    while True:
        try:
            data = await websocket.receive_json()
        except WebSocketDisconnect:
            print("Websocket disconnect")

class MessageRequest(BaseModel):
    message: str

@app.post("/message")
async def send_message(request: MessageRequest):
    return StreamingResponse(
        content=generate_chat(request),
        media_type="application/x-ndjson"
    )

async def generate_chat(request: MessageRequest):
    messages = []
    messages.append({
        "role": "system",
        "content": """
            You are Kwanza AI, developed by Arsal Fahrulloh.
            You can answer general questions normally.
            Use tools only when you need:
            - get_city
            - get_weather
            Do not use tools for general knowledge, casual conversation, or conceptual explanations.
            Always use tool results when user asks for personal or city name available in the database.
        """
    })

    messages.append({
        "role": "user",
        "content": request.message
    })

    message = {
        "role": "user",
        "content": request.message
    }
    await manager.broadcast_message(message, "create")

    while True:
        tool_calls_content = []
        tool_calls = []
        full_content = ""
        full_thinking = ""

        response = chat(
            model="qwen3.5:4b",
            stream=True,
            messages=messages,
            tools=tools()
        )

        for chunk in response:
            if chunk.message.thinking:
                full_thinking += chunk.message.thinking

            if chunk.message.content:
                full_content += chunk.message.content
                await manager.broadcast_response_ai(chunk.message.content, chunk.done)

            if chunk.message.tool_calls:
                tool_calls.extend(chunk.message.tool_calls)
                # tool_calls.extend([
                #     tool.model_dump()
                #     for tool in chunk.message.tool_calls
                # ])
            yield json.dumps(chunk.model_dump()) + "\n"

            if chunk.done:
                messages.append({
                    "role": "assistant",
                    "thinking": full_thinking,
                    "content": full_content,
                    "tool_calls": tool_calls
                })

                if tool_calls:
                    for tool in tool_calls:
                        tool_name = tool.function.name
                        arguments = tool.function.arguments or {}
                        # tool_name = tool['function']['name']
                        # arguments = tool['function']['arguments'] or {}
                        await manager.broadcast_tool_calls(tool_name)
                        result = exec_tool(tool_name, arguments)
                        await manager.broadcast_tool_calls(None)
                        tool_calls_content.append({
                            "role": "tool",
                            "tool_name": tool_name,
                            "content": json.dumps(result)
                        })
                    messages.extend(tool_calls_content)
                else:
                    assistant_message = {
                        "role": chunk.message.role,
                        "thinking": full_thinking,
                        "content": full_content
                    }
                    await manager.broadcast_message(assistant_message, "create")
                    # yield json.dumps(messages) + "\n"
                    return


def tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "get_city",
                "description": """
                    Get the list of cities available in the database.
                    This tool must be used when you need to know whether a city
                    exists in the database.
                    Do not assume that a city exists in the database.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": """
                    Get weather information for a city that exists in the database.
                    The city name must come from the database returned by get_city.
                    Do not invent city names or weather information.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city_name": {
                            "type": "string",
                            "description": "The exact city name from the database."
                        }
                    },
                    "required": [
                        "city_name"
                    ]
                }
            }
        }
    ]

def exec_tool(name: str, arguments: dict):
    if name == "get_city":
        return get_city()
    elif name == "get_weather":
        return get_weateher(arguments['city_name'])
    else:
        return {
            "message": "Error, Unknown Tool"
        }

def get_city():
    return [
        {
            "name": "Bandung",
            "province": "Jawa Barat"
        },
        {
            "name": "Jakarta",
            "province": "DKI Jakarta"
        }
    ]

def get_weateher(city_name: str):
    if city_name == "Bandung":
        return {
            "temperature": 24,
            "condition": "Hujan"
        }
    elif city_name == "Jakarta":
        return {
            "temperature": 32,
            "condition": "Cerah"
        }
    else:
        return {
            "message": "Error, Unknown City Name"
        }

### tool call city

# {
#     "model": "qwen3.5:4b",
#     "created_at": "2026-08-16T12:43:02.6929196Z",
#     "done": false,
#     "done_reason": null,
#     "total_duration": null,
#     "load_duration": null,
#     "prompt_eval_count": null,
#     "prompt_eval_duration": null,
#     "eval_count": null,
#     "eval_duration": null,
#     "message": {
#         "role": "assistant",
#         "content": "",
#         "thinking": " one",
#         "images": null,
#         "tool_name": null,
#         "tool_calls": null
#     },
#     "logprobs": null
# }
# {
#     "model": "qwen3.5:4b",
#     "created_at": "2026-08-16T12:43:04.7326459Z",
#     "done": false,
#     "done_reason": null,
#     "total_duration": null,
#     "load_duration": null,
#     "prompt_eval_count": null,
#     "prompt_eval_duration": null,
#     "eval_count": null,
#     "eval_duration": null,
#     "message": {
#         "role": "assistant",
#         "content": "",
#         "thinking": null,
#         "images": null,
#         "tool_name": null,
#         "tool_calls": [
#             {
#                 "function": {
#                     "name": "get_city",
#                     "arguments": {}
#                 }
#             }
#         ]
#     },
#     "logprobs": null
# }
# {
#     "model": "qwen3.5:4b",
#     "created_at": "2026-08-16T12:43:04.8540042Z",
#     "done": true,
#     "done_reason": "stop",
#     "total_duration": 38539686000,
#     "load_duration": 6765512200,
#     "prompt_eval_count": 512,
#     "prompt_eval_duration": 17778652000,
#     "eval_count": 118,
#     "eval_duration": 13974457000,
#     "message": {
#         "role": "assistant",
#         "content": "",
#         "thinking": null,
#         "images": null,
#         "tool_name": null,
#         "tool_calls": null
#     },
#     "logprobs": null
# }

### tool call weather
# {
#     "model": "qwen3.5:4b",
#     "created_at": "2026-08-16T12:43:11.4391971Z",
#     "done": false,
#     "done_reason": null,
#     "total_duration": null,
#     "load_duration": null,
#     "prompt_eval_count": null,
#     "prompt_eval_duration": null,
#     "eval_count": null,
#     "eval_duration": null,
#     "message": {
#         "role": "assistant",
#         "content": "",
#         "thinking": "get",
#         "images": null,
#         "tool_name": null,
#         "tool_calls": null
#     },
#     "logprobs": null
# }
# {
#     "model": "qwen3.5:4b",
#     "created_at": "2026-08-16T12:43:11.5577247Z",
#     "done": false,
#     "done_reason": null,
#     "total_duration": null,
#     "load_duration": null,
#     "prompt_eval_count": null,
#     "prompt_eval_duration": null,
#     "eval_count": null,
#     "eval_duration": null,
#     "message": {
#         "role": "assistant",
#         "content": "",
#         "thinking": "_weather",
#         "images": null,
#         "tool_name": null,
#         "tool_calls": null
#     },
#     "logprobs": null
# }
# {
#     "model": "qwen3.5:4b",
#     "created_at": "2026-08-16T12:43:15.2793432Z",
#     "done": false,
#     "done_reason": null,
#     "total_duration": null,
#     "load_duration": null,
#     "prompt_eval_count": null,
#     "prompt_eval_duration": null,
#     "eval_count": null,
#     "eval_duration": null,
#     "message": {
#         "role": "assistant",
#         "content": "",
#         "thinking": null,
#         "images": null,
#         "tool_name": null,
#         "tool_calls": [
#             {
#                 "function": {
#                     "name": "get_weather",
#                     "arguments": {
#                         "city_name": "Bandung"
#                     }
#                 }
#             }
#         ]
#     },
#     "logprobs": null
# }
# {
#     "model": "qwen3.5:4b",
#     "created_at": "2026-08-16T12:43:18.5271395Z",
#     "done": false,
#     "done_reason": null,
#     "total_duration": null,
#     "load_duration": null,
#     "prompt_eval_count": null,
#     "prompt_eval_duration": null,
#     "eval_count": null,
#     "eval_duration": null,
#     "message": {
#         "role": "assistant",
#         "content": "",
#         "thinking": null,
#         "images": null,
#         "tool_name": null,
#         "tool_calls": [
#             {
#                 "function": {
#                     "name": "get_weather",
#                     "arguments": {
#                         "city_name": "Jakarta"
#                     }
#                 }
#             }
#         ]
#     },
#     "logprobs": null
# }
# {
#     "model": "qwen3.5:4b",
#     "created_at": "2026-08-16T12:43:18.6472603Z",
#     "done": true,
#     "done_reason": "stop",
#     "total_duration": 13790466300,
#     "load_duration": 678148700,
#     "prompt_eval_count": 676,
#     "prompt_eval_duration": 1770702000,
#     "eval_count": 96,
#     "eval_duration": 11328594000,
#     "message": {
#         "role": "assistant",
#         "content": "",
#         "thinking": null,
#         "images": null,
#         "tool_name": null,
#         "tool_calls": null
#     },
#     "logprobs": null
# }

###break loop agent

# {
#     "model": "qwen3.5:4b",
#     "created_at": "2026-08-16T12:43:43.5624893Z",
#     "done": false,
#     "done_reason": null,
#     "total_duration": null,
#     "load_duration": null,
#     "prompt_eval_count": null,
#     "prompt_eval_duration": null,
#     "eval_count": null,
#     "eval_duration": null,
#     "message": {
#         "role": "assistant",
#         "content": " cerah",
#         "thinking": null,
#         "images": null,
#         "tool_name": null,
#         "tool_calls": null
#     },
#     "logprobs": null
# }
# {
#     "model": "qwen3.5:4b",
#     "created_at": "2026-08-16T12:43:43.8135096Z",
#     "done": true,
#     "done_reason": "stop",
#     "total_duration": 25163167300,
#     "load_duration": 675286300,
#     "prompt_eval_count": 820,
#     "prompt_eval_duration": 1912404000,
#     "eval_count": 185,
#     "eval_duration": 22558260000,
#     "message": {
#         "role": "assistant",
#         "content": "",
#         "thinking": null,
#         "images": null,
#         "tool_name": null,
#         "tool_calls": null
#     },
#     "logprobs": null
# }

###complte message

# [
#     {
#         "role": "system",
#         "content": "\n            You are Kwanza AI, developed by Arsal Fahrulloh.\n            You can answer general questions normally.\n            Use tools only when you need:\n            - get_city\n            - get_weather\n            Do not use tools for general knowledge, casual conversation, or conceptual explanations.\n            Always use tool results when user asks for personal or city name available in the database.\n        "
#     },
#     {
#         "role": "user",
#         "content": "Tolong berikan semua data nama kota yang ada didatabase, dan juga berikan data cuaca-nya dari setiap masing masing kota yang ada didatabase"
#     },
#     {
#         "role": "assistant",
#         "thinking": "The user is asking me to provide all city names from the database and their weather information for each of those cities. This requires using two tools:\n\n1. First, I need to get all available cities in the database using `get_city`\n2. Then, for each city returned, I need to get the weather information using `get_weather` with that specific city name\n\nLet me start by getting the list of cities first, then I can make multiple calls to get weather for each one.",
#         "content": "",
#         "tool_calls": [
#             {
#                 "function": {
#                     "name": "get_city",
#                     "arguments": {}
#                 }
#             }
#         ]
#     },
#     {
#         "role": "tool",
#         "tool_name": "get_city",
#         "content": "[{\"name\": \"Bandung\", \"province\": \"Jawa Barat\"}, {\"name\": \"Jakarta\", \"province\": \"DKI Jakarta\"}]"
#     },
#     {
#         "role": "assistant",
#         "thinking": "Great, I got the list of cities in the database. There are two cities: Bandung and Jakarta. Now I need to get weather information for each of these cities using `get_weather`.",
#         "content": "",
#         "tool_calls": [
#             {
#                 "function": {
#                     "name": "get_weather",
#                     "arguments": {
#                         "city_name": "Bandung"
#                     }
#                 }
#             },
#             {
#                 "function": {
#                     "name": "get_weather",
#                     "arguments": {
#                         "city_name": "Jakarta"
#                     }
#                 }
#             }
#         ]
#     },
#     {
#         "role": "tool",
#         "tool_name": "get_weather",
#         "content": "{\"temperature\": 24, \"condition\": \"Hujan\"}"
#     },
#     {
#         "role": "tool",
#         "tool_name": "get_weather",
#         "content": "{\"temperature\": 32, \"condition\": \"Cerah\"}"
#     },
#     {
#         "role": "assistant",
#         "thinking": "Now I have all the information needed. Let me provide a comprehensive summary of both cities from their database names and weather data for each city.\n\nThe user asked in Indonesian (\"Tolong berikan...\") so I should respond in Indonesian as well.",
#         "content": "Berikut adalah semua data nama kota yang ada di database beserta cuacanya:\n\n### 📍 Data Kota & Cuaca di Database\n\n| Nama Kota | Provinsi | Suhu (°C) | Kondisi Cuaca |\n|-----------|----------|-----------|---------------|\n| Bandung   | Jawa Barat  | 24        | Hujan           |\n| Jakarta   | DKI Jakarta  | 32        | Cerah            |\n\n**Ringkasan:**\n- **Bandung**: Suhu 24°C, Cuaca sedang hujan.\n- **Jakarta**: Suhu 32°C, Cuaca cerah.",
#         "tool_calls": []
#     },
#     {
#         "role": "assistant",
#         "thinking": "Now I have all the information needed. Let me provide a comprehensive summary of both cities from their database names and weather data for each city.\n\nThe user asked in Indonesian (\"Tolong berikan...\") so I should respond in Indonesian as well.",
#         "content": "Berikut adalah semua data nama kota yang ada di database beserta cuacanya:\n\n### 📍 Data Kota & Cuaca di Database\n\n| Nama Kota | Provinsi | Suhu (°C) | Kondisi Cuaca |\n|-----------|----------|-----------|---------------|\n| Bandung   | Jawa Barat  | 24        | Hujan           |\n| Jakarta   | DKI Jakarta  | 32        | Cerah            |\n\n**Ringkasan:**\n- **Bandung**: Suhu 24°C, Cuaca sedang hujan.\n- **Jakarta**: Suhu 32°C, Cuaca cerah."
#     }
# ]