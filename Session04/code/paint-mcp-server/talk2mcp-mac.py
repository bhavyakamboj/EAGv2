import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
from google import genai
from concurrent.futures import TimeoutError
from functools import partial

# Load environment variables from a .env file into process environment variables.
# This allows you to keep secrets (like API keys) out of source code.
load_dotenv()

# Read the GEMINI_API_KEY variable from the environment. This will be used to
# authenticate with Google's generative AI (Gemini) client below.
api_key = os.getenv("GEMINI_API_KEY")

# Create a client object for the Gemini API. The client object wraps authentication
# and lets you call model generation functions. If api_key is None, calls will fail,
# so make sure the .env file or environment contains a valid key.
client = genai.Client(api_key=api_key)

# Control variables for the iterative agent loop.
# max_iterations: how many times the agent will loop before stopping.
# last_response: stores the last tool result the agent used.
# iteration: current iteration counter.
# iteration_response: list collecting human-readable summaries of each iteration.
max_iterations = 10
last_response = None
iteration = 0
iteration_response = []

# Asynchronous helper to run LLM generation with a timeout.
# We wrap the synchronous client.models.generate_content call in a thread
# (via loop.run_in_executor) so we can await it in asyncio code and apply a timeout.
async def generate_with_timeout(client, prompt, timeout=10):
    """Generate content with a timeout

    - prompt: text prompt to send to the LLM
    - timeout: number of seconds to wait before raising a TimeoutError
    """
    print("Starting LLM generation...")
    try:
        # Get the currently running event loop (asyncio core).
        loop = asyncio.get_event_loop()
        # run_in_executor runs the blocking code in a threadpool so it doesn't block
        # the async event loop. We then wait for it with asyncio.wait_for to enforce
        # the timeout.
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
        # This is the TimeoutError imported from concurrent.futures.
        # It is raised when the call to the LLM takes longer than `timeout`.
        print("LLM generation timed out!")
        raise
    except Exception as e:
        # Catch any other exceptions, print them for debugging, and re-raise.
        print(f"Error in LLM generation: {e}")
        raise

# Reset function to clear global state between runs.
def reset_state():
    """Reset all global variables to their initial state."""
    global last_response, iteration, iteration_response
    last_response = None
    iteration = 0
    iteration_response = []

# The main coroutine that sets up the MCP (tool) session and interacts with the LLM.
# This function uses async/await because networking and I/O are involved.
async def main():
    # Start with a fresh state for safety.
    reset_state()
    print("Starting main execution...")
    try:
        # Create server parameters for a child process that exposes tools via stdio.
        # StdioServerParameters tells the MCP client how to start the server that
        # provides tools. Here it runs "python paint-mcp-server-mac.py".
        print("Establishing connection to MCP server...")
        server_params = StdioServerParameters(
            command="python",
            args=["paint-mcp-server-mac.py"]
        )

        # stdio_client is an async context manager that starts the server process
        # and gives back read/write streams that the MCP client uses to communicate.
        # Using "async with" ensures proper cleanup when we exit the block.
        async with stdio_client(server_params) as (read, write):
            print("Connection established, creating session...")
            # ClientSession wraps the read/write streams into a higher-level API
            # for listing tools and calling them.
            async with ClientSession(read, write) as session:
                print("Session created, initializing...")
                # initialize negotiates capabilities with the server and must be awaited.
                await session.initialize()
                
                # List available tools from the MCP server. This returns metadata
                # about each tool (name, description, input schema) so the agent
                # can decide which tool to call and how to format arguments.
                print("Requesting tool list...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"Successfully retrieved {len(tools)} tools")

                # Build a textual description of the tools to include in the system prompt.
                # This helps the LLM understand what functions (tools) it can call.
                print("Creating system prompt...")
                print(f"Number of tools: {len(tools)}")
                
                try:
                    # tools_description will contain human-readable lines for each tool.
                    tools_description = []
                    for i, tool in enumerate(tools):
                        try:
                            # Access the tool input schema which tells parameter names and types.
                            params = tool.inputSchema
                            # description and name are common tool metadata fields.
                            desc = getattr(tool, 'description', 'No description available')
                            name = getattr(tool, 'name', f'tool_{i}')
                            
                            # If the schema contains 'properties' (typical JSON schema format),
                            # create a short summary of parameter names and types.
                            if 'properties' in params:
                                param_details = []
                                for param_name, param_info in params['properties'].items():
                                    param_type = param_info.get('type', 'unknown')
                                    param_details.append(f"{param_name}: {param_type}")
                                params_str = ', '.join(param_details)
                            else:
                                params_str = 'no parameters'

                            # Combine name, params and description into one line.
                            tool_desc = f"{i+1}. {name}({params_str}) - {desc}"
                            tools_description.append(tool_desc)
                            print(f"Added description for tool: {tool_desc}")
                        except Exception as e:
                            # If something goes wrong describing one tool, include an error
                            # message for that entry but continue processing the rest.
                            print(f"Error processing tool {i}: {e}")
                            tools_description.append(f"{i+1}. Error processing tool")
                    
                    # Join the tool descriptions into a single text block to feed the LLM.
                    tools_description = "\n".join(tools_description)
                    print("Successfully created tools description")
                except Exception as e:
                    # If building the tools description fails completely, fall back to a short message.
                    print(f"Error creating tools description: {e}")
                    tools_description = "Error loading tools"
                
                print("Created system prompt...")
                
                # The system prompt instructs the LLM how to behave. It is very strict:
                # the LLM must reply with exactly one line in a specified format.
                system_prompt = f"""You are a math agent with skills solving problems in iterations. You have access to various mathematical tools.

                Available tools:
                {tools_description}

                You must respond with EXACTLY ONE line in one of these formats (no additional text):
                1. For function calls:
                FUNCTION_CALL: function_name|param1|param2|...

                2. For final answers:
                FINAL_ANSWER: number

                3. For completing the task:
                COMPLETE_RUN

                Important:
                - When a function returns multiple values, you need to process all of them
                - Only give FINAL_ANSWER when you have completed all necessary calculations
                - Do not include multiple responses. Give ONE response at a time.
                - Do not include any explanations or additional text.
                - Do not repeat function calls with the same parameters
                - After you have completed the task, you can call COMPLETE_RUN to end the program

                Examples:
                - FUNCTION_CALL: add|5|3
                - FUNCTION_CALL: strings_to_chars_to_int|INDIA
                - FINAL_ANSWER: 42
                - COMPLETE_RUN

                DO NOT include any explanations or additional text.
                Your entire response should be a single line starting with either FUNCTION_CALL: or FINAL_ANSWER: or COMPLETE_RUN"""

                # The initial human query we give to the agent. The agent should follow the
                # system prompt and reply with a single-line instruction for next action.
                query = """Find the ASCII values of characters in INDIA and then return sum of exponentials of those values. """
                print("Starting iteration loop...")
                
                # Use global iteration variables to let modifications inside this function
                # affect the outer scope declared earlier.
                global iteration, last_response
                
                # Main loop: iterate until max_iterations or until the agent indicates completion.
                while iteration < max_iterations:
                    print(f"\n--- Iteration {iteration + 1} ---")
                    # If this is the first iteration, send the original query.
                    if last_response is None:
                        current_query = query
                    else:
                        # Otherwise, append the summaries of what happened in previous iterations,
                        # and ask the model what to do next. This is a simple way to provide memory.
                        current_query = current_query + "\n\n" + " ".join(iteration_response)
                        current_query = current_query + "  What should I do next?"

                    # Prepare the prompt for the LLM by combining the system instructions and the query.
                    print("Preparing to generate LLM response...")
                    prompt = f"{system_prompt}\n\nQuery: {current_query}"
                    try:
                        # Call the LLM asynchronously with a timeout.
                        response = await generate_with_timeout(client, prompt)
                        # response.text typically contains the model's textual answer.
                        response_text = response.text.strip()
                        print(f"LLM Response: {response_text}")
                        
                        # The LLM might include multiple lines; we look for the required one-line response.
                        for line in response_text.split('\n'):
                            line = line.strip()
                            if (line.startswith("FUNCTION_CALL:")):
                                response_text = line
                                break
                        
                    except Exception as e:
                        # If we cannot get a response from the model, break the loop and print error.
                        print(f"Failed to get LLM response: {e}")
                        break

                    # Now handle the model's one-line reply according to the protocol:
                    # FUNCTION_CALL, FINAL_ANSWER, or COMPLETE_RUN
                    if response_text.startswith("FUNCTION_CALL:"):
                        # Extract function name and parameters from the single-line protocol.
                        _, function_info = response_text.split(":", 1)
                        parts = [p.strip() for p in function_info.split("|")]
                        func_name, params = parts[0], parts[1:]
                        
                        # Print debug information to help trace what's happening.
                        print(f"\nDEBUG: Raw function info: {function_info}")
                        print(f"DEBUG: Split parts: {parts}")
                        print(f"DEBUG: Function name: {func_name}")
                        print(f"DEBUG: Raw parameters: {params}")
                        
                        try:
                            # Find the corresponding tool object by name so we know expected schema.
                            tool = next((t for t in tools if t.name == func_name), None)
                            if not tool:
                                # If tool not found, raise an error so the loop records it.
                                print(f"DEBUG: Available tools: {[t.name for t in tools]}")
                                raise ValueError(f"Unknown tool: {func_name}")

                            print(f"DEBUG: Found tool: {tool.name}")
                            print(f"DEBUG: Tool schema: {tool.inputSchema}")

                            # Prepare the arguments dictionary that will be passed to call_tool.
                            # We consult the tool's inputSchema to know parameter names and types.
                            arguments = {}
                            schema_properties = tool.inputSchema.get('properties', {})
                            print(f"DEBUG: Schema properties: {schema_properties}")

                            # For each parameter defined in the schema, pop one value from params list.
                            # Convert that value to the required type (int/float/array/string).
                            for param_name, param_info in schema_properties.items():
                                if not params:  # Ensure the model provided enough parameters.
                                    raise ValueError(f"Not enough parameters provided for {func_name}")
                                    
                                value = params.pop(0)  # Get the next parameter value.
                                param_type = param_info.get('type', 'string')
                                
                                print(f"DEBUG: Converting parameter {param_name} with value {value} to type {param_type}")
                                
                                # Convert the string parameter into the appropriate Python type.
                                if param_type == 'integer':
                                    arguments[param_name] = int(value)
                                elif param_type == 'number':
                                    arguments[param_name] = float(value)
                                elif param_type == 'array':
                                    # Arrays may be passed as "[1,2,3]" or "1,2,3" strings.
                                    if isinstance(value, str):
                                        value = value.strip('[]')
                                        value = value.split(',')
                                    # Convert each array element to int here; adjust if your tool expects other types.
                                    arguments[param_name] = [int(x.strip()) for x in value]
                                else:
                                    # Default: treat as string
                                    arguments[param_name] = str(value)

                            print(f"DEBUG: Final arguments: {arguments}")
                            print(f"DEBUG: Calling tool {func_name}")
                            
                            # Call the tool function on the MCP session. This is async and returns the tool result.
                            result = await session.call_tool(func_name, arguments=arguments)

                            print(f"DEBUG: Raw result: {result}")
                            
                            # The tool result can have a 'content' attribute containing text or multiple items.
                            if hasattr(result, 'content'):
                                print(f"DEBUG: Result has content attribute")
                                # If the content is a list, extract text from each item if possible.
                                if isinstance(result.content, list):
                                    iteration_result = [
                                        item.text if hasattr(item, 'text') else str(item)
                                        for item in result.content
                                    ]
                                else:
                                    iteration_result = str(result.content)
                            else:
                                # If the result doesn't have content, stringify the result object.
                                print(f"DEBUG: Result has no content attribute")
                                iteration_result = str(result)
                                
                            print(f"DEBUG: Final iteration result: {iteration_result}")
                            
                            # Format the result into a readable string for iteration_response history.
                            if isinstance(iteration_result, list):
                                result_str = f"[{', '.join(iteration_result)}]"
                            else:
                                result_str = str(iteration_result)
                            

                            # Record what we did and what the tool returned. This is used as context
                            # for future iterations so the LLM can reason about previous steps.
                            iteration_response.append(
                                f"In the {iteration + 1} iteration you called {func_name} with {arguments} parameters, "
                                f"and the function returned {result_str}."
                            )
                            # Update last_response for the top of the loop to know we have a result now.
                            last_response = iteration_result

                        except Exception as e:
                            # If any error occurred during preparing arguments or calling the tool,
                            # print debug info and append an error message to iteration_response.
                            print(f"DEBUG: Error details: {str(e)}")
                            print(f"DEBUG: Error type: {type(e)}")
                            import traceback
                            traceback.print_exc()
                            iteration_response.append(f"Error in iteration {iteration + 1}: {str(e)}")
                            # Break the loop because we can't continue from an exception here.
                            break

                    elif response_text.startswith("FINAL_ANSWER:"):
                        # If the model signals it's done and gives a final numeric answer, record it.
                        print("\n=== Math Agent Execution Complete ===")
                        iteration_response.append(
                                f"In the {iteration + 1} you completed calculations with {response_text}."
                            )
                        last_response = iteration_result
                    
                    elif response_text.startswith("COMPLETE"):
                        # COMPLETE_RUN or similar signal to end the run.
                        print("\n=== Task complete. Ending run now ===")
                        break

                    # Increment the iteration counter and loop again if not finished.
                    iteration += 1

    except Exception as e:
        # Catch-all for unexpected errors in the main flow. Print traceback to help debugging.
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Ensure global state is reset when main exits so subsequent runs start fresh.
        reset_state()

# Standard Python entrypoint check: if this script is run directly (not imported),
# start the asyncio event loop and run the main coroutine.
if __name__ == "__main__":
    asyncio.run(main())


