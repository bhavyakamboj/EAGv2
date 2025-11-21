# Flask Backend API for Car Price Calculator

This is a Flask backend API that processes natural language queries about car prices using the Gemini AI model with an agentic loop.

## Features

- **Agentic Loop**: Uses Gemini 2.0 Flash to understand queries and iteratively call functions
- **Price Calculation**: Calculates on-road prices for Tata Harrier vehicles
- **REST API**: Simple POST endpoint for processing queries
- **JSON Response**: Returns structured JSON responses

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the `app` directory (or parent directory) with your Gemini API key:

```
GEMINI_API_KEY=your_api_key_here
```

### 3. Run the Application

```bash
python app.py
```

The API will start on `http://localhost:5000`

## API Endpoints

### POST `/v1/chat`

Process a natural language query and get the result.

**Request Body:**
```json
{
  "query": "Calculate the on road price of all cars with brand as tata, model as harrier, fuel type as diesel, transmission as automatic in DELHI with ex_showroom_price greater than 2500000."
}
```

**Response:**
```json
{
  "result": "..."
}
```

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

## Supported Functions

The agent has access to the following functions:

1. **variants(brand, model, fuel_type, transmission)** - Get available variants for a car
2. **ex_showroom_price(brand, model, fuel_type, transmission, variant)** - Get the ex-showroom price
3. **road_tax_multiplier(state, ex_showroom_price, fuel_type)** - Calculate road tax multiplier
4. **on_road_price(ex_showroom_price, road_tax_multiplier)** - Calculate final on-road price

## Example Usage

```bash
curl -X POST http://localhost:5000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Calculate the on road price of all cars with brand as tata, model as harrier, fuel type as diesel, transmission as automatic in DELHI with ex_showroom_price greater than 2500000."
  }'
```

## How It Works

1. The client sends a query to the `/v1/chat` endpoint
2. The `process_query()` function initiates an agentic loop with Gemini
3. The agent analyzes the query and decides which functions to call
4. Functions are executed and results are fed back to the agent
5. The agent continues until it has enough information to provide a FINAL_ANSWER
6. The final answer is returned as JSON to the client

## File Structure

```
app/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## System prompt

```
You are a math agent solving problems in iterations. Respond with EXACTLY ONE of these formats:\n1. FUNCTION_CALL: python_function_name|input\n2. FINAL_ANSWER: {answer_dict}\n\ninput is a string of comma separated values.\n\nAvailable functions:\n1. variants(brand, model, fuel_type, transmission) - Returns list of variant names\n2. ex_showroom_price(brand, model, fuel_type, transmission, variant) - Returns the ex-showroom price as integer\n3. road_tax_multiplier(state, ex_showroom_price, fuel_type) - Returns the road tax multiplier as float\n4. on_road_price(ex_showroom_price, road_tax_multiplier) - Returns the on-road price as integer\n\nDO NOT include multiple responses. Give ONE response at a time.
```