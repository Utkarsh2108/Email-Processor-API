# app/main.py

import logging
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
import groq

# --- Local Imports ---
from app.logging_config import setup_logging
from app.config import settings
from app.services.email_processor import process_unseen_emails
from app.schemas.app_schemas import ProcessingReport
from app.auth import (
    get_current_user,
    get_current_admin_user,
    create_access_token,
    verify_password,
    get_password_hash
)
from app.schemas.user_schemas import UserResponse, Token, UserCreate, UserLogin # <-- CORRECTED LINE
from app.database import get_db, Base, engine
from app.models.users import User

# --- SETUP LOGGING & DATABASE ---
setup_logging()
logger = logging.getLogger(__name__)
# This creates the database tables if they don't exist on startup
Base.metadata.create_all(bind=engine)

# --- Initialize Groq Client ---
try:
    logger.info("Initializing Groq client...")
    groq_client = groq.Groq(api_key=settings.GROQ_API_KEY)
    logger.info("Groq client initialized successfully.")
except Exception as e:
    logger.error(f"FATAL: Could not initialize Groq client. {e}", exc_info=True)
    groq_client = None

# --- Create FastAPI app instance ---
app = FastAPI(
    title="Email Processing API with Authentication"
)


# --- AUTHENTICATION ENDPOINTS ---
@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Endpoint to register a new user.
    """
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token", response_model=Token)
async def login_for_access_token(
    user_credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticates a user with email and password and returns a JWT access token.
    """
    user = db.query(User).filter(User.email == user_credentials.email).first()
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "role": user.role.value},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}



# --- PROTECTED APPLICATION ENDPOINTS ---

@app.post("/process-emails", response_model=ProcessingReport, status_code=status.HTTP_200_OK)
def trigger_email_processing(current_user: UserResponse = Depends(get_current_user)):
    """
    Triggers the email processing service. Requires user authentication.
    """
    logger.info(f"Endpoint /process-emails called by user: {current_user.email}")

    if not groq_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq client is not initialized."
        )

    try:
        results = process_unseen_emails(settings=settings, groq_client=groq_client)
        sent_count = sum(1 for res in results if "successfully" in res.status)
        return ProcessingReport(
            message=f"Processing complete for user {current_user.email}.",
            processed_count=len(results),
            sent_count=sent_count,
            results=results
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred in the main endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/admin/dashboard", status_code=status.HTTP_200_OK)
def get_admin_dashboard(current_admin: UserResponse = Depends(get_current_admin_user)):
    """
    An example of an admin-only endpoint.
    """
    return {"message": f"Welcome to the admin dashboard, {current_admin.email}!"}