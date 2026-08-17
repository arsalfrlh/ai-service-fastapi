from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from ollama import chat
from pydantic import BaseModel
import json

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validator_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": exc.errors()
        }
    )

class MessageRequest(BaseModel):
    message: str

@app.post("/message")
def send_message(request: MessageRequest):
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

    while True:
        response = chat(
            model="qwen3.5:4b",
            messages=messages,
            stream=False,
            tools=tools()
        )

        messages.append({
            "role": "assistant",
            "thinking": response.message.thinking,
            "content": response.message.content,
            "tool_calls": response.message.tool_calls
        })

        if response.message.tool_calls:
            for tool in response.message.tool_calls:
                tool_name = tool.function.name
                tool_argument = tool.function.arguments or {}

                result = exec_tool(tool_name, tool_argument)
                messages.append({
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": json.dumps(result)
                })

        else:
            break

    return messages

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
#         "thinking": "The user is asking me to provide all city names from the database and their weather information for each city. This requires using tools:\n\n1. First I need to use get_city to get all available cities in the database\n2. Then for each city, I need to use get_weather to get the weather information\n\nLet me start by getting the list of cities first.",
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
#         "thinking": "Good, I got the list of cities in the database. There are 2 cities:\n1. Bandung (province: Jawa Barat)\n2. Jakarta (province: DKI Jakarta)\n\nNow I need to get weather information for both cities using get_weather function.",
#         "content": "",
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
#     {
#         "role": "tool",
#         "tool_name": "get_weather",
#         "content": "{\"temperature\": 24, \"condition\": \"Hujan\"}"
#     },
#     {
#         "role": "assistant",
#         "thinking": "Got weather for Bandung. Now let me get the weather for Jakarta.",
#         "content": "",
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
#     {
#         "role": "tool",
#         "tool_name": "get_weather",
#         "content": "{\"temperature\": 32, \"condition\": \"Cerah\"}"
#     },
#     {
#         "role": "assistant",
#         "thinking": "Perfect! Now I have all the data. Let me present it in a clear format for the user:\n\n- Bandung (Jawa Barat): Temperature 24°C, Rainy\n- Jakarta (DKI Jakarta): Temperature 32°C, Clear\n\nLet me provide this information to the user with their requested format.",
#         "content": "Berikut adalah data lengkap nama kota dan cuaca untuk setiap kota yang ada dalam database:\n\n**Bandung** - Jawa Barat 🌧️  \nSuhu: 24°C | Ketinggian Cuaca: Hujan  \n\n**Jakarta** - DKI Jakarta ☀️  \nSuhu: 32°C | Kondisi Cuaca: Cerah",
#         "tool_calls": null
#     }
# ]