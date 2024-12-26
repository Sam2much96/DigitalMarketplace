from http.server import BaseHTTPRequestHandler
from algokit_utils.beta.algorand_client import AlgorandClient
import json




class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Create an Algorand client
        algorand = AlgorandClient.default_local_net()
        
        # Generate a new random account
        creator = algorand.account.random()
        
        # Prepare the response
        response = {
            "message": "Wallet connected.",
            "address": creator.address,
        }
        
        # Send response headers
        # Send response headers with CORS
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')  # Allow all origins
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')  # Allow specific methods
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')  # Allow specific headers
        self.end_headers()
        
        # Write the JSON response
        self.wfile.write(json.dumps(response).encode('utf-8'))
        return


    def do_OPTIONS(self):
        # Handle preflight requests for CORS
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        return
