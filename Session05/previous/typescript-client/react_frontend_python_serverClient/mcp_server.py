from mcp.server.fastmcp import FastMCP
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading

# Create MCP server instance
mcp = FastMCP("String Reverser")

@mcp.tool()
async def reverse_string(text: str) -> dict:
    """Reverse a given string"""
    return {
        "content": [
            {
                "type": "text",
                "text": text[::-1]
            }
        ]
    }

# HTTP server to handle browser requests
class RequestHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        text = data.get('text', '')
        
        # Use our MCP tool directly
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(reverse_string(text))
            reversed_text = result['content'][0]['text']
        finally:
            loop.close()
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = json.dumps({'reversed': reversed_text})
        self.wfile.write(response.encode('utf-8'))

def run_http_server():
    server = HTTPServer(('localhost', 8080), RequestHandler)
    print("HTTP Server running on http://localhost:8080")
    server.serve_forever()

if __name__ == "__main__":
    # Start HTTP server in a separate thread
    http_thread = threading.Thread(target=run_http_server)
    http_thread.daemon = True
    http_thread.start()
    
    # Start MCP server in main thread
    print("Starting MCP String Reverser server...")
    mcp.run() 