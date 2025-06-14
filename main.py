import re
import logging
from fastapi import FastAPI, UploadFile, File, Form
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import mimetypes
from app import main, pdf_first_page_to_image_bytes

# ✅ Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS if cross-origin issues occur
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/webhook/chat")
async def receive_receipt(
    chatInput: str = Form(...),
    files: List[UploadFile] = File(...)
):
    webhook_data = []

    logger.info("📥 Received chatInput: %s", chatInput)
    logger.info("📎 Number of uploaded files: %d", len(files))

    # Extract user_id from chatInput, e.g. "user 12345 batch uploaded 3 receipts"
    match = re.search(r"user (\S+?) batch uploaded", chatInput)
    user_id = match.group(1) if match else "unknown"
    logger.info("👤 Extracted user_id: %s", user_id)

    for idx, upload in enumerate(files):
        file_bytes = await upload.read()

        file_name = upload.filename
        mime_type = upload.content_type or mimetypes.guess_type(file_name)[0] or "application/octet-stream"

        if file_name.lower().endswith(".pdf"):
            logger.info("📄 Converting PDF to image: %s", file_name)
            file_bytes = pdf_first_page_to_image_bytes(file_bytes)
            file_name = file_name.replace(".pdf", ".jpg")
            mime_type = "image/jpeg"

        webhook_data.append({
            "fileName": file_name,
            "mimeType": mime_type,
            "fileContent": file_bytes,
            "chatInput": chatInput,
            "sessionId": f"n8n-session-{idx}",
            "user_id": user_id
        })

    logger.info("🚀 Passing data to main()")
    result_summary = await main(webhook_data)

    logger.info("✅ Summary returned from main():\n%s", result_summary)
    return {"summary": result_summary}