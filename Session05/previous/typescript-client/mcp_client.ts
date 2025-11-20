import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import * as readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';

async function main() {
    // Create transport to communicate with Python MCP server
    const transport = new StdioClientTransport({
        command: "python",
        args: ["mcp_server.py"]
    });

    // Create MCP client
    const client = new Client(
        {
            name: "string-reverser-client",
            version: "1.0.0"
        },
        {
            capabilities: {
                tools: {}
            }
        }
    );

    // Connect to the server
    await client.connect(transport);
    console.log("Connected to MCP server");

    // Create readline interface
    const rl = readline.createInterface({ input, output });

    // Get input from user
    const text = await rl.question('Enter text to reverse: ');
    rl.close();

    // Call the reverse_string tool
    const result = await client.callTool({
        name: "reverse_string",
        arguments: { text }
    }) as CallToolResult;

    // Print the result
    console.log(`Reversed text: ${result.content[0].text}`);
}

main().catch(console.error); 