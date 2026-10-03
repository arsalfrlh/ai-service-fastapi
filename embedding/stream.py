from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse

from transformers import (
    AutoProcessor,
    AutoModelForMultimodalLM,
    TextIteratorStreamer,
)

from threading import Thread
from pydantic import BaseModel

import torch
import json
import re


# ==========================================================
# CONFIG
# ==========================================================

MODEL_PATH = r"E:\model\llm\Qwen3.5-0.8B"

# Maksimal jumlah agent step.
#
# Untuk contoh:
#
# STEP 1 -> get_cities
# STEP 2 -> get_weather
# STEP 3 -> final answer
#
MAX_AGENT_STEPS = 10

# Generation agent.
AGENT_MAX_NEW_TOKENS = 256

# Generation final answer.
FINAL_MAX_NEW_TOKENS = 256

# Thinking hanya digunakan pada agent/tool steps.
THINKING_ENABLED = True

# Sampling untuk Qwen3.5 thinking.
TEMPERATURE = 1.0
TOP_P = 0.95
TOP_K = 20


# ==========================================================
# FASTAPI
# ==========================================================

app = FastAPI()


@app.exception_handler(RequestValidationError)
def request_validation(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content={
            "message": exc.errors(),
            "success": False,
        },
    )


# ==========================================================
# MODEL
# ==========================================================

print("===================================")
print("Loading model...")
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

    print("[TOOL] get_cities()")

    return CITIES


# ==========================================================
# TOOL 2
# ==========================================================

def get_weather(city: str) -> dict:
    """
    Get current weather information for a city.

    Args:
        city:
            Name of the city.

    Returns:
        Weather information.
    """

    print(
        f"[TOOL] get_weather(city={city})"
    )

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
# TEXT CLEANING
# ==========================================================

def clean_control_tokens(text: str) -> str:
    """
    Remove model control tokens that should never
    be visible in the final answer.
    """

    text = text.replace(
        "<|im_end|>",
        "",
    )

    text = text.replace(
        "<|endoftext|>",
        "",
    )

    return text.strip()


# ==========================================================
# PARSE TOOL CALLS
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

    tool_calls = []

    pattern = re.compile(
        r"<tool_call>\s*"
        r"<function=(.*?)>\s*"
        r"(.*?)"
        r"</function>\s*"
        r"</tool_call>",
        re.DOTALL,
    )

    matches = pattern.findall(text)

    for function_name, body in matches:

        function_name = function_name.strip()

        arguments = {}

        parameter_pattern = re.compile(
            r"<parameter=(.*?)>\s*"
            r"(.*?)"
            r"\s*</parameter>",
            re.DOTALL,
        )

        parameters = parameter_pattern.findall(
            body
        )

        for parameter_name, parameter_value in parameters:

            parameter_name = parameter_name.strip()

            parameter_value = parameter_value.strip()

            # Try to decode JSON.
            #
            # Example:
            #
            # ["Bandung", "Jakarta"]
            # 123
            # true
            #
            # If it is not JSON, keep it as string.
            try:
                parameter_value = json.loads(
                    parameter_value
                )

            except json.JSONDecodeError:
                pass

            arguments[
                parameter_name
            ] = parameter_value

        tool_calls.append(
            {
                "name": function_name,
                "arguments": arguments,
            }
        )

    return tool_calls


# ==========================================================
# EXECUTE TOOL
# ==========================================================

def execute_tool(
    tool_name: str,
    arguments: dict,
):
    """
    Execute a registered tool.
    """

    print()
    print("-----------------------------------")
    print("Executing tool")
    print("Tool:", tool_name)
    print("Arguments:", arguments)
    print("-----------------------------------")

    tool = TOOL_MAP.get(
        tool_name
    )

    if tool is None:

        return {
            "success": False,
            "error": (
                f"Unknown tool: {tool_name}"
            ),
        }

    try:

        result = tool(
            **arguments
        )

        return result

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# ==========================================================
# CUT AFTER FIRST COMPLETE TOOL CALL
# ==========================================================

def cut_after_tool_call(
    text: str,
) -> str:
    """
    Stop generation logically after the first complete
    tool-call block.

    This prevents the model from continuing and inventing:

        <tool_response>
        user
        another tool call
        etc.
    """

    marker = "</tool_call>"

    position = text.find(
        marker
    )

    if position == -1:

        return text

    return text[
        : position + len(marker)
    ]


# ==========================================================
# LLM STREAM
# ==========================================================

def stream_model(
    messages,
    use_tools: bool,
    enable_thinking: bool,
    max_new_tokens: int,
):
    """
    Run one model generation.

    use_tools=True:
        Agent/tool generation.

    use_tools=False:
        Final answer generation.
    """

    # ------------------------------------------------------
    # TEMPLATE ARGUMENTS
    # ------------------------------------------------------

    template_kwargs = {
        "add_generation_prompt": True,

        "tokenize": True,

        "return_dict": True,

        "return_tensors": "pt",

        "enable_thinking": enable_thinking,
    }

    # Only provide tools during agent generation.
    if use_tools:

        template_kwargs[
            "tools"
        ] = TOOLS


    # ------------------------------------------------------
    # APPLY CHAT TEMPLATE
    # ------------------------------------------------------

    inputs = processor.apply_chat_template(
        messages,
        **template_kwargs,
    )

    inputs = inputs.to(
        model.device
    )


    # ------------------------------------------------------
    # STREAMER
    # ------------------------------------------------------

    streamer = TextIteratorStreamer(
        processor.tokenizer,

        skip_prompt=True,

        # We need the generated tool markup,
        # but we remove special control tokens later.
        skip_special_tokens=False,
    )


    # ------------------------------------------------------
    # GENERATION
    # ------------------------------------------------------

    generation_kwargs = {
        **inputs,

        "streamer": streamer,

        "max_new_tokens": max_new_tokens,

        "do_sample": True,

        "temperature": TEMPERATURE,

        "top_p": TOP_P,

        "top_k": TOP_K,
    }


    # ------------------------------------------------------
    # THREAD
    # ------------------------------------------------------

    thread = Thread(
        target=model.generate,
        kwargs=generation_kwargs,
    )

    thread.start()


    # ------------------------------------------------------
    # STREAM
    # ------------------------------------------------------

    full_text = ""

    for token in streamer:

        full_text += token

        yield token


    # ------------------------------------------------------
    # WAIT FOR MODEL
    # ------------------------------------------------------

    thread.join()


# ==========================================================
# SYSTEM PROMPT
# ==========================================================

SYSTEM_PROMPT = """
You are Kwanza AI developed by Arsal Fahrulloh.

You are an AI agent with access to tools.

IMPORTANT RULES:

1. Never invent data.

2. Never invent database information.

3. Never invent weather information.

4. If the user asks for city data from the database,
   call get_cities.

5. If weather is requested for database cities,
   first obtain the city list.

6. After receiving the city list,
   call get_weather for every required city.

7. Use only values returned by tools.

8. Do not generate fake tool responses.

9. Do not generate <tool_response>.
   The application will provide tool responses.

10. Do not generate a "user" message.

11. When you need a tool, generate the tool call
    and stop.

12. When all required information has been collected,
    answer the user.

13. Never call the same tool unnecessarily.
"""


# ==========================================================
# DEBUG
# ==========================================================

def print_messages(
    messages,
):
    """
    Print current conversation state.
    """

    print()
    print(
        "==================================="
    )
    print(
        "CURRENT CONVERSATION"
    )
    print(
        "==================================="
    )

    for index, message in enumerate(
        messages
    ):

        print(
            f"\nMESSAGE {index}"
        )

        print(
            "ROLE:",
            message.get(
                "role"
            ),
        )

        content = message.get(
            "content"
        )

        if content:

            print(
                "CONTENT:",
                content,
            )

        reasoning = message.get(
            "reasoning_content"
        )

        if reasoning:

            print(
                "REASONING:",
                reasoning,
            )

        tool_calls = message.get(
            "tool_calls"
        )

        if tool_calls:

            print(
                "TOOL CALLS:",
                tool_calls,
            )


# ==========================================================
# AGENT
# ==========================================================

def generate_chat(
    message: str,
):

    # ======================================================
    # AGENT STATE
    # ======================================================

    cities_loaded = False

    cities = []

    weather_loaded = set()

    requested_weather = (
        "weather" in message.lower()
        or "cuaca" in message.lower()
    )


    # ======================================================
    # INITIAL MESSAGES
    # ======================================================

    messages = [

        # --------------------------------------------------
        # SYSTEM
        # --------------------------------------------------

        {
            "role": "system",

            "content": [
                {
                    "type": "text",

                    "text": SYSTEM_PROMPT,
                }
            ],
        },

        # --------------------------------------------------
        # USER
        # --------------------------------------------------

        {
            "role": "user",

            "content": [
                {
                    "type": "text",

                    "text": message,
                }
            ],
        },
    ]


    # ======================================================
    # AGENT LOOP
    # ======================================================

    for step in range(
        MAX_AGENT_STEPS
    ):

        print()
        print(
            "==================================="
        )

        print(
            f"AGENT STEP {step + 1}"
        )

        print(
            "==================================="
        )


        # --------------------------------------------------
        # DEBUG
        # --------------------------------------------------

        print_messages(
            messages
        )


        # ==================================================
        # DETERMINE STATE
        # ==================================================

        all_weather_loaded = (
            requested_weather
            and cities_loaded
            and bool(cities)
            and set(cities).issubset(
                weather_loaded
            )
        )


        # --------------------------------------------------
        # If all required weather data exists,
        # move immediately to final mode.
        # --------------------------------------------------

        if all_weather_loaded:

            print()
            print(
                "All required data collected."
            )

            print(
                "Switching to FINAL MODE."
            )

            # ----------------------------------------------
            # Add explicit final instruction.
            # ----------------------------------------------

            messages.append(
                {
                    "role": "user",

                    "content": [
                        {
                            "type": "text",

                            "text": """
All required tool data has been collected.

Now answer the user's original request.

Do not call any tools.

Do not invent information.

Use only the tool results already present
in the conversation.

Return only the final answer.
""",
                        }
                    ],
                }
            )


            # ----------------------------------------------
            # FINAL GENERATION
            #
            # IMPORTANT:
            #
            # Thinking disabled.
            # Tools disabled.
            # ----------------------------------------------

            final_response = ""

            for token in stream_model(
                messages,

                use_tools=False,

                enable_thinking=False,

                max_new_tokens=FINAL_MAX_NEW_TOKENS,
            ):

                final_response += token


            # ----------------------------------------------
            # CLEAN FINAL
            # ----------------------------------------------

            final_response = clean_control_tokens(
                final_response
            )

            final_response = re.sub(
                r"<think>.*?</think>",
                "",
                final_response,
                flags=re.DOTALL,
            ).strip()


            final_response = re.sub(
                r"<tool_call>.*?</tool_call>",
                "",
                final_response,
                flags=re.DOTALL,
            ).strip()


            # ----------------------------------------------
            # SEND FINAL ANSWER
            # ----------------------------------------------

            yield json.dumps(
                {
                    "done": False,

                    "type": "message",

                    "message": {
                        "role": "assistant",

                        "content": final_response,
                    },
                },

                ensure_ascii=False,
            ) + "\n"


            # ----------------------------------------------
            # DONE
            # ----------------------------------------------

            yield json.dumps(
                {
                    "done": True,

                    "type": "done",

                    "message": {
                        "role": "assistant",

                        "content": final_response,
                    },
                },

                ensure_ascii=False,
            ) + "\n"


            return


        # ==================================================
        # AGENT GENERATION
        # ==================================================

        full_response = ""

        for token in stream_model(
            messages,

            use_tools=True,

            enable_thinking=THINKING_ENABLED,

            max_new_tokens=AGENT_MAX_NEW_TOKENS,
        ):

            full_response += token


        # ==================================================
        # STOP AT TOOL CALL
        # ==================================================

        full_response = cut_after_tool_call(
            full_response
        )


        # ==================================================
        # CLEAN CONTROL TOKENS
        # ==================================================

        full_response = clean_control_tokens(
            full_response
        )


        # ==================================================
        # DEBUG
        # ==================================================

        print()
        print(
            "==================================="
        )

        print(
            "RAW AGENT RESPONSE"
        )

        print(
            "==================================="
        )

        print(
            repr(full_response)
        )


        # ==================================================
        # PARSE TOOL CALL
        # ==================================================

        tool_calls = parse_tool_calls(
            full_response
        )


        print()
        print(
            "==================================="
        )

        print(
            "TOOL CALLS"
        )

        print(
            "==================================="
        )

        print(
            tool_calls
        )


        # ==================================================
        # NO TOOL CALL
        # ==================================================

        if not tool_calls:

            print()
            print(
                "No tool call detected."
            )


            # ------------------------------------------------
            # If no tool is needed, produce final answer
            # using the current response.
            #
            # Do not expose thinking markup.
            # ------------------------------------------------

            final_response = re.sub(
                r"<think>.*?</think>",
                "",
                full_response,
                flags=re.DOTALL,
            ).strip()


            final_response = clean_control_tokens(
                final_response
            )


            if not final_response:

                final_response = (
                    "Maaf, saya tidak dapat "
                    "menyelesaikan permintaan tersebut."
                )


            yield json.dumps(
                {
                    "done": False,

                    "type": "message",

                    "message": {
                        "role": "assistant",

                        "content": final_response,
                    },
                },

                ensure_ascii=False,
            ) + "\n"


            yield json.dumps(
                {
                    "done": True,

                    "type": "done",

                    "message": {
                        "role": "assistant",

                        "content": final_response,
                    },
                },

                ensure_ascii=False,
            ) + "\n"


            return


        # ==================================================
        # TOOL CALL DETECTED
        # ==================================================

        print()
        print(
            "==================================="
        )

        print(
            "TOOL CALL DETECTED"
        )

        print(
            "==================================="
        )


        # ==================================================
        # ASSISTANT TOOL MESSAGE
        # ==================================================

        assistant_message = {

            "role": "assistant",

            # Do NOT put raw <tool_call> markup
            # inside content.
            "content": "",

            "tool_calls": [

                {
                    "type": "function",

                    "function": {

                        "name": call[
                            "name"
                        ],

                        "arguments": call[
                            "arguments"
                        ],
                    },
                }

                for call in tool_calls
            ],
        }


        messages.append(
            assistant_message
        )


        # ==================================================
        # EXECUTE TOOL CALLS
        # ==================================================

        for call in tool_calls:

            tool_name = call[
                "name"
            ]

            arguments = call[
                "arguments"
            ]


            # ------------------------------------------------
            # DUPLICATE PROTECTION
            # ------------------------------------------------

            if (
                tool_name == "get_weather"
            ):

                city = arguments.get(
                    "city"
                )

                if city in weather_loaded:

                    print(
                        "Skipping duplicate weather:",
                        city,
                    )

                    continue


            # ------------------------------------------------
            # EXECUTE TOOL
            # ------------------------------------------------

            result = execute_tool(
                tool_name,

                arguments,
            )


            # =================================================
            # UPDATE AGENT STATE
            # =================================================

            if tool_name == "get_cities":

                cities_loaded = True

                if isinstance(
                    result,
                    list,
                ):

                    cities = result


            elif tool_name == "get_weather":

                city = arguments.get(
                    "city"
                )

                if city:

                    weather_loaded.add(
                        city
                    )


            # =================================================
            # SEND TOOL EVENT TO CLIENT
            # =================================================

            yield json.dumps(
                {
                    "done": False,

                    "type": "tool",

                    "tool": {

                        "name": tool_name,

                        "arguments": arguments,

                        "result": result,
                    },
                },

                ensure_ascii=False,
            ) + "\n"


            # =================================================
            # APPEND TOOL RESULT
            # =================================================

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


        # ==================================================
        # SHOW STATE
        # ==================================================

        all_weather_loaded = (
            requested_weather
            and cities_loaded
            and bool(cities)
            and set(cities).issubset(
                weather_loaded
            )
        )


        print()
        print(
            "==================================="
        )

        print(
            "AGENT STATE"
        )

        print(
            "==================================="
        )

        print(
            "cities_loaded:",
            cities_loaded,
        )

        print(
            "cities:",
            cities,
        )

        print(
            "weather_loaded:",
            weather_loaded,
        )

        print(
            "all_weather_loaded:",
            all_weather_loaded,
        )


        if all_weather_loaded:

            print()
            print(
                "All required data obtained."
            )

            print(
                "Next iteration will use FINAL MODE."
            )

        else:

            print(
                "Returning to agent..."
            )


    # ======================================================
    # MAX AGENT STEPS
    # ======================================================

    error_message = (
        "The agent reached the maximum "
        "number of iterations."
    )


    yield json.dumps(
        {
            "done": True,

            "type": "error",

            "message": {
                "role": "assistant",

                "content": error_message,
            },
        },

        ensure_ascii=False,
    ) + "\n"


# ==========================================================
# API
# ==========================================================

@app.post("/message")
def send_message(
    request: MessageRequest,
):

    return StreamingResponse(
        generate_chat(
            request.message
        ),
        media_type="application/x-ndjson",
    )