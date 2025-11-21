import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
from google import genai
from concurrent.futures import TimeoutError
from functools import partial
import json, time
from rich.console import Console
from rich.panel import Panel

console = Console()

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Access your API key and initialize Gemini client correctly
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

max_iterations = 10
last_response = None
iteration = 0
iteration_response = []

async def generate_with_timeout(client, prompt, timeout=10):
    """Generate content with a timeout"""
    try:
        console.print(Panel("Car on-road price calculator.", border_style="magenta"))
        # Convert the synchronous generate_content call to run in a thread
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None, 
                lambda: client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
            ),
            timeout=timeout
        )
        print("LLM generation completed")
        return response
    except TimeoutError:
        console.print("[red]LLM generation timed out![/red]")
        raise
    except Exception as e:
        print(f"[red]Error in LLM generation: {e}[/red]")
        raise

def reset_state():
    """Reset all global variables to their initial state"""
    global last_response, iteration, iteration_response
    last_response = None
    iteration = 0
    iteration_response = []

async def process_query(query: str):
    reset_state()  # Reset at the start of main
    try:
        # Create a single MCP server connection
        console.print("[yellow]Establishing connection to MCP server...[/yellow]")
        server_params = StdioServerParameters(
            command="python",
            args=["mcp-server.py"]
        )

        async with stdio_client(server_params) as (read, write):
            console.print("[yellow]Connection established, creating session...[/yellow]")
            async with ClientSession(read, write) as session:
                console.print("[yellow]Session created, initializing...[/yellow]")
                await session.initialize()
                
                # Get available tools
                console.print("[yellow]Requesting tool list...[/yellow]")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                console.print(f"[green]Successfully retrieved {len(tools)} tools[/green]")

                # Create system prompt with available tools
                print("Creating system prompt...")
                print(f"Number of tools: {len(tools)}")
                
                try:
                    # First, let's inspect what a tool object looks like
                    # if tools:
                    #     print(f"First tool properties: {dir(tools[0])}")
                    #     print(f"First tool example: {tools[0]}")
                    
                    tools_description = []
                    for i, tool in enumerate(tools):
                        try:
                            # Get tool properties
                            params = tool.inputSchema
                            desc = getattr(tool, 'description', 'No description available')
                            name = getattr(tool, 'name', f'tool_{i}')
                            
                            # Format the input schema in a more readable way
                            if 'properties' in params:
                                param_details = []
                                for param_name, param_info in params['properties'].items():
                                    param_type = param_info.get('type', 'unknown')
                                    param_details.append(f"{param_name}: {param_type}")
                                params_str = ', '.join(param_details)
                            else:
                                params_str = 'no parameters'

                            tool_desc = f"{i+1}. {name}({params_str}) - {desc}"
                            tools_description.append(tool_desc)
                            print(f"Added description for tool: {tool_desc}")

                        except Exception as e:
                            print(f"[red]Error processing tool {i}: {e}[/red]")
                            tools_description.append(f"{i+1}. Error processing tool")
                    
                    tools_description = "\n".join(tools_description)
                    console.print("[green]Successfully created tools description[/green]")

                except Exception as e:
                    console.print(f"[red]Error creating tools description: {e}[/red]")

                    tools_description = "Error loading tools"
                
                console.print("[green]Created system prompt...[/green]")
                
                system_prompt = f"""
                You are a math-and-planning agent that solves car-pricing problems using explicit, verifiable reasoning steps. You operate in a loop where you reason, act, and verify.

                ### AVAILABLE FUNCTIONS FOR TOOL USE
                {tools_description}
                
                ### OUTPUT FORMAT
                You must respond with a SINGLE valid JSON object. Do not include markdown formatting (like ```json).
                The JSON must strictly follow this schema:

                {{
                "step_id": integer_step_number,
                "reasoning": {{
                    "type": "< arithmetic | logic | lookup | verification >",
                    "thought_trace": "< detailed step-by-step thinking >",
                    "need_for_tool":< true | false >
                }},
                "self_check": {{
                    "input_validation": "confirm inputs are present/valid",
                    "plausibility_check": "confirm previous result makes sense",
                    "previous_response": "<answer_or_error_message>",
                    "last_user_input": "<previous input from user>",
                    "last_tool_use": "previous tool use",
                    "status": "<PASS | FAIL"
                }},
                "action": {{
                    "type": "FUNCTION_CALL | FINAL_ANSWER | ERROR",
                    "function_name": "<name_or_null>",
                    "function_args": {{"arg1": "value1", "arg2": "value2"}},
                    "final_response_text": "<answer_or_error_message>"
                }}
                }}

                ### REASONING & BEHAVIOR RULES
                1. **Trace Your Thoughts:** Fill the `thought_trace` field before deciding on an action. Explain *why* you are taking the next step.
                2. **Categorize:** Explicitly label your logic in `reasoning.type`.
                3. **Verify Inputs:** Before calling a function, ensure you have all required arguments in the `self_check` field.
                4. **Safety Fallback:** If `self_check.status` is "FAIL" or if you lack information, set `action.type` to "ERROR" and ask the user for missing information.
                5. **Tool Separation:** Never perform the math for `on_road_price` or `road_tax_multiplier` yourself. You must call the tools.
                6. **Iterative Flow:** Use the output provided by the user (from previous tool calls) to inform your next JSON response.
                7. **When to Stop:** Return FINAL_ANSWER when you have the complete on_road_price calculation."""
                
                # import pdb; pdb.set_trace()
                print("{system_prompt}")

                with open("prompt_of_prompts.md", "r", encoding='utf-8') as file:
                    evaluation_prompt = file.read()

                query = """Find the on road price of a car with brand as "Tata", model as "Harrier", fuel type as "Diesel", transmission as "Automatic" and state as "Delhi"."""
                print("Starting iteration loop...")
                
                # Evaluate the system prompt before proceeding
                print("\n--- Evaluating System Prompt ---")
                try:
                    system_prompt_evaluation = await generate_with_timeout(
                        client, 
                        f"{evaluation_prompt}\n\nSystem Prompt to evaluate:\n{system_prompt}"
                    )
                    evaluation_result = system_prompt_evaluation.text.strip()
                    console.print(f"System Prompt Evaluation Result:\n[green]{evaluation_result}[/green]")
                    print("Evaluation completed. Proceeding with main loop...\n")
                except Exception as e:
                    console.print(f"[red]Error evaluating system prompt: {e}[/red]")
                    evaluation_result = None
                
                # Use global iteration variables
                global iteration, last_response
                context = ""
                
                while iteration < max_iterations:
                    time.sleep(1)  # Small delay for rate limiting
                    print(f"\n--- Iteration {iteration + 1} ---")
                    if iteration == 0:
                        current_query = query
                    else:
                        current_query = f"{query}\n\nPrevious context:\n{context}\n\nWhat should I do next?"
                    
                    # Get model's response with timeout
                    print("Preparing to generate LLM response...")
                    prompt = f"{system_prompt}\n\nQuery: {current_query}"

                    try:
                        response = await generate_with_timeout(client, prompt)
                        response_text = response.text.strip()
                        console.print(f"[green]LLM Response:\n{response_text}[/green]")
                        
                        # Parse JSON response
                        try:
                            # Try to extract JSON from response
                            json_start = response_text.find('{')
                            json_end = response_text.rfind('}') + 1
                            if json_start != -1 and json_end > json_start:
                                json_str = response_text[json_start:json_end]
                                agent_response = json.loads(json_str)
                            else:
                                raise ValueError("No JSON found in response")
                        except json.JSONDecodeError as e:
                            console.print(f"[red]Failed to parse JSON: {e}[/red]")
                            iteration_response.append(f"Iteration {iteration + 1}: Invalid JSON response")
                            iteration += 1
                            continue
                        
                    except Exception as e:
                        console.print(f"[red]Failed to get LLM response: {e}[/red]")
                        break

                    # Process the agent response
                    action_type = agent_response.get('action', {}).get('type')
                    
                    if action_type == "FUNCTION_CALL":
                        func_name = agent_response.get('action', {}).get('function_name')
                        func_args = agent_response.get('action', {}).get('function_args', {})
                        
                        console.print(f"[yellow]Calling tool: {func_name}[/yellow]")
                        console.print(f"[yellow]With arguments: {func_args}[/yellow]")
                        
                        try:
                            # Find the matching tool to validate
                            tool = next((t for t in tools if t.name == func_name), None)
                            if not tool:
                                print(f"Available tools: {[t.name for t in tools]}")
                                raise ValueError(f"Unknown tool: {func_name}")

                            console.print(f"[green]Found tool: {tool.name}[/green]")
                            
                            # Call the tool
                            result = await session.call_tool(func_name, arguments=func_args)
                            
                            console.print(f"[green]Tool result: {result}[/green]")
                            
                            # Extract result content
                            if hasattr(result, 'content'):
                                if isinstance(result.content, list):
                                    iteration_result = [
                                        item.text if hasattr(item, 'text') else str(item)
                                        for item in result.content
                                    ]
                                else:
                                    iteration_result = str(result.content)
                            else:
                                iteration_result = str(result)
                            
                            console.print(f"[green]Extracted result: {iteration_result}[/green]")
                            
                            # Format result for context
                            if isinstance(iteration_result, list):
                                result_str = ", ".join(str(r) for r in iteration_result)
                            else:
                                result_str = str(iteration_result)
                            
                            context += f"\nIteration {iteration + 1}: Called {func_name}({func_args}) and received: {result_str}"
                            iteration_response.append(context)
                            last_response = iteration_result

                        except Exception as e:
                            console.print(f"[red]Error calling tool: {str(e)}[/red]")
                            import traceback
                            traceback.print_exc()
                            context += f"\nIteration {iteration + 1}: Error - {str(e)}"
                            iteration += 1
                            continue

                    elif action_type == "FINAL_ANSWER":
                        final_text = agent_response.get('action', {}).get('final_response_text')
                        console.print(f"[green]\n=== Final Answer ===\n{final_text}[/green]")
                        break

                    elif action_type == "ERROR":
                        error_text = agent_response.get('action', {}).get('final_response_text')
                        console.print(f"[red]\n=== Agent Error ===\n{error_text}[/red]")
                        context += f"\nIteration {iteration + 1}: Error - {error_text}"

                    iteration += 1

        return {
            "status": "completed",
            "iterations": iteration,
            "final_response": last_response,
            "iteration_log": iteration_response
        }

    except Exception as e:
        console.print(f"[red]Error in main execution: {e}[/red]")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "iterations": iteration
        }
    finally:
        reset_state()  # Reset at the end of main

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/v1/chat', methods=['POST'])
def chat():
    """API endpoint to process queries"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            console.print("[red]Error: Missing 'query' field in request body[/red]")

            return jsonify({"error": "Missing 'query' field in request body"}), 400
        
        query = data['query']
        app.logger.info(f"Received query: {query}")
        
        # Process the query by running the async function
        result = asyncio.run(process_query(query))
        
        return jsonify(result), 200
    
    except Exception as e:
        console.print(f"[red]Error processing request: {str(e)}[/red]")

        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)