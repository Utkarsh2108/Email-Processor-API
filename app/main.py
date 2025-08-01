from fastapi import FastAPI, HTTPException, status
import groq
import logging
from app.logging_config import setup_logging

# --- SETUP LOGGING FIRST ---
setup_logging()

from app.config import settings
from app.services.email_processor import process_unseen_emails
from app.schemas import ProcessingReport

logger = logging.getLogger(__name__)

# --- Initialize Groq Client at Startup ---
try:
    logger.info("Initializing Groq client...")
    groq_client = groq.Groq(api_key=settings.GROQ_API_KEY)
    logger.info("Groq client initialized successfully.")
except Exception as e:
    logger.error(f"FATAL: Could not initialize Groq client. {e}", exc_info=True)
    groq_client = None

# Create FastAPI app instance
app = FastAPI(
    title="Email Processing API")

@app.post("/process-emails", response_model=ProcessingReport, status_code=status.HTTP_200_OK)
def trigger_email_processing():
    """
    Triggers the process to check for unseen emails, analyze their content
    with AI, and forward them to the extracted recipient address.
    """
    logger.info("Endpoint /process-emails called.")
    
    if not groq_client:
        logger.error("Groq client not available. Aborting request.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq client is not initialized. Please check server logs and API key."
        )

    try:
        logger.info("Starting email processing service.")
        results = process_unseen_emails(settings=settings, groq_client=groq_client)
        
        sent_count = sum(1 for res in results if "successfully" in res.status)
        processed_count = len(results)
        
        logger.info(f"Processing complete. Processed: {processed_count}, Sent: {sent_count}.")
        return ProcessingReport(
            message="Processing complete.",
            processed_count=processed_count,
            sent_count=sent_count,
            results=results
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred in the main endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred: {str(e)}"
        )