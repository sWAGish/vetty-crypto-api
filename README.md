# Vetty Crypto Market API (Basic Version)

This is a simple Python project that implements a small HTTP REST API
using FastAPI. The API fetches cryptocurrency market data from the public
CoinGecko API.

The code is written in a straightforward style and is meant
for the Vetty Intern – Python API Technical Exercise.

## Features

Version 1.0 of the application provides:

1. GET /coins  
   Lists all coins from CoinGecko (id, symbol, name).  
   Supports pagination using page_num and per_page.

2. GET /categories  
   Lists all coin categories from CoinGecko.  
   Supports pagination using page_num and per_page.

3. GET /markets  
   Lists specific coins by coin_ids (comma separated) and/or category_id.  
   Returns market data against INR (Indian Rupee) and CAD (Canadian Dollar).  
   Supports pagination using page_num and per_page.

Other requirements satisfied:

- The API is protected with a JWT-based authentication mechanism.
- API documentation is automatically available via Swagger UI at /docs.
- The project includes basic unit tests using pytest.

## Project structure

vetty_crypto_api_basic/
- app/
  - __init__.py
  - main.py
- tests/
  - __init__.py
  - test_app.py
- requirements.txt
- README.md

## How to run the project

1. Go to the project folder:

```bash
cd vetty_crypto_api_basic
```

2. (Optional) Create and activate a virtual environment:

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS / Linux: source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the API server:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

- http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs

## Authentication

The application uses a simple JWT token-based authentication.

Default credentials:

- Username: admin
- Password: admin123

1. Get a token:

```bash
curl -X POST "http://127.0.0.1:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

2. Use the token with protected endpoints:

```bash
curl "http://127.0.0.1:8000/coins?page_num=1&per_page=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Running tests

To run the tests:

```bash
pytest
```
