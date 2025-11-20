from flask import Flask, request, jsonify
import os
import time
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
    app.logger.info(f"Fetching variants for {brand}, {model}, {fuel_type}, {transmission}")
    """Get variants for a specific brand, model, fuel type, and transmission"""
    brand = brand.upper().strip()
    model = model.upper().strip()
    fuel_type = fuel_type.upper().strip()
    transmission = transmission.upper().strip()

    try:
        if prices[brand][model][fuel_type][transmission]:
            app.logger.info(f"Variants found: {list(prices[brand][model][fuel_type][transmission].keys())}")
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
    app.logger.info(f"Fetching ex-showroom price for {brand}, {model}, {fuel_type}, {transmission}, {variant}")

    try:
        if prices[brand][model][fuel_type][transmission][variant]:
            app.logger.info(f"Ex-showroom price found: {prices[brand][model][fuel_type][transmission][variant]}")
            return prices[brand][model][fuel_type][transmission][variant]
    except KeyError:
        pass
    return -1


def road_tax_multiplier(state: str, ex_showroom_price: int, fuel_type: str) -> float:
    """Calculate road tax multiplier based on state, price, and fuel type"""
    app.logger.info(f"Calculating road tax multiplier for {state}, {ex_showroom_price}, {fuel_type}")
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
    ex_showroom_price = int(ex_showroom_price)
    road_tax_multiplier = float(road_tax_multiplier)
    road_tax = int(ex_showroom_price * road_tax_multiplier)
    state_development_fee = 4000
    registration_charges = 600
    fastag = 600
    hypothecation_endorsement = 1500
    other_charges = 400
    insurance = int(ex_showroom_price * 0.05)

    app.logger.info(
        f"Calculating on-road price with ex_showroom_price: {ex_showroom_price}, road_tax: {road_tax}, state_development_fee: {state_development_fee}, registration_charges: {registration_charges}, fastag: {fastag}, hypothecation_endorsement: {hypothecation_endorsement}, other_charges: {other_charges}, insurance: {insurance}")
    
    return ex_showroom_price + road_tax + state_development_fee + registration_charges + fastag + hypothecation_endorsement + other_charges + insurance


def function_caller(func_name: str, params: str):
    """Call a function by name with string parameters"""
    app.logger.info(f"Calling function {func_name} with params: {params}")
    try:
        function_map = {
            "variants": variants,
            "ex_showroom_price": ex_showroom_price,
            "road_tax_multiplier": road_tax_multiplier,
            "on_road_price": on_road_price
        }

        if func_name not in function_map:
            app.logger.error(f"Function {func_name} not found") 
            return f"Function {func_name} not found"

        func = function_map[func_name]

        if params.strip():
            params_list = [param.strip() for param in params.split(",")]
        else:
            params_list = []

        app.logger.info(f"Executing {func_name} with parameters: {params_list}")
        return func(*params_list)

    except Exception as e:
        error_msg = f"Error calling function {func_name}: {str(e)}"
        app.logger.error(error_msg)
        return error_msg


def process_query(query: str) -> dict:
    # import pdb; pdb.set_trace()
    """Process a query using the Gemini model with agentic loop"""
    max_iterations = 20
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
        time.sleep(1)  # To avoid hitting rate limits

        # Get model's response
        prompt = f"{system_prompt}\n\nQuery: {current_query}"
        app.logger.info(f"Iteration {iteration + 1}, Prompt sent to model: {prompt}")
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        response_text = response.text.strip()
        app.logger.info(f"Iteration {iteration + 1}, Model response: {response_text}")

        if response_text.startswith("FUNCTION_CALL:"):
            _, function_info = response_text.split(":", 1)
            func_name, params = [x.strip() for x in function_info.split("|", 1)]
            
            app.logger.info(f"Function to call: {func_name} with params: {params}")
            iteration_result = function_caller(func_name, params)
            
            last_response = iteration_result
            iteration_response.append(f"In iteration {iteration + 1}, function {func_name} was called with parameters '{params}' and returned: {iteration_result}")
            app.logger.info(f"Iteration {iteration + 1}, Function result: {iteration_result}")

        elif response_text.startswith("FINAL_ANSWER:"):
            # Extract the answer part
            _, answer_part = response_text.split(":", 1)
            answer_part = answer_part.strip()
            
            # Try to parse as JSON/dict
            try:
                import json
                if answer_part.startswith("{"):
                    final_answer = json.loads(answer_part)
                    app.logger.info(f"Final answer parsed as dict: {final_answer}")
                else:
                    # If it's not a dict, return it as is
                    final_answer = {"result": answer_part}
                    app.logger.info(f"Final answer as string: {final_answer}")
            except json.JSONDecodeError:
                app.logger.warning("Final answer is not a valid JSON, returning as string : {}", answer_part)
                final_answer = {"result": answer_part}
            
            app.logger.info(f"Iteration {iteration + 1}, Final answer obtained: {final_answer}")
            return final_answer

        iteration += 1

    # If max iterations reached without final answer
    app.logger.error("Max iterations reached without final answer")
    return {"error": "Max iterations reached without final answer", "last_result": last_response}


@app.route('/v1/chat', methods=['POST'])
def chat():
    # import pdb; pdb.set_trace()
    """API endpoint to process queries"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            app.logger.error("Missing 'query' field in request body")
            return jsonify({"error": "Missing 'query' field in request body"}), 400
        
        query = data['query']
        app.logger.info(f"Received query: {query}")
        
        # Process the query
        result = process_query(query)
        
        return jsonify(result), 200
    
    except Exception as e:
        app.logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
