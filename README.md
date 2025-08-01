# Email Processor API

This FastAPI application automates the processing of emails. It reads unseen emails from an IMAP server, extracts text from the body and PDF attachments (including OCR on images within PDFs using **Tesseract**), uses the Groq API to find a recipient's email address, and forwards the original email to that address.

## Features

- **IMAP Integration**: Reads unseen emails from a specified inbox.
- **Advanced Content Extraction**: Parses text from email bodies and PDFs.
- **Tesseract OCR**: Uses the powerful Tesseract engine to extract text from images inside PDFs.
- **AI-Powered Analysis**: Leverages Groq (Llama 3) to intelligently extract recipient information.
- **API-based**: All logic is triggered via a secure API endpoint.
- **Secure**: Uses environment variables for all credentials—no hardcoded secrets.

## 🚀 Setup and Installation

### Prerequisites

- Python 3.8+
- A Gmail account with an **App Password**. You can generate one here: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
- A Groq API Key.
- **The Tesseract-OCR Engine**: This is a separate program that must be installed on your system.

### Steps

1.  **Install the Tesseract-OCR Engine:**

    -   **Windows**: Download and run the installer from the [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) page. During installation, make sure to check the option to add Tesseract to your system PATH.
    -   **macOS**: Use Homebrew: `brew install tesseract`
    -   **Debian/Ubuntu**: Use apt: `sudo apt update && sudo apt install tesseract-ocr`

2.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd email-processor-api
    ```

3.  **Create a Python virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

4.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Configure your environment variables:**
    Copy the example `.env` file:
    ```bash
    cp .env.example .env
    ```
    Now, open the `.env` file and fill in your actual credentials. If you installed Tesseract to a custom location on Windows, you can add the `TESSERACT_CMD_PATH` variable.

6.  **Run the application:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The server will be running at `http://127.0.0.1:8000`.

## ⚙️ API Usage

To trigger the email processing, send a `POST` request to the `/process-emails` endpoint.

You can use the interactive API documentation provided by FastAPI at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).