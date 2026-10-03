from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from transformers import (
    AutoProcessor,
    AutoModelForMultimodalLM,
)

import torch
import json
import re


# ==========================================================
# CONFIG
# ==========================================================

MODEL_PATH = r"E:\model\llm\Qwen3.5-0.8B"

MAX_AGENT_STEPS = 10
MAX_NEW_TOKENS = 256


# ==========================================================
# FASTAPI
# ==========================================================

app = FastAPI()


@app.exception_handler(RequestValidationError)
def request_validation(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "message": exc.errors(),
            "success": False,
        },
    )


# ==========================================================
# LOAD MODEL
# ==========================================================

print("===================================")
print("Loading Qwen3.5-0.8B")
print("===================================")

processor = AutoProcessor.from_pretrained(
    MODEL_PATH,
    local_files_only=True,
)

model = AutoModelForMultimodalLM.from_pretrained(
    MODEL_PATH,
    dtype=torch.float32,
    local_files_only=True,
)

model.eval()

print("Model loaded.")
print("Device:", model.device)


# ==========================================================
# DUMMY DATA
# ==========================================================
#
# NANTI INI BISA DIGANTI DATABASE
#
# get_cities()
#      ↓
# SELECT name FROM cities
#
# get_weather(city)
#      ↓
# request ke weather API
#
# ==========================================================

CITIES = [
    "Bandung",
    "Jakarta",
    "Surabaya",
    "Yogyakarta",
]


WEATHER_DATA = {
    "Bandung": {
        "temperature": 24,
        "condition": "Rainy",
        "humidity": 80,
    },
    "Jakarta": {
        "temperature": 31,
        "condition": "Sunny",
        "humidity": 65,
    },
    "Surabaya": {
        "temperature": 33,
        "condition": "Cloudy",
        "humidity": 70,
    },
    "Yogyakarta": {
        "temperature": 29,
        "condition": "Partly Cloudy",
        "humidity": 72,
    },
}


# ==========================================================
# TOOL 1
# ==========================================================

def get_cities() -> list[str]:
    """
    Get all city names from the database.

    Returns:
        A list of city names.
    """

    print("\n[TOOL] get_cities()")

    return CITIES


# ==========================================================
# TOOL 2
# ==========================================================

def get_weather(city: str) -> dict:
    """
    Get weather information for a city.

    Args:
        city: The city name.

    Returns:
        Weather information for the city.
    """

    print(f"\n[TOOL] get_weather(city={city})")

    weather = WEATHER_DATA.get(city)

    if weather is None:
        return {
            "success": False,
            "city": city,
            "message": "Weather data not found.",
        }

    return {
        "success": True,
        "city": city,
        **weather,
    }


# ==========================================================
# TOOL REGISTRY
# ==========================================================

TOOLS = [
    get_cities,
    get_weather,
]


TOOL_MAP = {
    "get_cities": get_cities,
    "get_weather": get_weather,
}


# ==========================================================
# REQUEST
# ==========================================================

class MessageRequest(BaseModel):
    message: str


# ==========================================================
# GENERATE MODEL
# ==========================================================

def generate_model(messages: list[dict]) -> str:

    inputs = processor.apply_chat_template(
        messages,
        tools=TOOLS,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        enable_thinking=False,
    )

    inputs = {
        key: value.to(model.device)
        for key, value in inputs.items()
        if hasattr(value, "to")
    }

    with torch.no_grad():

        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
        )

    input_length = inputs["input_ids"].shape[-1]

    generated_ids = outputs[0][input_length:]

    response = processor.tokenizer.decode(
        generated_ids,
        skip_special_tokens=True,
    )

    return response.strip()


# ==========================================================
# PARSE TOOL CALL
# ==========================================================

def parse_tool_calls(text: str) -> list[dict]:

    """
    Parse Qwen3.5 tool-call format.

    Example:

    <tool_call>
    <function=get_weather>
    <parameter=city>
    Bandung
    </parameter>
    </function>
    </tool_call>
    """

    results = []

    pattern = re.compile(
        r"<tool_call>\s*"
        r"<function=(.*?)>\s*"
        r"(.*?)"
        r"</function>\s*"
        r"</tool_call>",
        re.DOTALL,
    )

    matches = pattern.findall(text)

    for function_name, parameters_text in matches:

        function_name = function_name.strip()

        arguments = {}

        parameter_pattern = re.compile(
            r"<parameter=(.*?)>\s*(.*?)\s*</parameter>",
            re.DOTALL,
        )

        parameter_matches = parameter_pattern.findall(
            parameters_text
        )

        for parameter_name, parameter_value in parameter_matches:

            parameter_name = parameter_name.strip()
            parameter_value = parameter_value.strip()

            # coba decode JSON
            try:
                parameter_value = json.loads(
                    parameter_value
                )
            except json.JSONDecodeError:
                pass

            arguments[parameter_name] = parameter_value

        results.append(
            {
                "name": function_name,
                "arguments": arguments,
            }
        )

    return results


# ==========================================================
# EXECUTE TOOL
# ==========================================================

def execute_tool(tool_name: str, arguments: dict):

    print("\n-----------------------------------")
    print("Executing Tool")
    print("Name:", tool_name)
    print("Arguments:", arguments)
    print("-----------------------------------")

    tool = TOOL_MAP.get(tool_name)

    if tool is None:

        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
        }

    try:

        result = tool(**arguments)

        return result

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# ==========================================================
# AGENT LOOP
# ==========================================================

def run_agent(user_message: str):

    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": """
You are Kwanza AI developed by Arsal Fahrulloh.

You are an AI agent that can use tools.

Rules:

1. Use tools when the user asks for data that must
   come from external sources.
2. Do not invent database data.
3. If the user asks for cities, use get_cities.
4. If the user asks for weather, use get_weather.
5. You can call multiple tools when necessary.
6. Continue using tools until you have enough
   information to answer the user.
7. After all required tool calls are complete,
   return a clear final answer.
""",
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_message,
                }
            ],
        },
    ]

    # ======================================================
    # AGENT LOOP
    # ======================================================

    for step in range(MAX_AGENT_STEPS):

        print("\n")
        print("===================================")
        print(f"AGENT STEP {step + 1}")
        print("===================================")

        # ----------------------------------------------
        # CALL LLM
        # ----------------------------------------------

        model_response = generate_model(messages)

        print("\n[MODEL]")
        print(model_response)

        # ----------------------------------------------
        # PARSE TOOL CALL
        # ----------------------------------------------

        tool_calls = parse_tool_calls(model_response)

        # ----------------------------------------------
        # NO TOOL CALL
        #
        # berarti model sudah membuat final answer
        # ----------------------------------------------

        if not tool_calls:

            return model_response

        # ----------------------------------------------
        # SIMPAN ASSISTANT TOOL CALL
        # ----------------------------------------------

        assistant_tool_calls = []

        for tool_call in tool_calls:

            assistant_tool_calls.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool_call["name"],
                        "arguments": tool_call["arguments"],
                    },
                }
            )

        messages.append(
            {
                "role": "assistant",
                "content": model_response,
                "tool_calls": assistant_tool_calls,
            }
        )

        # ----------------------------------------------
        # EXECUTE TOOLS
        # ----------------------------------------------

        for tool_call in tool_calls:

            tool_name = tool_call["name"]

            arguments = tool_call["arguments"]

            result = execute_tool(
                tool_name,
                arguments,
            )

            # ------------------------------------------
            # MASUKKAN HASIL TOOL KE CONVERSATION
            # ------------------------------------------

            messages.append(
                {
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps(
                        result,
                        ensure_ascii=False,
                    ),
                }
            )

    # ======================================================
    # MAX ITERATION
    # ======================================================

    return (
        "Agent stopped because maximum tool "
        "iterations were reached."
    )


# ==========================================================
# API ENDPOINT
# ==========================================================

@app.post("/message")
def send_message(request: MessageRequest):

    response = run_agent(
        request.message
    )

    return {
        "success": True,
        "message": response,
    }