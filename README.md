# Receipt & Invoice Intelligent Archiving and Extraction Service

This project is built with FastAPI and leverages LLMs (such as OpenRouter GPT) and Supabase to enable batch uploading, automatic information extraction, OCR recognition, and cloud archiving of receipts/invoices. It supports PDF, image formats, and is ideal for travel reimbursement, financial archiving, and similar scenarios.

## Features

- Batch upload of receipts/invoices (PDF, image formats)
- Automatic conversion of PDF first page to image for unified processing
- Use LLMs to intelligently extract key information (amount, vendor, date, currency, invoice number, address, etc.)
- OCR recognition of image content
- Results are automatically stored in Supabase cloud database
- One-click deployment with Docker


## Environment Variables

Create a `.env` file in the project root with the following content (fill in your actual values):

```
SUPABASE_STORAGE_URL=your_supabase_storage_url
SUPABASE_TABLE_URL=your_supabase_table_api_url
SUPABASE_TOKEN=your_supabase_token
SUPABASE_API_KEY=your_supabase_api_key
SUPABASE_STATUS_TABLE_URL=your_supabase_status_table_api_url
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_URL=your_openrouter_api_url
MODEL=your_model_name (e.g. gpt-3.5-turbo)
```

## Quick Start

### 1. Run Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

The service will listen on port `8000` by default.

### 2. Docker Deployment

#### Build the image

```bash
docker build -t receipt-save .
```

#### Run the container

```bash
docker run --env-file .env -p 8000:8000 receipt-save
```

### 3. Docker Compose

For one-click deployment, use:

```bash
docker-compose up --build
```

The service will be mapped to port `8002` on your host.

## API

### Upload Endpoint

- Path: `POST /webhook/chat`
- Parameters:
  - `chatInput`: text, includes user info, batch info, etc.
  - `files`: multiple file upload, supports PDF and images
- Returns: summary of extraction and archiving results

## Typical Workflow

1. User uploads receipts/invoices and description via form or automation tool
2. Service processes files (PDF to image, OCR, information extraction)
3. Structured data and original images/text are stored in Supabase
4. Returns a summary of the archiving result

