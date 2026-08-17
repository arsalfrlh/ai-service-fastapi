from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from ollama import chat
from pydantic import BaseModel
import json

import ast
import math
import statistics
from decimal import Decimal, ROUND_HALF_UP

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

class SafeCalculator:
    ALLOWED_FUNCTIONS = {
        # Basic
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,

        # Math
        "sqrt": math.sqrt,
        "cbrt": lambda x: x ** (1 / 3),
        "root": lambda x, n: x ** (1 / n),
        "pow": pow,
        "exp": math.exp,
        "ln": math.log,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "floor": math.floor,
        "ceil": math.ceil,

        # Trigonometry - radians
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,

        # Angle conversion
        "radians": math.radians,
        "degrees": math.degrees,

        # Trigonometry - degrees
        "sin_deg": lambda x: math.sin(math.radians(x)),
        "cos_deg": lambda x: math.cos(math.radians(x)),
        "tan_deg": lambda x: math.tan(math.radians(x)),

        # Statistics
        "mean": statistics.mean,
        "median": statistics.median,
        "variance": statistics.variance,
        "stdev": statistics.stdev,

        # Combinatorics
        "factorial": math.factorial,
        "combinations": math.comb,
        "permutations": math.perm,

        # Number theory
        "gcd": math.gcd,
        "lcm": math.lcm,

        # Finance / percentage
        "percent": lambda x: x / 100,
        "percent_of": lambda percent, value: (percent / 100) * value,

        "percentage_change":
            lambda old, new: ((new - old) / old) * 100,

        "discount":
            lambda price, percent: price - ((percent / 100) * price),

        "tax":
            lambda price, percent: price + ((percent / 100) * price),

        "tip":
            lambda bill, percent: bill + ((percent / 100) * bill),

        "simple_interest":
            lambda principal, rate, years:
                principal * (rate / 100) * years,

        "simple_interest_total":
            lambda principal, rate, years:
                principal + (principal * (rate / 100) * years),

        "compound_interest":
            lambda principal, rate, years:
                principal * ((1 + rate / 100) ** years),

        "compound_interest_only":
            lambda principal, rate, years:
                principal * ((1 + rate / 100) ** years) - principal,

        "cagr":
            lambda beginning, ending, years:
                ((ending / beginning) ** (1 / years) - 1) * 100,

        "loan_payment":
            lambda principal, annual_rate, years:
                (
                    principal
                    * (
                        (annual_rate / 100 / 12)
                        * (
                            1 + annual_rate / 100 / 12
                        ) ** (years * 12)
                    )
                    /
                    (
                        (
                            1 + annual_rate / 100 / 12
                        ) ** (years * 12)
                        - 1
                    )
                ),
    }

    CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
        "inf": math.inf,
    }

    ALLOWED_BIN_OPS = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
        ast.FloorDiv: lambda a, b: a // b,
        ast.Mod: lambda a, b: a % b,
        ast.Pow: lambda a, b: a ** b,
    }

    ALLOWED_UNARY_OPS = {
        ast.UAdd: lambda a: +a,
        ast.USub: lambda a: -a,
    }

    def calculate(self, expression: str):
        expression = expression.strip()

        if not expression:
            raise ValueError("Expression cannot be empty.")

        if len(expression) > 500:
            raise ValueError("Expression is too long.")

        try:
            tree = ast.parse(expression, mode="eval")

            result = self._evaluate(tree.body)

            if isinstance(result, float):
                if math.isnan(result):
                    raise ValueError("Result is NaN.")

                if math.isinf(result):
                    raise ValueError("Result is infinite.")

                # Avoid ugly floating point artifacts
                result = round(result, 12)

            return {
                "success": True,
                "expression": expression,
                "result": result
            }

        except ZeroDivisionError:
            return {
                "success": False,
                "expression": expression,
                "error": "Division by zero."
            }

        except (ValueError, TypeError, OverflowError) as e:
            return {
                "success": False,
                "expression": expression,
                "error": str(e)
            }

        except Exception as e:
            return {
                "success": False,
                "expression": expression,
                "error": f"Invalid expression: {str(e)}"
            }

    def _evaluate(self, node):

        # Number
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value

            if isinstance(node.value, list):
                return node.value

            raise ValueError("Unsupported constant.")

        # List
        if isinstance(node, ast.List):
            return [
                self._evaluate(element)
                for element in node.elts
            ]

        # Binary operation
        if isinstance(node, ast.BinOp):
            operator_type = type(node.op)

            if operator_type not in self.ALLOWED_BIN_OPS:
                raise ValueError(
                    f"Operator {operator_type.__name__} is not allowed."
                )

            left = self._evaluate(node.left)
            right = self._evaluate(node.right)

            # Protect against extremely huge powers
            if operator_type is ast.Pow:
                if abs(right) > 1000:
                    raise ValueError(
                        "Exponent is too large."
                    )

            return self.ALLOWED_BIN_OPS[operator_type](
                left,
                right
            )

        # Unary
        if isinstance(node, ast.UnaryOp):
            operator_type = type(node.op)

            if operator_type not in self.ALLOWED_UNARY_OPS:
                raise ValueError(
                    f"Unary operator {operator_type.__name__} is not allowed."
                )

            operand = self._evaluate(node.operand)

            return self.ALLOWED_UNARY_OPS[operator_type](
                operand
            )

        # Function call
        if isinstance(node, ast.Call):

            if not isinstance(node.func, ast.Name):
                raise ValueError(
                    "Only direct function calls are allowed."
                )

            function_name = node.func.id

            if function_name not in self.ALLOWED_FUNCTIONS:
                raise ValueError(
                    f"Function '{function_name}' is not allowed."
                )

            function = self.ALLOWED_FUNCTIONS[function_name]

            args = [
                self._evaluate(arg)
                for arg in node.args
            ]

            # keyword arguments are intentionally disabled
            if node.keywords:
                raise ValueError(
                    "Keyword arguments are not supported."
                )

            return function(*args)

        # Variable/constants
        if isinstance(node, ast.Name):

            if node.id in self.CONSTANTS:
                return self.CONSTANTS[node.id]

            raise ValueError(
                f"Unknown variable '{node.id}'."
            )

        raise ValueError(
            f"Unsupported expression: {type(node).__name__}"
        )
    
calculator = SafeCalculator()

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

            Available tools:
            - get_city
            - get_weather
            - calculator

            Tool rules:

            1. get_city
            Use this tool when you need to know whether a city exists in the database.
            Never assume a city exists.

            2. get_weather
            Use this tool when the user asks for weather information.
            The city name must come from get_city.
            Never invent city names or weather information.

            3. calculator
            Use this tool whenever the user asks for:
            - arithmetic calculations
            - percentages
            - discounts
            - taxes
            - tips
            - averages
            - statistics
            - powers
            - roots
            - logarithms
            - trigonometry
            - factorial
            - combinations
            - permutations
            - simple interest
            - compound interest
            - loan payments
            - percentage changes
            - CAGR
            - or any other numerical calculation

            IMPORTANT:
            - Do not perform complex calculations mentally when calculator can be used.
            - Always use calculator for numerical calculations.
            - Do not invent calculator results.
            - Use the calculator result in your final answer.
            - For ambiguous mathematical expressions, interpret them using standard mathematical precedence.
        """
    })

    messages.append({
        "role": "user",
        "content": request.message
    })

    tool_used = 0
    limit_use_tool = 10

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
            tool_used += 1
            if tool_used > limit_use_tool:
                break

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
        },
        # {
        #     "type": "function",
        #     "function": {
        #         "name": "calculator",
        #         "description": """
        #             A powerful and safe mathematical calculator.

        #             Use this tool for numerical calculations instead of doing
        #             complex arithmetic manually.

        #             Supported operations include:
        #             - addition, subtraction, multiplication, division
        #             - modulo
        #             - powers
        #             - square roots and nth roots
        #             - absolute values
        #             - rounding
        #             - floor and ceiling
        #             - percentages
        #             - percentage change
        #             - discounts
        #             - tax calculations
        #             - tips
        #             - simple interest
        #             - compound interest
        #             - loan payment calculations
        #             - CAGR
        #             - factorial
        #             - combinations
        #             - permutations
        #             - GCD and LCM
        #             - trigonometry
        #             - logarithms
        #             - exponentials
        #             - averages
        #             - median
        #             - variance
        #             - standard deviation
        #             - min and max

        #             Use standard mathematical precedence.

        #             Examples:
        #             2 + 5 * 3
        #             sqrt(144)
        #             15% can be represented with percent(15)
        #             percent_of(20, 500)
        #             percentage_change(100, 125)
        #             discount(100000, 20)
        #             tax(100000, 11)
        #             tip(50000, 10)
        #             simple_interest(1000000, 5, 2)
        #             compound_interest(1000000, 5, 2)
        #             loan_payment(100000000, 8, 15)
        #             factorial(5)
        #             combinations(10, 3)
        #             sin(pi / 2)
        #             sin_deg(90)
        #             log10(1000)
        #             mean([10, 20, 30])
        #         """,
        #         "parameters": {
        #             "type": "object",
        #             "properties": {
        #                 "expression": {
        #                     "type": "string",
        #                     "description": """
        #                         Mathematical expression to calculate.

        #                         Examples:
        #                         2 + 5 * 3
        #                         sqrt(144)
        #                         percent_of(20, 500)
        #                         discount(100000, 20)
        #                         compound_interest(1000000, 5, 2)
        #                         mean([10,20,30])
        #                     """
        #                 }
        #             },
        #             "required": [
        #                 "expression"
        #             ]
        #         }
        #     }
        # }
        {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": """
                    Evaluate a mathematical expression accurately.

                    ALWAYS use this tool for numerical calculations.

                    The expression supports:
                    +  addition
                    -  subtraction
                    *  multiplication
                    /  division
                    %  modulo
                    ** power
                    parentheses

                    Supported functions include:
                    sqrt, cbrt, root, abs, round, min, max,
                    sin, cos, tan, asin, acos, atan,
                    sin_deg, cos_deg, tan_deg,
                    log, log10, log2, ln,
                    factorial, combinations, permutations,
                    gcd, lcm,
                    mean, median, variance, stdev,
                    percent_of, discount, tax,
                    percentage_change, simple_interest,
                    simple_interest_total, compound_interest,
                    compound_interest_only, cagr, loan_payment.

                    IMPORTANT:
                    - Do not invent functions.
                    - Do not use functions that are not listed above.
                    - Every function must have the correct number of arguments.
                    - Use standard mathematical notation whenever possible.
                    - For discounts, taxes and percentages, prefer basic arithmetic
                    when it is simpler and clearer.

                    Examples:
                    12500000 * (1 - 15/100)
                    5000000 * (1 - 10/100)
                    (12500000 * (1 - 15/100) + 5000000 * (1 - 10/100) + 750000) * 1.11
                    sqrt(144)
                    2 ** 10
                    mean([10, 20, 30])
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "A valid mathematical expression."
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
    ]

def exec_tool(name: str, arguments: dict):
    if name == "get_city":
        return get_city()
    elif name == "get_weather":
        return get_weateher(arguments['city_name'])
    elif name == "calculator":
        return calculator.calculate(arguments["expression"])
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

#exmple 1
# [
#     {
#         "role": "system",
#         "content": "\n            You are Kwanza AI, developed by Arsal Fahrulloh.\n\n            You can answer general questions normally.\n\n            Available tools:\n            - get_city\n            - get_weather\n            - calculator\n\n            Tool rules:\n\n            1. get_city\n            Use this tool when you need to know whether a city exists in the database.\n            Never assume a city exists.\n\n            2. get_weather\n            Use this tool when the user asks for weather information.\n            The city name must come from get_city.\n            Never invent city names or weather information.\n\n            3. calculator\n            Use this tool whenever the user asks for:\n            - arithmetic calculations\n            - percentages\n            - discounts\n            - taxes\n            - tips\n            - averages\n            - statistics\n            - powers\n            - roots\n            - logarithms\n            - trigonometry\n            - factorial\n            - combinations\n            - permutations\n            - simple interest\n            - compound interest\n            - loan payments\n            - percentage changes\n            - CAGR\n            - or any other numerical calculation\n\n            IMPORTANT:\n            - Do not perform complex calculations mentally when calculator can be used.\n            - Always use calculator for numerical calculations.\n            - Do not invent calculator results.\n            - Use the calculator result in your final answer.\n            - For ambiguous mathematical expressions, interpret them using standard mathematical precedence.\n        "
#     },
#     {
#         "role": "user",
#         "content": "Hitung berapa hasil dari 25 × 48 + 750 ÷ 5 − 15² + √144. Jangan hitung secara manual, gunakan calculator tool dan berikan hasil akhirnya beserta langkah perhitungannya."
#     },
#     {
#         "role": "assistant",
#         "thinking": "The user is asking me to calculate: 25 × 48 + 750 ÷ 5 - 15² + √144\n\nThey want me NOT to do the calculation manually, but instead use the calculator tool and provide both the result and the step-by-step process.\n\nLet me break this down:\n- 25 × 48 = ? (multiplication)\n- 750 ÷ 5 = ? (division)\n- 15² = ? (exponentiation/powower)\n- √144 = ? (square root)\n\nI should use the calculator tool for these calculations. Let me think about how to structure this:\n\nSince standard mathematical precedence applies, I need to follow order of operations (PEMDAS/BODMAS):\n1. Exponents first (√144 and 15²)\n2. Multiplication and division (left to right)\n3. Addition and subtraction (left to right)\n\nHowever, for a complex expression like this with multiple operations, I could calculate it all at once in one calculator call or break it down into steps.\n\nGiven the instructions emphasize using calculator tools properly, let me use one comprehensive calculation that follows standard mathematical precedence: 25*48+750/5-15^2+sqrt(144)\n\nLet me calculate this using the calculator tool and also show step-by-step for clarity as requested.",
#         "content": "",
#         "tool_calls": [
#             {
#                 "function": {
#                     "name": "calculator",
#                     "arguments": {
#                         "expression": "25 * 48 + 750 / 5 - 15² + √144"
#                     }
#                 }
#             }
#         ]
#     },
#     {
#         "role": "tool",
#         "tool_name": "calculator",
#         "content":"{\"success\": false, \"expression\": \"25 * 48 + 750 / 5 - 15\² + \√144\", \"error\": \"Invalid expression: invalid character '\²' (U+00B2) (<unknown>, line 1)\"}"
#     },
#     {
#         "role": "assistant",
#         "thinking": "The calculator doesn't accept the superscript notation (²). I need to use a different syntax for exponents. Let me try using power function or just write it as * operator, like 15*15 instead of 15².\n\nAlso let me check if sqrt is supported - looking at the examples in the calculator description:\n- \"sqrt(144)\" seems to be mentioned explicitly! So I should use that syntax.\n\nLet me try again with proper syntax: 25 * 48 + 750 / 5 - 15*15 + sqrt(144) or maybe just leave as is? Let me check if power operation exists... The examples show \"sqrt\" but let me think about how to do the exponentiation.\n\nActually, looking at the calculator description again:\n- It mentions \"powers\" in supported operations list\n- Examples show simple math expressions like 2 + 5 * 3 and sqrt(144)\n\nLet me try a different approach - I'll calculate it step by step to make sure each part works correctly. First let me check if the expression is too complex for one call, or maybe use power() function instead of superscript notation? Let me also note that percent_of exists but not other specific math functions like exp().\n\nActually, looking more carefully at the calculator examples:\n- \"2 + 5 * 3\" - basic operations work\n- \"sqrt(144)\" works\n- But I don't see a power() function mentioned in the description... \n\nLet me try using ^ operator instead of superscript notation or multiply explicitly. Let me recalculate with explicit multiplication: 25*48+750/5-15*15+sqrt(144)",
#         "content": "",
#         "tool_calls": [
#             {
#                 "function": {
#                     "name": "calculator",
#                     "arguments": {
#                         "expression": "25 * 48 + 750 / 5 - 15 * 15 + sqrt(144)"
#                     }
#                 }
#             }
#         ]
#     },
#     {
#         "role": "tool",
#         "tool_name": "calculator",
#         "content": "{\"success\": true, \"expression\": \"25 * 48 + 750 / 5 - 15 * 15 + sqrt(144)\", \"result\": 1137.0}"
#     },
#     {
#         "role": "assistant",
#         "thinking": "Great! The calculator worked and gave me the result: 1137.0\n\nNow I need to present this with a step-by-step explanation showing how each part of the calculation was computed, following standard mathematical order of operations (PEMDAS/BODMAS):\n\nLet me break down:\n- Step 1: Calculate powers/roots first\n  - √144 = 12\n  - 15² = 225\n  \n- Step 2: Multiplication and division  \n  - 25 × 48 = 1,200\n  - 750 ÷ 5 = 150\n\n- Step 3: Addition and subtraction (left to right)\n  - Starting from the left: 1,200 + 150 = 1,350\n  - Then subtract exponents: 1,350 - 225 = 1,125\n  - Finally add square root: 1,125 + 12 = 1,137\n\nLet me verify this is correct... yes the final answer is 1,137 (or 1137.0 as returned by calculator)",
#         "content": "Berikut adalah perhitungan langkah demi langkah untuk menyelesaikan **25 × 48 + 750 ÷ 5 − 15² + √144**:\n\n---\n\n## 📊 Langkah Perhitungan:\n\n### Step 1: Hitung Pangkat dan Akar Kuadrat (Pertama)\n- **√144** = **12**  \n- **15²** = **225**  \n\n$$ \\text{Menjadi}: 25 × 48 + 750 ÷ 5 - 225 + 12 $$\n\n---\n\n### Step 2: Hitung Perkalian dan Pembagian (Kiri ke Kanan)\n- **25 × 48** = **1,200**  \n- **750 ÷ 5** = **150**  \n\n$$ \\text{Menjadi}: 1.200 + 150 - 225 + 12 $$\n\n---\n\n### Step 3: Hitung Penjumlahan dan Pengurangan (Kiri ke Kanan)\n- **1,200 + 150** = **1,350**  \n- **1,350 − 225** = **1,125**  \n- **1,125 + 12** = **1,137**\n\n---\n\n## ✅ Hasil Akhir:\n$$ \\text{Hasil} = \\mathbf{1.137} $$ \n\n*(Dihitung menggunakan tool calculator dengan hasil akhir `1137.0`)*",
#         "tool_calls": null
#     }
# ]

#example 2
# [
#     {
#         "role": "system",
#         "content": "\n            You are Kwanza AI, developed by Arsal Fahrulloh.\n\n            You can answer general questions normally.\n\n            Available tools:\n            - get_city\n            - get_weather\n            - calculator\n\n            Tool rules:\n\n            1. get_city\n            Use this tool when you need to know whether a city exists in the database.\n            Never assume a city exists.\n\n            2. get_weather\n            Use this tool when the user asks for weather information.\n            The city name must come from get_city.\n            Never invent city names or weather information.\n\n            3. calculator\n            Use this tool whenever the user asks for:\n            - arithmetic calculations\n            - percentages\n            - discounts\n            - taxes\n            - tips\n            - averages\n            - statistics\n            - powers\n            - roots\n            - logarithms\n            - trigonometry\n            - factorial\n            - combinations\n            - permutations\n            - simple interest\n            - compound interest\n            - loan payments\n            - percentage changes\n            - CAGR\n            - or any other numerical calculation\n\n            IMPORTANT:\n            - Do not perform complex calculations mentally when calculator can be used.\n            - Always use calculator for numerical calculations.\n            - Do not invent calculator results.\n            - Use the calculator result in your final answer.\n            - For ambiguous mathematical expressions, interpret them using standard mathematical precedence.\n        "
#     },
#     {
#         "role": "user",
#         "content": "Bantu saya mengerjakan soal ini ,Pa Tantan memiliki uang Rp20.000.000 dan ingin membeli 3 barang. Laptop seharga Rp12.500.000 mendapat diskon 15%, HP seharga Rp5.000.000 mendapat diskon 10%, dan mouse seharga Rp750.000 tidak mendapat diskon. Setelah semua diskon, total pembelian dikenakan pajak 11%. Apakah uang Pa Tantan cukup? Jika cukup, berapa sisa uang Pa Tantan?"
#     },
#     {
#         "role": "assistant",
#         "thinking": "The user is asking me to help solve a math problem about buying items with discounts and taxes. Let me break this down:\n\n1. Laptop price: Rp12,500,000 with 15% discount\n2. HP (phone) price: Rp5,000,000 with 10% discount  \n3. Mouse price: Rp750,000 no discount\n4. Total purchase has 11% tax applied after discounts\n\nI need to use the calculator tool for this since there are multiple calculations involving percentages and totals. Let me think about what calculation I should make with the calculator tool.\n\nThe user asks if Pa Tantan's money (Rp20,000,000) is enough and how much remains after purchase + tax.\n\nLet me calculate:\n1. Discounted laptop price = 12500000 * (1 - 15/100) or 12500000 - (12500000 * 15/100)\n2. Discounted HP price = 5000000 * (1 - 10/100) \n3. Mouse = 750000 (no discount)\n4. Total before tax = laptop + hp + mouse\n5. After tax = total_before_tax * (1 + 11/100)\n\nI should use the calculator tool to compute this properly as instructed in my system rules about using calculator for numerical calculations involving percentages, discounts and taxes.\n\nLet me create an expression that calculates everything step by step or all at once:\n- Laptop discounted = 12500000 * (1 - 15/100) \n- HP discounted = 5000000 * (1 - 10/100)\n- Mouse = 750000\n- Total before tax = laptop + hp + mouse\n- Total after tax = total_before_tax * 1.11\n\nI'll use calculator with an expression that calculates everything in one go to find the final cost, then compare with Rp20,000,000 and calculate remainder if positive.",
#         "content": "",
#         "tool_calls": [
#             {
#                 "function": {
#                     "name": "calculator",
#                     "arguments": {
#                         "expression": "12500000 * (1 - 15/100) + 5000000 * (1 - 10/100) + 750000 * 1.11"
#                     }
#                 }
#             }
#         ]
#     },
#     {
#         "role": "tool",
#         "tool_name": "calculator",
#         "content": "{\"success\": true, \"expression\": \"12500000 * (1 - 15/100) + 5000000 * (1 - 10/100) + 750000 * 1.11\", \"result\": 15957500.0}"
#     },
#     {
#         "role": "assistant",
#         "thinking": "Wait, let me recalculate this more carefully:\n\nThe problem says the tax applies to the TOTAL purchase after discounts are applied, not just to each item separately with individual taxes and then added up together. Let me think again...\n\nActually looking at my expression again - I calculated it as if only mouse has 1.11 multiplier, which is wrong. The 1.11 should apply to the entire total (laptop + hp + mouse) after all discounts are applied first.\n\nLet me recalculate:\n- Laptop discounted = 12500000 * (1 - 15/100) \n- HP discounted = 5000000 * (1 - 10/100)  \n- Mouse = 750000\n- Total before tax = laptop_discounted + hp_discounted + mouse\n- After tax = total_before_tax * 1.11\n\nLet me create a better expression:\n(12500000 * (1 - 15/100) + 5000000 * (1 - 10/100) + 750000) * 1.11\n\nOr let me think step by step more carefully:\n- Laptop after discount = 12500000 × 85% = 12500000 × (1 - 0.15) \n- HP after discount = 5000000 × 90% = 5000000 × (1 - 0.10)\n- Mouse = 750000\n\nLet me use calculator with the correct expression:\n\n\nI realize my previous calculation had a critical error in how I applied taxes and discounts across items. The tax should be calculated on the total sum after all individual item discounts are computed separately, not just multiplying one specific component by the tax rate.",
#         "content": "",
#         "tool_calls": [
#             {
#                 "function": {
#                     "name": "calculator",
#                     "arguments": {
#                         "expression": "(12500000 * (1 - 15/100) + 5000000 * (1 - 10/100) + 750000) * 1.11"
#                     }
#                 }
#             }
#         ]
#     },
#     {
#         "role": "tool",
#         "tool_name": "calculator",
#         "content": "{\"success\": true, \"expression\": \"(12500000 * (1 - 15/100) + 5000000 * (1 - 10/100) + 750000) * 1.11\", \"result\": 17621250.0}"
#     },
#     {
#         "role": "assistant",
#         "thinking": "Now let me calculate how much money Pa Tantan has remaining:\n\nRemaining = 20,000,000 - 17,621,250 = ?\n\nLet me use the calculator to get this final answer.",
#         "content": "",
#         "tool_calls": [
#             {
#                 "function": {
#                     "name": "calculator",
#                     "arguments": {
#                         "expression": "20000000 - 17621250"
#                     }
#                 }
#             }
#         ]
#     },
#     {
#         "role": "tool",
#         "tool_name": "calculator",
#         "content": "{\"success\": true, \"expression\": \"20000000 - 17621250\", \"result\": 2378750}"
#     },
#     {
#         "role": "assistant",
#         "thinking": "Perfect! Now I have all the information needed to answer the question:\n\n- Total cost after discount and tax: Rp17,621,250.00\n- Pa Tantan's money: Rp20,000,000.00\n- Remaining money: Rp2,378,750.00\n\nSo the answer is: Yes, he has enough money and will have Rp2,378,750 remaining after purchase with tax.",
#         "content": "Mari saya jelaskan perhitungannya untuk Anda:\n\n**Langkah-langkah perhitungan:**\n\n1. **Laptop dengan diskon 15%:** \n   = Rp12.500.000 × (1 - 15/100)  \n   = Rp12.500.000 × 85%  \n   = Rp10.625.000\n\n2. **HP dengan diskon 10%:** \n   = Rp5.000.000 × (1 - 10/100)  \n   = Rp5.000.000 × 90%  \n   = Rp4.500.000\n\n3. **Mouse tanpa diskon:** \n   = Rp750.000\n\n4. **Total harga sebelum pajak:**\n   = Rp10.625.000 + Rp4.500.000 + Rp750.000  \n   = Rp15.875.000\n\n5. **Setelah ditambah pajak 11%:** \n   = (Rp10.625.000 + Rp4.500.000 + Rp750.000) × 1,11  \n   = Rp15.875.000 × 1,11  \n   = **Rp17.621.250**\n\n---\n\n## Jawaban:\n✅ **Uang Pa Tantan CUKUP!** \n\n- Biaya total pembelian setelah pajak: **Rp17.621.250**\n- Uang yang dimiliki Pa Tantan: Rp20.000.000\n- Sisa uangPa Tantan : **Rp2.378.750**\n\nJadi Pa Tantan cukup membeli 3 barang tersebut dan masih menyisakan sekitar dua juta tiga ratus tujuh puluh delapan ribu rupiah.",
#         "tool_calls": null
#     }
# ]