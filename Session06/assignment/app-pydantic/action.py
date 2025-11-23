import ast
import os
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
from concurrent.futures import TimeoutError
import json, time
from rich.console import Console
from rich.panel import Panel
from pydantic import BaseModel

console = Console()

class ActionResult(BaseModel):
    func_name: str
    content: dict | list | str | None = None
    arguments: dict
    result: str
    status: str
    error: str | None = None

class FunctionCallParamsOutput(BaseModel):
    func_name: str
    arguments: dict

def parse_function_call_params(param_parts: list[str]) -> dict:
    """
    Parses key=value parts from the FUNCTION_CALL format.
    Supports nested keys like input.string=foo and list values like input.int_list=[1,2,3]
    Returns a nested dictionary.
    """
    result = {}

    for part in param_parts:
        if "=" not in part:
            raise ValueError(f"Invalid parameter format (expected key=value): {part}")

        key, value = part.split("=", 1)

        # Try to parse as Python literal (int, float, list, etc.)
        try:
            parsed_value = ast.literal_eval(value)
        except Exception:
            parsed_value = value.strip()

        # Support nested keys like input.string
        keys = key.split(".")
        current = result
        for k in keys[:-1]:
            current = current.setdefault(k, {})
        current[keys[-1]] = parsed_value
    
    console.print(f"Parsed function call parameters: {result}")

    return result

async def perform_action(action: str) -> ActionResult:
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
            
            

                if action.startswith("FUNCTION_CALL:"):
                    _, function_info = action.split(":", 1)
                    parts = [p.strip() for p in function_info.split("|")]
                    func_name, param_parts = parts[0], parts[1:]

                    print(f"\nDEBUG: Raw function info: {function_info}")
                    print(f"DEBUG: Split parts: {parts}")
                    print(f"DEBUG: Function name: {func_name}")
                    print(f"DEBUG: Raw parameters: {param_parts}")

                    try:
                        tool = next((t for t in tools if t.name == func_name), None)
                        if not tool:
                            print(f"DEBUG: Available tools: {[t.name for t in tools]}")
                            raise ValueError(f"Unknown tool: {func_name}")

                        print(f"DEBUG: Found tool: {tool.name}")
                        print(f"DEBUG: Tool schema: {tool.inputSchema}")

                        arguments = parse_function_call_params(param_parts)
                        print(f"DEBUG: Final arguments: {arguments}")
                        print(f"DEBUG: Calling tool {func_name}")

                        result = await session.call_tool(func_name, arguments=arguments)
                        print(f"DEBUG: Raw result: {result}")

                        if hasattr(result, 'content'):
                            print(f"DEBUG: Result has content attribute")
                            if isinstance(result.content, list):
                                action_result = [
                                    item.text if hasattr(item, 'text') else str(item)
                                    for item in result.content
                                ]
                            else:
                                action_result = str(result.content)
                        else:
                            print(f"DEBUG: Result has no content attribute")
                            action_result = str(result)

                        result_str = f"[{', '.join(action_result)}]" if isinstance(action_result, list) else str(action_result)
                        


                        return {
                            "func_name": func_name,
                            "arguments": arguments,
                            "result": result_str,
                            "status": "success",
                        }

                    except Exception as e:
                        print(f"DEBUG: Error details: {str(e)}")
                        print(f"DEBUG: Error type: {type(e)}")
                        import traceback
                        traceback.print_exc()
                        return {
                            "func_name": func_name,
                            "arguments": arguments if 'arguments' in locals() else None,
                            "error": str(e),
                            "status": "error",
                        }


                elif action.startswith("FINAL_ANSWER:"):
                    return {
                            "status": "complete",
                        }
    except Exception as e:
        console.print(f"[red]Error in main execution: {e}[/red]")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        console.print("[yellow]Closing MCP session and connection...[/yellow]")