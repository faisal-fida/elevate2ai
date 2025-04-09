# Elevate2AI

A FastAPI application with Supabase integration.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure environment variables:
   - Create a `.env` file in the root directory
   - Add the following variables (replace with your actual values):
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   SUPABASE_JWT_SECRET=your_supabase_jwt_secret
   ENVIRONMENT=development
   ```

## Running the Application

Use the provided `run.py` script to start the application:

```
python run.py
```

The server will start at http://0.0.0.0:8000

## API Documentation

Once the server is running, you can access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc