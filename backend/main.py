from starlette import responses
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import fitz
import requests
import threading
import time
import typing
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from ai_extractor import extract_invoice_data
from database import (
    create_database,
    save_invoice,
    update_invoice_metadata,
    update_invoice_status,
    get_all_invoices,
    check_invoice_exists,
    get_invoice_by_id,
    delete_invoice_by_id
)

# Load configuration
load_dotenv()

FLOWISE_API_URL = os.getenv("FLOWISE_API_URL", "http://localhost:3000")
FLOWISE_CHAT_FLOW_ID = os.getenv("FLOWISE_CHAT_FLOW_ID", "")
MOCK_ONEDRIVE_DIR = os.getenv("MOCK_ONEDRIVE_DIR", "d:/InvoiceAI/mock_onedrive")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the directory watcher thread on startup
    t = threading.Thread(target=watch_onedrive_folder)
    t.daemon = True
    t.start()
    yield

app = FastAPI(lifespan=lifespan)
create_database()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MOCK_ONEDRIVE_DIR, exist_ok=True)

# CORS middleware for SvelteKit communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        page_text = page.get_text()
        if isinstance(page_text, str):
            text += page_text
    doc.close()
    
    # OCR Fallback: If standard extraction fails to extract meaningful text (e.g. image-only PDF)
    if len(text.strip()) < 50:
        print(f"Standard text extraction yielded only {len(text.strip())} characters. Falling back to Gemini Multimodal OCR...")
        try:
            text = extract_text_via_gemini_ocr(file_path)
        except Exception as ocr_failed:
            print(f"Failed to run Gemini OCR: {ocr_failed}")
            
    return text


def extract_text_via_gemini_ocr(file_path):
    from google import genai
    from google.genai import types
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    doc = fitz.open(file_path)
    ocr_text = ""
    
    for page_num, page in enumerate(doc):
        print(f"OCR Pipeline (Gemini): Processing page {page_num + 1}/{len(doc)}...")
        
        # 1. Render page to image at 150 DPI (highly sufficient for Gemini vision)
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        
        # 2. Call Gemini model to transcribe text
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(
                        data=img_bytes,
                        mime_type="image/png"
                    ),
                    "Transcribe all text from this invoice image accurately. Keep the text layout readable. Do not add any introductory or explanatory text, just output the exact text contents of the document."
                ]
            )
            page_text = response.text or ""
            print(f"OCR Pipeline (Gemini): Successfully extracted {len(page_text)} characters from page {page_num + 1}")
            ocr_text += page_text + "\n"
        except Exception as ocr_err:
            print(f"OCR Pipeline (Gemini) failed on page {page_num + 1}: {ocr_err}")
            # Fall back to standard extraction if Gemini fails
            page_text = page.get_text()
            ocr_text += page_text + "\n"
            
    doc.close()
    return ocr_text


def process_invoice_in_background(invoice_id, file_path, filename):
    try:
        print(f"Background Process: Starting processing for {filename} (ID: {invoice_id})")

        # 1. Extract text from PDF
        extracted_text = extract_text_from_pdf(file_path)

        # 2. Extract metadata via Gemini
        try:
            invoice_data = extract_invoice_data(extracted_text)
            print(f"Background Process: Gemini metadata extracted for {filename}")

        except Exception as e:
            print(f"Background Process: Gemini extraction failed for {filename}: {e}")

            invoice_data = {
                "invoice_number": "Failed to Parse",
                "vendor": "Unknown Vendor",
                "date": "N/A",
                "total_amount": "N/A"
            }

        # 3. Save extracted metadata
        update_invoice_metadata(
            invoice_id,
            invoice_data.get("invoice_number"),
            invoice_data.get("vendor"),
            invoice_data.get("date"),
            invoice_data.get("total_amount"),
            "Ingesting"
        )


        # 4. Ingest into Chroma directly
        try:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100
            )
            chunks = splitter.split_text(extracted_text)

            if not chunks:
                raise ValueError("No text could be extracted from PDF")

            print(f"Split into {len(chunks)} chunks for {filename}")

            embeddings_model = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                google_api_key=os.getenv("GEMINI_API_KEY"),
                output_dimensionality=3072
            )
            vectors = embeddings_model.embed_documents(chunks)

            print(f"Generated {len(vectors)} embeddings for {filename}")

            chroma_client = chromadb.HttpClient(host="localhost", port=8000)
            client_any = typing.cast(typing.Any, chroma_client)
            if hasattr(client_any, "_server") and hasattr(client_any._server, "_session"):
                client_any._server._session.headers["Content-Type"] = "application/json"
            
            try:
                collection = chroma_client.get_collection("invoices")
            except Exception:
                collection = chroma_client.create_collection("invoices")

            collection.add(
                documents=chunks,
                embeddings=typing.cast(typing.Any, vectors),
                ids=[f"{filename}_{i}" for i in range(len(chunks))],
                metadatas=[{"source": filename} for _ in chunks]
            )

            update_invoice_status(invoice_id, "Processed")
            print(f"Successfully stored {len(chunks)} chunks for {filename}")

        except Exception as e:
            update_invoice_status(invoice_id, "Failed (Ingestion Error)")
            print(f"Ingestion error for {filename}: {e}")


    except Exception as e:

        update_invoice_status(
            invoice_id,
            "Failed"
        )

        print(f"Unexpected processing error: {e}")


def watch_onedrive_folder():
    print(f"OneDrive Mock Watcher: Monitoring directory {MOCK_ONEDRIVE_DIR}")
    while True:
        try:
            if os.path.exists(MOCK_ONEDRIVE_DIR):
                for file_name in os.listdir(MOCK_ONEDRIVE_DIR):
                    if file_name.lower().endswith(".pdf"):
                        # Skip if already exists in DB
                        if not check_invoice_exists(file_name):
                            src_path = os.path.join(MOCK_ONEDRIVE_DIR, file_name)
                            dest_path = os.path.join(UPLOAD_FOLDER, file_name)
                            
                            # Wait briefly to ensure the file copy/write is finished
                            initial_size = os.path.getsize(src_path)
                            time.sleep(1.5)
                            if os.path.getsize(src_path) != initial_size:
                                continue
                            
                            print(f"OneDrive Mock Watcher: New PDF detected: {file_name}. Copying & Ingesting...")
                            shutil.copy2(src_path, dest_path)
                            
                            # Save initial status in Database
                            invoice_id = save_invoice(
                                filename=file_name,
                                invoice_number=None,
                                vendor=None,
                                date=None,
                                total_amount=None,
                                file_path=dest_path,
                                status="Ingesting"
                            )
                            
                            # Process in background thread
                            t = threading.Thread(
                                target=process_invoice_in_background,
                                args=(invoice_id, dest_path, file_name)
                            )
                            t.daemon = True
                            t.start()
        except Exception as e:
            print(f"OneDrive Mock Watcher: Error scanning folder: {e}")
        
        time.sleep(5)


# Startup is managed by FastAPI lifespan event handler


@app.get("/")
def home():
    return {
        "status": "healthy",
        "message": "Invoice AI Backend is active",
        "mock_onedrive_dir": MOCK_ONEDRIVE_DIR,
        "flowise_api": FLOWISE_API_URL,
        "chat_flow_configured": bool(FLOWISE_CHAT_FLOW_ID)
    }


@app.get("/api/invoices")
def get_invoices():
    rows = get_all_invoices()
    invoices = []
    for r in rows:
        invoices.append({
            "id": r[0],
            "filename": r[1],
            "invoice_number": r[2] if r[2] else "Processing...",
            "vendor": r[3] if r[3] else "Processing...",
            "date": r[4] if r[4] else "Processing...",
            "total_amount": r[5] if r[5] else "Processing...",
            "file_path": r[6],
            "status": r[7] if len(r) > 7 else "Processed"
        })
    return invoices


@app.delete("/api/invoices/{invoice_id}")
def delete_invoice(invoice_id: int):
    # 1. Get invoice details to find filename and file path
    invoice = get_invoice_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    filename = invoice[1]
    file_path = invoice[6]

    # 2. Delete from SQLite database
    delete_invoice_by_id(invoice_id)

    # 3. Delete physical files from uploads
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Deleted local file: {file_path}")
        except Exception as e:
            print(f"Failed to delete local file {file_path}: {e}")

    # 4. Delete physical file from mock OneDrive (if exists) to avoid auto-re-ingestion
    mock_onedrive_path = os.path.join(MOCK_ONEDRIVE_DIR, filename)
    if os.path.exists(mock_onedrive_path):
        try:
            os.remove(mock_onedrive_path)
            print(f"Deleted OneDrive file: {mock_onedrive_path}")
        except Exception as e:
            print(f"Failed to delete OneDrive file {mock_onedrive_path}: {e}")

    # 5. Delete from Chroma Vector DB
    try:
        chroma_client = chromadb.HttpClient(host="localhost", port=8000)
        client_any = typing.cast(typing.Any, chroma_client)
        if hasattr(client_any, "_server") and hasattr(client_any._server, "_session"):
            client_any._server._session.headers["Content-Type"] = "application/json"
        
        try:
            collection = chroma_client.get_collection("invoices")
            # Delete chunks belonging to this file using the source metadata filter
            collection.delete(where={"source": filename})
            print(f"Successfully deleted Chroma vector index for {filename}")
        except Exception as chroma_err:
            print(f"Chroma collection not found or failed to delete: {chroma_err}")
    except Exception as e:
        print(f"Failed to connect to Chroma client: {e}")

    return {"message": f"Successfully deleted invoice {filename} from database, storage, and Chroma vector index"}



@app.post("/api/chat")
def chat_with_invoice(body: dict):
    question = body.get("question")
    
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    
    # Check if Flowise Chat is configured
    if not FLOWISE_CHAT_FLOW_ID:
        print("No Flowise Chat Flow ID configured. Falling back to direct Gemini chat with local database context.")
        try:
            invoices = get_all_invoices()
            context = "Here is the list of invoices currently extracted and stored in the database:\n\n"
            for r in invoices:
                # Format: filename, invoice_number, vendor, date, total_amount, status
                filename = r[1]
                inv_num = r[2] if r[2] else "N/A"
                vendor = r[3] if r[3] else "N/A"
                date = r[4] if r[4] else "N/A"
                total = r[5] if r[5] else "N/A"
                status = r[7] if len(r) > 7 else "Processed"
                context += f"- Filename: {filename}\n"
                context += f"  Invoice Number: {inv_num}\n"
                context += f"  Vendor: {vendor}\n"
                context += f"  Date: {date}\n"
                context += f"  Total Amount: {total}\n"
                context += f"  Sync Status: {status}\n\n"

            prompt = f"""You are "InvoiceAI Chatbot", an advanced conversational finance assistant.
Your task is to answer natural language queries about the invoices stored in the company database.

Current Database Context:
{context}

Guidelines:
1. Provide accurate answers based ONLY on the invoice database context above.
2. If the user asks about invoices that are not in the context, politely state you do not have records for those invoices.
3. Be professional, direct, and summarize financial data clearly (e.g. sum totals, compare dates, or list vendors if asked).
4. Do not mention Flowise or SQLite. Act as a direct finance intelligence system.

User Question: {question}
Answer:"""

            from google import genai
            # Initialize Client (uses GEMINI_API_KEY from environment)
            client = genai.Client()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return {"text": (response.text or "").strip()}
        except Exception as e:
            print(f"Fallback chat execution failed: {e}")
            raise HTTPException(status_code=500, detail=f"Gemini Chat Fallback failed: {str(e)}")

    # Forward to Flowise Chat Flow
    flowise_url = f"{FLOWISE_API_URL}/api/v1/prediction/{FLOWISE_CHAT_FLOW_ID}"
    try:
        # Flowise standard prediction endpoint body
        payload = {"question": question}
        if body.get("history"):
            # Map 'role' to 'type' for Flowise compatibility
            payload["history"] = [
                {
                    "type": h.get("type") or h.get("role") or "userMessage",
                    "message": h.get("message") or h.get("text") or ""
                }
                for h in body.get("history")
            ]
            
        response = requests.post(flowise_url, json=payload, timeout=60)
        
        if response.status_code in (200, 201):
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Flowise responded with: {response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Flowise Chat: {str(e)}")


@app.post("/upload-invoice")
def upload_invoice(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing")
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    # Save uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Save initial state in DB
    invoice_id = save_invoice(
        filename=file.filename,
        invoice_number=None,
        vendor=None,
        date=None,
        total_amount=None,
        file_path=file_path,
        status="Ingesting"
    )

    # Add processing to background tasks
    background_tasks.add_task(
        process_invoice_in_background,
        invoice_id,
        file_path,
        file.filename
    )

    return {
        "id": invoice_id,
        "filename": file.filename,
        "status": "Ingesting",
        "message": "Invoice uploaded and queued for ingestion and extraction"
    }


@app.post("/api/sync-onedrive")
def force_sync_onedrive(background_tasks: BackgroundTasks):
    """
    Manually triggers a scan of the OneDrive directory.
    """
    scanned_count = 0
    if os.path.exists(MOCK_ONEDRIVE_DIR):
        for file_name in os.listdir(MOCK_ONEDRIVE_DIR):
            if file_name.lower().endswith(".pdf") and not check_invoice_exists(file_name):
                src_path = os.path.join(MOCK_ONEDRIVE_DIR, file_name)
                dest_path = os.path.join(UPLOAD_FOLDER, file_name)
                
                shutil.copy2(src_path, dest_path)
                
                invoice_id = save_invoice(
                    filename=file_name,
                    invoice_number=None,
                    vendor=None,
                    date=None,
                    total_amount=None,
                    file_path=dest_path,
                    status="Ingesting"
                )
                
                background_tasks.add_task(
                    process_invoice_in_background,
                    invoice_id,
                    dest_path,
                    file_name
                )
                scanned_count += 1

    return {
        "message": f"Scan completed. Queued {scanned_count} new invoices for sync."
    }
