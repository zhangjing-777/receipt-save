Here is the English version of your README:

---

# 🧾 Receipt AI Extractor

An intelligent receipt processing service built with **FastAPI**, **OpenRouter**, and **Supabase**.

## 📦 Features

This project allows users to upload receipts or invoices (images or PDFs), and the system automatically performs the following:

1. **PDF to Image**: Converts the first page of a PDF to a JPEG image;
2. **Upload to Supabase Storage**;
3. **Call OpenRouter LLM to extract receipt fields**:
   
   * Perform OCR to extract raw text from the image
   * Vendor name, amount, date, currency, invoice number, etc.;
   
4. **Save the extracted data to Supabase tables**;
5. **Generate a summary to inform users about the extraction results.**

## 🚀 Quick Start

### 1. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure `.env` file

Example:

```env
SUPABASE_STORAGE_URL=https://xxx.supabase.co/storage/v1/object/public/receipts/
SUPABASE_TABLE_URL=https://xxx.supabase.co/rest/v1/receipt_table
SUPABASE_STATUS_TABLE_URL=https://xxx.supabase.co/rest/v1/receipt_status
SUPABASE_TOKEN=your_supabase_service_role_token
SUPABASE_API_KEY=your_supabase_anon_or_key
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_URL=https://openrouter.ai/api/v1/chat/completions
MODEL=gpt-4o
```

### 3. Run the service

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Visit the documentation page:
[http://localhost:8002/docs](http://localhost:8002/docs)

## 🔁 Webhook Endpoint

### POST `/webhook/chat`

Used to upload receipt files and receive summarized extraction results.

#### Request Parameters (multipart/form-data):

* `chatInput`: Description containing user ID, e.g.:
  `"user 1234 batch uploaded 3 receipts"`
* `files`: One or more image or PDF files.

#### Sample Response:

```json
{
  "summary": "✅ 2 receipts backed up successfully:\n- Uber, $22.5 on 2024-05-12\n- Hotel ABC, $198.0 on 2024-05-10\n\nAll receipts were successfully backed up."
}
```

