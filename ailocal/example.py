import json
import re
import torch

from threading import Thread

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from transformers import (
    AutoProcessor,
    AutoModelForMultimodalLM,
    TextIteratorStreamer,
)


# ============================================================
# CONFIG
# ============================================================

MODEL_PATH = r"C:\model\qwen"

MAX_AGENT_ITERATIONS = 5


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Qwen3.5 Local AI Agent",
    version="1.0.0",
)


# ============================================================
# LOAD PROCESSOR
# ============================================================

print("Loading processor...")

processor = AutoProcessor.from_pretrained(
    MODEL_PATH,
    local_files_only=True,
)


# ============================================================
# LOAD MODEL
# ============================================================

print("Loading model...")

model = AutoModelForMultimodalLM.from_pretrained(
    MODEL_PATH,
    dtype=torch.float32,
    local_files_only=True,
)

model.eval()

print()
print("====================================")
print("Qwen3.5 berhasil dimuat")
print("Device:", next(model.parameters()).device)
print("====================================")
print()


# ============================================================
# TOOLS
# ============================================================

CITIES = [
    "Bandung",
    "Jakarta",
    "Surabaya",
    "Yogyakarta",
    "Semarang",
    "Malang",
    "Depok",
    "Bogor",
    "Bekasi",
    "Tangerang",
]


WEATHER = {
    "bandung": {
        "temperature": 24,
        "condition": "Hujan",
        "humidity": 85,
    },
    "jakarta": {
        "temperature": 31,
        "condition": "Cerah",
        "humidity": 70,
    },
    "surabaya": {
        "temperature": 33,
        "condition": "Panas",
        "humidity": 65,
    },
    "yogyakarta": {
        "temperature": 28,
        "condition": "Berawan",
        "humidity": 75,
    },
    "semarang": {
        "temperature": 30,
        "condition": "Cerah",
        "humidity": 72,
    },
    "malang": {
        "temperature": 22,
        "condition": "Hujan",
        "humidity": 88,
    },
    "depok": {
        "temperature": 30,
        "condition": "Hujan",
        "humidity": 82,
    },
    "bogor": {
        "temperature": 23,
        "condition": "Hujan",
        "humidity": 90,
    },
    "bekasi": {
        "temperature": 31,
        "condition": "Berawan",
        "humidity": 76,
    },
    "tangerang": {
        "temperature": 31,
        "condition": "Cerah",
        "humidity": 69,
    },
}


def get_cities():
    """
    Get all available city names.

    Returns:
        List of available city names.
    """

    return {
        "cities": CITIES
    }


def get_weather(city: str):
    """
    Get weather information for a city.

    Args:
        city: Name of the city.
    """

    normalized_city = city.strip().lower()

    weather = WEATHER.get(normalized_city)

    if weather is None:
        return {
            "error": f"Weather untuk kota '{city}' tidak tersedia.",
            "available_cities": CITIES,
        }

    return {
        "city": city,
        **weather,
    }


# ============================================================
# TOOL REGISTRY
# ============================================================

TOOLS = [
    get_cities,
    get_weather,
]


# ============================================================
# TOOL EXECUTOR
# ============================================================

def execute_tool(
    tool_name: str,
    arguments: dict,
):
    """
    Menjalankan function Python berdasarkan
    nama tool yang diberikan oleh model.
    """

    if tool_name == "get_cities":
        return get_cities()

    if tool_name == "get_weather":
        return get_weather(
            city=arguments.get("city", "")
        )

    return {
        "error": f"Tool '{tool_name}' tidak ditemukan."
    }


# ============================================================
# PARSE QWEN TOOL CALL
# ============================================================

def parse_tool_calls(text: str):
    """
    Parse format tool call Qwen3.5:

    <tool_call>
    <function=get_weather>
    <parameter=city>
    Bandung
    </parameter>
    </function>
    </tool_call>
    """

    tool_calls = []

    function_pattern = re.compile(
        r"<tool_call>\s*"
        r"<function=([^>]+)>\s*"
        r"(.*?)"
        r"</function>\s*"
        r"</tool_call>",
        re.DOTALL,
    )

    matches = function_pattern.finditer(text)

    for match in matches:

        function_name = match.group(1).strip()
        function_body = match.group(2)

        arguments = {}

        parameter_pattern = re.compile(
            r"<parameter=([^>]+)>\s*"
            r"(.*?)"
            r"\s*</parameter>",
            re.DOTALL,
        )

        parameters = parameter_pattern.finditer(
            function_body
        )

        for parameter in parameters:

            parameter_name = parameter.group(1).strip()
            parameter_value = parameter.group(2).strip()

            arguments[parameter_name] = parameter_value

        tool_calls.append(
            {
                "name": function_name,
                "arguments": arguments,
            }
        )

    return tool_calls


# ============================================================
# CREATE INPUTS
# ============================================================

def create_inputs(messages):
    """
    Convert messages + tools menjadi input tensor.
    """

    inputs = processor.apply_chat_template(
        messages,
        tools=TOOLS,

        add_generation_prompt=True,

        tokenize=True,

        return_dict=True,

        return_tensors="pt",

        enable_thinking=False,
    )

    inputs = inputs.to(model.device)

    return inputs


# ============================================================
# GENERATE NORMAL
# ============================================================

def generate_response(
    messages,
    max_new_tokens=256,
):
    """
    Generate response tanpa streaming.
    """

    inputs = create_inputs(
        messages
    )

    with torch.no_grad():

        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )

    input_length = inputs[
        "input_ids"
    ].shape[-1]

    generated_tokens = outputs[
        0,
        input_length:
    ]

    response = processor.decode(
        generated_tokens,
        skip_special_tokens=True,
    )

    return response


# ============================================================
# RUN AGENT
# ============================================================

def run_agent(
    user_message: str,
    max_new_tokens: int = 256,
):
    """
    Agent loop:

    User
      ↓
    Qwen
      ↓
    Tool call?
      ↓
    Execute tool
      ↓
    Tool result
      ↓
    Qwen
      ↓
    Final answer
    """

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_message,
                }
            ],
        }
    ]

    tool_history = []

    for iteration in range(
        MAX_AGENT_ITERATIONS
    ):

        print(
            f"\nAgent iteration: {iteration + 1}"
        )

        response = generate_response(
            messages,
            max_new_tokens=max_new_tokens,
        )

        print(
            "\nMODEL RESPONSE:"
        )
        print(response)

        tool_calls = parse_tool_calls(
            response
        )

        # ====================================================
        # Tidak ada tool call
        # ====================================================

        if not tool_calls:

            return {
                "response": response,
                "tools_used": tool_history,
            }

        # ====================================================
        # Model meminta tool
        # ====================================================

        print(
            "\nTOOL CALLS:"
        )

        assistant_tool_calls = []

        for tool_call in tool_calls:

            tool_name = tool_call[
                "name"
            ]

            arguments = tool_call[
                "arguments"
            ]

            print(
                "Tool:",
                tool_name,
            )

            print(
                "Arguments:",
                arguments,
            )

            assistant_tool_calls.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": arguments,
                    },
                }
            )

        # ====================================================
        # Simpan assistant tool calls
        # ====================================================

        messages.append(
            {
                "role": "assistant",
                "content": response,
                "tool_calls": assistant_tool_calls,
            }
        )

        # ====================================================
        # Execute semua tools
        # ====================================================

        for tool_call in tool_calls:

            tool_name = tool_call[
                "name"
            ]

            arguments = tool_call[
                "arguments"
            ]

            result = execute_tool(
                tool_name,
                arguments,
            )

            print(
                "Tool Result:",
                result,
            )

            tool_history.append(
                {
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": result,
                }
            )

            # =================================================
            # Masukkan result ke conversation
            # =================================================

            messages.append(
                {
                    "role": "tool",
                    "content": json.dumps(
                        result,
                        ensure_ascii=False,
                    ),
                }
            )

    # ========================================================
    # Agent timeout
    # ========================================================

    return {
        "response": (
            "Agent mencapai batas maksimum "
            "iterasi."
        ),
        "tools_used": tool_history,
    }


# ============================================================
# REQUEST
# ============================================================

class AgentRequest(BaseModel):

    message: str

    max_new_tokens: int = 256


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok",

        "model": "Qwen3.5-0.8B",

        "device": str(
            next(model.parameters()).device
        ),

        "cuda": torch.cuda.is_available(),
    }


# ============================================================
# AGENT NORMAL
# ============================================================

@app.post("/agent")
def agent(
    request: AgentRequest,
):

    result = run_agent(
        user_message=request.message,
        max_new_tokens=request.max_new_tokens,
    )

    return result


# ============================================================
# AGENT STREAM
# ============================================================

@app.post("/agent/stream")
def agent_stream(
    request: AgentRequest,
):


        # ================================================
        # Jalankan agent sampai mendapatkan final response
        # ================================================

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": request.message,
                    }
                ],
            }
        ]

        for iteration in range(
            MAX_AGENT_ITERATIONS
        ):

            response = generate_response(
                messages,
                max_new_tokens=request.max_new_tokens,
            )

            tool_calls = parse_tool_calls(
                response
            )

            # =========================================
            # Tidak ada tool
            # berarti ini final response
            # =========================================

            if not tool_calls:

                # Untuk streaming final response
                streamer = TextIteratorStreamer(
                    processor.tokenizer,
                    skip_prompt=True,
                    skip_special_tokens=True,
                )

                inputs = create_inputs(
                    messages
                )

                generation_kwargs = {
                    **inputs,
                    "streamer": streamer,
                    "max_new_tokens": request.max_new_tokens,
                    "do_sample": False,
                }

                thread = Thread(
                    target=model.generate,
                    kwargs=generation_kwargs,
                )

                thread.start()

                for text in streamer:

                    yield text

                thread.join()

                return

            # =========================================
            # Ada tool call
            # =========================================

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
                    "content": response,
                    "tool_calls": assistant_tool_calls,
                }
            )

            # =========================================
            # Jalankan tools
            # =========================================

            for tool_call in tool_calls:

                result = execute_tool(
                    tool_call["name"],
                    tool_call["arguments"],
                )

                messages.append(
                    {
                        "role": "tool",
                        "content": json.dumps(
                            result,
                            ensure_ascii=False,
                        ),
                    }
                )

        yield (
            "Agent mencapai batas maksimum iterasi."
        )