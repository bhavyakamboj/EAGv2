from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Initialize Gemini client
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Price data
prices = {
    "TATA": {
        "HARRIER": {
            "DIESEL": {
                "AUTOMATIC": {
                    "PUREXAT": 2303000,
                    "ADVENTUREXAT": 1957000,
                    "FEARLESSXAT": 2845000
                },
                "MANUAL": {
                    "SMART": 1747000,
                    "PUREX": 2116000,
                    "ADVENTUREX": 2234000,
                    "FEARLESSX": 2641000
                }
            },
            "ELECTRIC": {
                "AUTOMATIC": {
                    "ADVENTURE65": 2326000,
                    "FEARLESSPLUS65": 2592000,
                    "EMPOWERED75": 3256000,
                    "EMPOWEREDQWD75": 3432000
                }
            }
        }
    }
}


def variants(brand: str, model: str, fuel_type: str, transmission: str) -> list:
    """Get variants for a specific brand, model, fuel type, and transmission"""
    brand = brand.upper().strip()
    model = model.upper().strip()
    fuel_type = fuel_type.upper().strip()
    transmission = transmission.upper().strip()

    try:
        if prices[brand][model][fuel_type][transmission]:
            return list(prices[brand][model][fuel_type][transmission].keys())
    except KeyError:
        pass
    return []


def ex_showroom_price(brand: str, model: str, fuel_type: str, transmission: str, variant: str) -> int:
    """Get ex-showroom price for a specific variant"""
    brand = brand.upper().strip()
    model = model.upper().strip()
    fuel_type = fuel_type.upper().strip()
    transmission = transmission.upper().strip()
    variant = variant.upper().strip()

    try:
        if prices[brand][model][fuel_type][transmission][variant]:
            return prices[brand][model][fuel_type][transmission][variant]
    except KeyError:
        pass
    return -1


def road_tax_multiplier(state: str, ex_showroom_price: int, fuel_type: str) -> float:
    """Calculate road tax multiplier based on state, price, and fuel type"""
    if int(ex_showroom_price) > 2500000:
        above25 = True
    else:
        above25 = False

    if fuel_type == "ELECTRIC" and above25:
        if state in ["DELHI", "TAMILNADU", "HYDERABAD", "MAHARASHTRA",
                     "ODISHA", "PUNJAB", "WESTBENGAL", "MEGHALAYA", "BIHAR", "TELANGANA"]:
            return 0
        if state in ["GUJARAT", "KERALA"]:
            return 0.05
    if fuel_type == "DIESEL":
        return 0.125

    return 0.1


def on_road_price(ex_showroom_price: int, road_tax_multiplier: float) -> int:
    """Calculate on-road price"""
    road_tax = state_development_fee = 4000
    registration_charges = 600
    fastag = 600
    hypothecation_endorsement = 1500
    other_charges = 400
    insurance = int(int(ex_showroom_price) * 0.05)

    return int(ex_showroom_price) + road_tax + state_development_fee + registration_charges + fastag + hypothecation_endorsement + other_charges + insurance


def function_caller(func_name: str, params: str):
    """Call a function by name with string parameters"""
    try:
        function_map = {
            "variants": variants,
            "ex_showroom_price": ex_showroom_price,
            "road_tax_multiplier": road_tax_multiplier,
            "on_road_price": on_road_price
        }

        if func_name not in function_map:
            return f"Function {func_name} not found"

        func = function_map[func_name]

        if params.strip():
            params_list = [param.strip() for param in params.split(",")]
        else:
            params_list = []

        return func(*params_list)

    except Exception as e:
        error_msg = f"Error calling function {func_name}: {str(e)}"
        return error_msg


def process_query(query: str) -> dict:
    """Process a query using the Gemini model with agentic loop"""
    max_iterations = 10
    last_response = None
    iteration = 0
    iteration_response = []

    system_prompt = """You are a math agent solving problems in iterations. Respond with EXACTLY ONE of these formats:
1. FUNCTION_CALL: python_function_name|input
2. FINAL_ANSWER: {answer_dict}

input is a string of comma separated values.

Available functions:
1. variants(brand, model, fuel_type, transmission) - Returns list of variant names
2. ex_showroom_price(brand, model, fuel_type, transmission, variant) - Returns the ex-showroom price as integer
3. road_tax_multiplier(state, ex_showroom_price, fuel_type) - Returns the road tax multiplier as float
4. on_road_price(ex_showroom_price, road_tax_multiplier) - Returns the on-road price as integer

DO NOT include multiple responses. Give ONE response at a time."""

    while iteration < max_iterations:
        if last_response is None:
            current_query = query
        else:
            current_query = query + "\n\n" + " ".join(iteration_response)
            current_query = current_query + " What should I do next?"

        # Get model's response
        prompt = f"{system_prompt}\n\nQuery: {current_query}"
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        response_text = response.text.strip()

        if response_text.startswith("FUNCTION_CALL:"):
            _, function_info = response_text.split(":", 1)
            func_name, params = [x.strip() for x in function_info.split("|", 1)]
            iteration_result = function_caller(func_name, params)
            
            last_response = iteration_result
            iteration_response.append(f"In iteration {iteration + 1}, function {func_name} was called with parameters '{params}' and returned: {iteration_result}")

        elif response_text.startswith("FINAL_ANSWER:"):
            # Extract the answer part
            _, answer_part = response_text.split(":", 1)
            answer_part = answer_part.strip()
            
            # Try to parse as JSON/dict
            try:
                import json
                if answer_part.startswith("{"):
                    final_answer = json.loads(answer_part)
                else:
                    # If it's not a dict, return it as is
                    final_answer = {"result": answer_part}
            except json.JSONDecodeError:
                final_answer = {"result": answer_part}
            
            return final_answer

        iteration += 1

    # If max iterations reached without final answer
    return {"error": "Max iterations reached without final answer", "last_result": last_response}


@app.route('/v1/chat', methods=['POST'])
def chat():
    """API endpoint to process queries"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' field in request body"}), 400
        
        query = data['query']
        
        # Process the query
        result = process_query(query)
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
