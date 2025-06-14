import os
import json
import aiohttp
import asyncio
import hashlib
import logging
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv
from pdf2image import convert_from_bytes


# ✅ Load environment variables
load_dotenv()

# ✅ Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ✅ Configuration
SUPABASE_STORAGE_URL = os.getenv("SUPABASE_STORAGE_URL")
SUPABASE_TABLE_URL = os.getenv("SUPABASE_TABLE_URL")
SUPABASE_TOKEN = os.getenv("SUPABASE_TOKEN")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("MODEL")
SUPABASE_STATUS_TABLE_URL = os.getenv("SUPABASE_STATUS_TABLE_URL")
OPENROUTER_URL = os.getenv("OPENROUTER_URL")


def pdf_first_page_to_image_bytes(pdf_bytes):
    """
    Convert the first page of a PDF to JPEG image bytes (used for fileContent).
    """
    images = convert_from_bytes(pdf_bytes, dpi=200, first_page=1, last_page=1)
    if not images:
        raise ValueError("PDF conversion failed, no pages found.")
    buffer = BytesIO()
    images[0].save(buffer, format="JPEG")
    return buffer.getvalue()


# --- Call OpenRouter GPT model to extract fields ---
async def call_openrouter(session, user_input, file_url):
    system_prompt = """
    You are an intelligent business travel reimbursement assistant. You are responsible for saving invoices or receipts and other travel-related information.

    Based on the user's input and uploaded attachments, extract the following information and return it in **JSON format only**, with no extra explanation:

    {
      "category": "...",
      "amount": ...,
      "vendor_name": "...",
      "invoice_date": "...",
      "original_info": "...",
      "currency": ...,
      "address": "...",
      "file_url": "...",
      "invoice_number": "..."
    }

    Notes:

    - `invoice_date`: The invoice or receipt issue date. It must be returned in the format timestamp(`YYYY-MM-DD HH:mm:ss`).
                      Do **not** return vague expressions such as "today", "mañana", or "next Friday".
                      Convert such expressions into a specific date using the system time.
    - `amount`: Please extract the final paid amount from this invoice. Prioritize values explicitly labeled as:"Total Paid", "Total Charged", "Cobrado", "Amount Charged", or similar;If multiple totals exist, prefer the one that includes tax and/or is marked as paid;Avoid using subtotal or pre-tax fields as the final amount.
    - `address`: The invoice or receipt address. For transportation invoices, return in the format `"Origin - Destination"`
    """

    user_prompt = [
        { "type": "text", "text": user_input },
        { "type": "image_url", "image_url": { "url": file_url } }
    ]

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    async with session.post(OPENROUTER_URL, headers=headers, json=payload) as resp:
        if resp.status != 200:
            raise Exception(f"OpenRouter failed: {await resp.text()}")
        result = await resp.json()
        content = result["choices"][0]["message"]["content"]

        try:
            json_part = json.loads(content) if isinstance(content, str) and content.strip().startswith("{") else \
                        json.loads(content.split("```json")[1].split("```")[0].strip())
        except Exception as e:
            raise Exception(f"Failed to extract JSON from LLM output: {content}")

        json_part["file_url"] = file_url
        json_part["original_info"] = user_input
        return json_part


# --- Call OpenRouter GPT model to ocr ---
async def call_openrouter_ocr(session, file_url):
    system_prompt = """
    You are a professional OCR engine. Please extract the text content from the image provided by the user and return it in plain text format.

    ⚠️ Do not include any explanation, comments, or additional information.

    Output requirements:
    - Return only the text content recognized from the image
    - Preserve the original paragraph and line break structure (if any)
    - Do NOT include phrases like “The extracted text is:”
    - If the image is empty or contains no text, return an empty string without explanation

    """

    user_prompt = [
        { "type": "image_url", "image_url": { "url": file_url } }
    ]

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    async with session.post(OPENROUTER_URL, headers=headers, json=payload) as resp:
        if resp.status != 200:
            raise Exception(f"OpenRouter failed: {await resp.text()}")
        result = await resp.json()
        return result["choices"][0]["message"]["content"]


# --- Process a single receipt ---
async def process_receipt(session, item):
    try:
        logger.info("⬆️ Uploading file: %s", item['fileName'])

        timestamp = datetime.utcnow().isoformat()
        storage_url = f"{SUPABASE_STORAGE_URL}{timestamp}_{item['fileName']}"
        headers = {
            "Authorization": f"Bearer {SUPABASE_TOKEN}",
            "x-upsert": "true",
            "Content-Type": item["mimeType"]
        }

        async with session.post(storage_url, data=item["fileContent"], headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"Upload failed: {await resp.text()}")

        file_url = storage_url
        logger.info("✅ File uploaded to: %s", file_url)

        logger.info("🧠 Calling OpenRouter to extract fields...")
        fields = await call_openrouter(session, item["chatInput"], file_url)
        fields["ocr"] = await call_openrouter_ocr(session, file_url)
        logger.debug("📄 Fields returned:\n%s", json.dumps(fields, indent=2))

        hash_input = f"{fields['amount']}|{fields['vendor_name']}|{fields['invoice_date']}|{fields['invoice_number']}"
        fields["hash_id"] = hashlib.md5(hash_input.encode()).hexdigest()
        fields["user_id"] = item["user_id"]

        logger.info("💾 Inserting record into Supabase...")
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_TOKEN}",
            "Content-Type": "application/json"
        }

        async with session.post(SUPABASE_TABLE_URL, json=fields, headers=headers) as resp:
            if resp.status != 201:
                error = await resp.text()
                return {"status": "fail", "error": error, **fields}

        return {"status": "success", **fields}

    except Exception as e:
        logger.error("❌ Error processing receipt: %s", str(e))
        return {"status": "fail", "error": str(e), "vendor_name": item['fileName'], "amount": "?", "invoice_date": "?"}


# --- Save upload status ---
async def save_status(session, user_id, status):
    try:
        logger.info("📝 Saving upload result for user_id=%s", user_id)
        fields = {
            "user_id": user_id,
            "upload_result": status
        }

        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_TOKEN}",
            "Content-Type": "application/json"
        }

        async with session.post(SUPABASE_STATUS_TABLE_URL, json=fields, headers=headers) as resp:
            if resp.status != 201:
                error = await resp.text()
                logger.error("❌ Failed to save status: %s", error)
                return {"status": "fail", "error": error, **fields}

        logger.info("✅ Upload result saved.")
        return {"status": "success", **fields}
    except Exception as e:
        logger.error("❌ Exception in save_status: %s", str(e))
        return {"status": "fail", "error": str(e), "vendor_name": "?", "amount": "?", "invoice_date": "?"}


# --- Main processing function ---
async def main(webhook_data):
    logger.info("🚀 Starting processing of %d receipts", len(webhook_data))
    logger.debug("📦 webhook_data:\n%s", json.dumps(
        [{k: ("<binary>" if k == "fileContent" else v) for k, v in item.items()} for item in webhook_data],
        indent=2
    ))

    async with aiohttp.ClientSession() as session:
        tasks = [process_receipt(session, item) for item in webhook_data]
        results = await asyncio.gather(*tasks)

        success = [r for r in results if r["status"] == "success"]
        fail = [r for r in results if r["status"] == "fail"]

        response_lines = []
        response_lines.append(f"✅ {len(success)} receipts backed up successfully:")
        for r in success:
            response_lines.append(f"- {r['vendor_name']}, {r['currency']}{r['amount']} on {r['invoice_date']}")

        if fail:
            response_lines.append(f"\n❌ {len(fail)} receipts failed to back up:")
            for r in fail:
                response_lines.append(f"- {r['vendor_name']}, {r['amount']} on {r['invoice_date']} – reason: {r['error']}")
        else:
            response_lines.append("\nAll receipts were successfully backed up.")

        status = "\n".join(response_lines)
        await save_status(session, webhook_data[0]["user_id"], status)
        return status