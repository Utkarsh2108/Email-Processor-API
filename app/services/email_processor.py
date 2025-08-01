import imaplib
import smtplib
import ssl
import email
from email.header import decode_header
import fitz
import json
import groq
import io
import logging
from PIL import Image
import pytesseract
from bs4 import BeautifulSoup
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from app.config import Settings
from app.schemas import ProcessingResult

logger = logging.getLogger(__name__)

def ocr_from_image_bytes(image_bytes: bytes) -> str:
    """Extracts text from image bytes using Pytesseract."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        logger.error(f"Pytesseract OCR Error: {e}", exc_info=True)
        return f"[Pytesseract OCR Error: {e}]"

def process_unseen_emails(settings: Settings, groq_client: groq.Groq) -> list[ProcessingResult]:
    """
    Connects to an IMAP server, processes unseen emails, and forwards them based on AI analysis.
    """
    results_log = []
    try:
        logger.info(f"Connecting to IMAP server: {settings.IMAP_SERVER}")
        imap = imaplib.IMAP4_SSL(settings.IMAP_SERVER)
        imap.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
        imap.select("INBOX")
        logger.info("IMAP connection successful. Searching for unseen emails.")
        status, messages = imap.search(None, 'UNSEEN')
        
        email_ids = messages[0].split()
        logger.info(f"Found {len(email_ids)} unseen emails.")
        if not email_ids:
            results_log.append(ProcessingResult(status="No unseen emails found."))
            return results_log
    except Exception as e:
        logger.error(f"Failed to connect to IMAP server or search for emails: {e}", exc_info=True)
        results_log.append(ProcessingResult(status="Failed to connect to IMAP server.", details=str(e)))
        return results_log

    for email_id in email_ids:
        log_entry = ProcessingResult(status="Processing started.")
        try:
            _, msg_data = imap.fetch(email_id, "(RFC822)")
            original_message = email.message_from_bytes(msg_data[0][1])

            subject_header = decode_header(original_message['Subject'])
            original_subject = "".join(str(s, c or 'utf-8') if isinstance(s, bytes) else s for s, c in subject_header)
            sender = original_message.get('From')
            log_entry.source_from, log_entry.source_subject = sender, original_subject
            logger.info(f"Processing email ID {email_id.decode()}: From='{sender}', Subject='{original_subject}'")

            # --- A. Extract Content ---
            logger.info("Extracting email body and attachments.")
            full_text_for_analysis = f"Email Subject: {original_subject}\n\n"
            email_body_for_sending = ""
            pdf_to_attach_bytes, pdf_to_attach_filename = None, None
            plain_text_body, html_body_cleaned = "", ""

            for part in original_message.walk():
                content_disposition = str(part.get("Content-Disposition"))
                if "attachment" in content_disposition:
                    if part.get_content_type() == "application/pdf" and part.get_filename():
                        pdf_to_attach_bytes = part.get_payload(decode=True)
                        pdf_to_attach_filename = part.get_filename()
                        logger.info(f"Found PDF attachment: {pdf_to_attach_filename}")
                else:
                    if part.get_content_type() == "text/plain":
                        plain_text_body = part.get_payload(decode=True).decode('utf-8', 'ignore')
                    elif part.get_content_type() == "text/html":
                        html_source = part.get_payload(decode=True).decode('utf-8', 'ignore')
                        soup = BeautifulSoup(html_source, "html.parser")
                        html_body_cleaned = soup.get_text(separator='\n', strip=True)

            email_body_for_sending = plain_text_body or html_body_cleaned
            full_text_for_analysis += f"Email Body:\n{email_body_for_sending}\n\n"

            if pdf_to_attach_bytes:
                with fitz.open(stream=pdf_to_attach_bytes, filetype="pdf") as pdf_doc:
                    pdf_text = "".join(page.get_text() for page in pdf_doc)
                    full_text_for_analysis += f"--- Text from PDF '{pdf_to_attach_filename}' ---\n{pdf_text}\n"

                    logger.info("Searching for images within PDF for OCR.")
                    image_ocr_text = ""
                    for page in pdf_doc:
                        for img_index, img in enumerate(page.get_images(full=True)):
                            base_image = pdf_doc.extract_image(img[0])
                            ocr_result = ocr_from_image_bytes(base_image["image"])
                            if ocr_result.strip():
                                logger.info(f"Found text in image on page {page.page_number + 1} via OCR.")
                                image_ocr_text += f"\n--- OCR Text from Image on Page {page.page_number + 1} ---\n{ocr_result}\n"
                    if image_ocr_text:
                        full_text_for_analysis += image_ocr_text

            # --- B. Analyze with Groq ---
            logger.info("Sending extracted text to Groq for analysis.")
            prompt = f"""
            You are an expert information extraction system. From the text below, which includes content from an email body, PDF text, and OCR from images inside the PDF, extract the recipient's email address and their full physical mailing address.
            Return a single, valid JSON object with two keys: "recipient_email" and "physical_address".
            If a value is not found, use the string "Not Found".

            Here is the content:
            ---
            {full_text_for_analysis}
            ---

            JSON Response:
            """
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",
                temperature=0,
                response_format={"type": "json_object"},
            )
            extracted_data = json.loads(chat_completion.choices[0].message.content)
            recipient_address = extracted_data.get("recipient_email", "Not Found").strip().lower()
            physical_address = extracted_data.get("physical_address", "Not Found").strip()
            
            logger.info(f"Groq analysis result: recipient_email='{recipient_address}', physical_address='{physical_address}'")
            
            # --- C. Compose and Send New Email ---
            if recipient_address and recipient_address != "not found":
                logger.info(f"Recipient found. Composing and sending email to {recipient_address}.")
                new_email = MIMEMultipart()
                new_email['From'] = settings.SENDER_EMAIL
                new_email['To'] = recipient_address
                new_email['Subject'] = original_subject

                # ** START: MODIFICATION **
                final_email_body = email_body_for_sending
                if physical_address and physical_address.lower() != "not found":
                    logger.info("Appending extracted physical address to the email body.")
                    final_email_body += f"\n\n---\nAddress:\n{physical_address}"
                
                new_email.attach(MIMEText(final_email_body, 'plain'))
                # ** END: MODIFICATION **

                if pdf_to_attach_bytes and pdf_to_attach_filename:
                    pdf_part = MIMEApplication(pdf_to_attach_bytes, Name=pdf_to_attach_filename)
                    pdf_part['Content-Disposition'] = f'attachment; filename="{pdf_to_attach_filename}"'
                    new_email.attach(pdf_part)

                context = ssl.create_default_context()
                with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                    server.starttls(context=context)
                    server.login(settings.SENDER_EMAIL, settings.SENDER_PASSWORD)
                    server.sendmail(settings.SENDER_EMAIL, [recipient_address], new_email.as_string())

                imap.store(email_id, '+FLAGS', '\\Seen')
                logger.info(f"Email sent successfully and original email ID {email_id.decode()} marked as Seen.")
                log_entry.status = f"Email sent successfully to {recipient_address}."
            else:
                logger.warning(f"Recipient email not found by AI for email ID {email_id.decode()}. No action taken.")
                log_entry.status = "Recipient email not found by AI. No action taken."

        except Exception as e:
            logger.error(f"Failed to process email ID {email_id.decode()}: {e}", exc_info=True)
            log_entry.status = "Failed to process email."
            log_entry.details = str(e)
        finally:
            results_log.append(log_entry)

    logger.info("Closing IMAP connection.")
    imap.close()
    imap.logout()
    return results_log