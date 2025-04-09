# Test Suite Documentation

## Overview
This test suite provides comprehensive testing for the Elevate2AI API endpoints, including authentication, AI content generation, media search, and payment functionality.

## Setup

### Prerequisites
- Python 3.8 or higher
- pytest
- pytest-asyncio
- httpx

### Environment Variables
Create a `.env` file in the project root with the following variables:
```
TEST_AUTH_TOKEN=your_supabase_jwt_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_JWT_SECRET=your_supabase_jwt_secret
OPENAI_API_KEY=your_openai_api_key
PEXELS_API_KEY=your_pexels_api_key
UNSPLASH_API_KEY=your_unsplash_api_key
PIXABAY_API_KEY=your_pixabay_api_key
```

## Running Tests

1. Install test dependencies:
```bash
pip install pytest pytest-asyncio httpx
```

2. Run the test suite:
```bash
pytest tests/
```

3. Run specific test files:
```bash
pytest tests/test_auth.py
pytest tests/test_ai.py
pytest tests/test_media.py
pytest tests/test_payment.py
```

## Test Structure

- `conftest.py`: Contains shared fixtures and configurations
- `test_auth.py`: Authentication and user management tests
- `test_ai.py`: AI content generation tests
- `test_media.py`: Media search functionality tests
- `test_payment.py`: Payment status update tests

## Adding New Tests

1. Create a new test file in the `tests/` directory
2. Import necessary fixtures from `conftest.py`
3. Follow the existing test patterns for consistency
4. Use descriptive test names and docstrings
5. Include both positive and negative test cases