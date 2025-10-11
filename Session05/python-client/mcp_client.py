from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
from pdb import set_trace

async def main():
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            print("Connected to MCP server")
            import pdb; pdb.set_trace()

            # Get input from user
            text = input("Enter text to reverse: ")

            # Call the reverse_string tool
            result = await session.call_tool(
                "reverse_string",
                arguments={"text": text}
            )

            # Print the result - accessing as object properties
            reversed_text = result.content[0].text

            print(f"Reversed text: {reversed_text}")

            print(50*"+", "DONE", 50*"+")
            print(dir(session))
            result = await session.list_tools()
            print("/n/n/n", result.tools)
            print(50*"+", "DONE", 50*"+")
            
            

if __name__ == "__main__":
    asyncio.run(main()) 