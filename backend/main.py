"""
Demucs Audio Separation API with User Authentication and Credit System

REST API for uploading audio files, processing them with Demucs,
and downloading the separated tracks. Includes user authentication,
credit management, and job tracking.
"""

import asyncio
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

try:
    from square import Square
    from square.environment import SquareEnvironment
    from square.core.api_error import ApiError
    SQUARE_AVAILABLE = True
except ImportError:
    SQUARE_AVAILABLE = False
    Square = None
    SquareEnvironment = None
    ApiError = None

from database import get_db, engine, Base
from models import User, Job, JobStatus, CreditTransaction
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Directories
UPLOAD_DIR = Path("/app/uploads")
TEMP_DIR = Path("/app/temp")
COMPLETED_DIR = Path("/app/completed")

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
COMPLETED_DIR.mkdir(exist_ok=True)

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Demucs Audio Separation API",
    description="Upload audio files and separate them into individual tracks with user authentication and credit system",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://localhost",
        "https://muxminus.com",
        "https://www.muxminus.com",
        "*"  # Fallback for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend demo audio
FRONTEND_DIR = Path("/app/frontend")
if FRONTEND_DIR.exists():
    app.mount("/demo", StaticFiles(directory=str(FRONTEND_DIR / "demo")), name="demo")
    logger.info(f"Mounted frontend demo directory at /demo")

# Credit cost per job
CREDIT_COST_PER_JOB = 1.0

# Square API Configuration
SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN", "")
SQUARE_ENVIRONMENT = os.getenv("SQUARE_ENVIRONMENT", "sandbox")  # 'sandbox' or 'production'
SQUARE_APPLICATION_ID = os.getenv("SQUARE_APPLICATION_ID", "")
SQUARE_LOCATION_ID = os.getenv("SQUARE_LOCATION_ID", "")

# Initialize Square client
square_client = None
if SQUARE_ACCESS_TOKEN and SQUARE_AVAILABLE and Square:
    # Map environment string to Square Environment enum
    env = SquareEnvironment.SANDBOX if SQUARE_ENVIRONMENT.lower() == "sandbox" else SquareEnvironment.PRODUCTION
    square_client = Square(
        environment=env,
        token=SQUARE_ACCESS_TOKEN,
    )
    logger.info(f"Square client initialized in {SQUARE_ENVIRONMENT} mode")
elif not SQUARE_AVAILABLE:
    logger.warning("Square SDK not available. Install 'squareup' package to enable payment processing.")
else:
    logger.warning("Square credentials not configured. Payment processing will not be available.")


# ============================================================================
# Pydantic Models (Request/Response)
# ============================================================================

class UserRegister(BaseModel):
    """User registration request."""
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    email: str
    credits: float


class UserProfile(BaseModel):
    """User profile information."""
    id: int
    email: str
    username: str
    credits: float
    created_at: datetime


class JobResponse(BaseModel):
    """Job information response."""
    id: str
    filename: str
    model: str
    status: str
    error_message: Optional[str] = None
    cost: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None


class CreditPurchase(BaseModel):
    """Credit purchase request."""
    amount: float
    price: float
    payment_nonce: str  # Square payment token from frontend
    

class SquareConfigResponse(BaseModel):
    """Square configuration for frontend."""
    application_id: str
    location_id: str
    environment: str


# ============================================================================
# Background Processing
# ============================================================================

async def process_audio_file(job_id: str, input_path: Path, db_session_maker):
    """
    Background task to process audio file with Demucs.
    
    Args:
        job_id: Unique job identifier
        input_path: Path to uploaded audio file
        db_session_maker: Database session factory
    """
    db = db_session_maker()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in database")
            return
        
        # Update status to processing
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        db.commit()
        logger.info(f"Starting demucs processing for job {job_id}")
        
        # Create output directory for this job
        output_dir = TEMP_DIR / job_id
        output_dir.mkdir(exist_ok=True)
        
        # Build demucs command based on stem count
        cmd = [
            "demucs",
            "--out", str(output_dir),
            "--mp3",
            "--mp3-bitrate", "320"
        ]
        
        # Add two-stem mode if requested
        if job.stem_count == 2 and job.two_stem_type:
            cmd.append(f"--two-stems={job.two_stem_type}")
            logger.info(f"Using 2-stem mode: {job.two_stem_type}")
        
        # Add model if specified
        if job.model and job.model != "htdemucs":
            cmd.extend(["-n", job.model])
        
        cmd.append(str(input_path))
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"Demucs failed for job {job_id}: {error_msg}")
            job.status = JobStatus.FAILED
            job.error_message = error_msg
            job.completed_at = datetime.utcnow()
            db.commit()
            return
        
        logger.info(f"Demucs processing completed for job {job_id}")
        
        # Find the output directory
        demucs_output = output_dir / "htdemucs"
        if not demucs_output.exists():
            raise FileNotFoundError(f"Demucs output directory not found: {demucs_output}")
        
        # Get the first subdirectory (song name)
        song_dirs = list(demucs_output.iterdir())
        if not song_dirs:
            raise FileNotFoundError("No output files generated by Demucs")
        
        song_dir = song_dirs[0]
        
        # Create ZIP file
        zip_filename = f"{job_id}.zip"
        zip_path = COMPLETED_DIR / zip_filename
        
        logger.info(f"Creating ZIP archive for job {job_id}")
        shutil.make_archive(
            str(zip_path.with_suffix('')),
            'zip',
            song_dir
        )
        
        # Clean up temp files
        shutil.rmtree(output_dir)
        input_path.unlink()
        
        # Update job status
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.exception(f"Error processing job {job_id}")
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
        
        # Clean up on error
        try:
            if input_path.exists():
                input_path.unlink()
            temp_output = TEMP_DIR / job_id
            if temp_output.exists():
                shutil.rmtree(temp_output)
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")
    finally:
        db.close()


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    New users receive 3 free credits to try the service.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create new user with 3 free credits
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        credits=3.0  # Free trial credits
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Log the free credits
    transaction = CreditTransaction(
        user_id=new_user.id,
        amount=3.0,
        balance_after=3.0,
        description="Welcome bonus - 3 free credits",
        reference="registration"
    )
    db.add(transaction)
    db.commit()
    
    logger.info(f"New user registered: {user_data.email}")
    
    # Create access token (JWT spec requires 'sub' to be a string)
    access_token = create_access_token(data={"sub": str(new_user.id)})
    
    return TokenResponse(
        access_token=access_token,
        user_id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        credits=new_user.credits
    )


@app.post("/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )
    
    # Create access token (JWT spec requires 'sub' to be a string)
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        email=user.email,
        credits=user.credits
    )


@app.get("/auth/me", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        credits=current_user.credits,
        created_at=current_user.created_at
    )


# ============================================================================
# Credit Management
# ============================================================================

@app.get("/credits/square-config")
async def get_square_config():
    """Get Square configuration for frontend."""
    if not square_client or not SQUARE_APPLICATION_ID:
        raise HTTPException(status_code=503, detail="Payment processing not configured")
    
    return SquareConfigResponse(
        application_id=SQUARE_APPLICATION_ID,
        location_id=SQUARE_LOCATION_ID,
        environment=SQUARE_ENVIRONMENT
    )


@app.post("/credits/purchase")
async def purchase_credits(
    purchase: CreditPurchase,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Purchase credits with Square payment processing.
    """
    if not square_client:
        raise HTTPException(status_code=503, detail="Payment processing not configured")
    
    if purchase.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    if purchase.price <= 0:
        raise HTTPException(status_code=400, detail="Price must be positive")
    
    try:
        # Create Square payment
        idempotency_key = str(uuid.uuid4())
        
        # Call Square payments API (synchronous as per quickstart)
        response = square_client.payments.create(
            source_id=purchase.payment_nonce,
            idempotency_key=idempotency_key,
            amount_money={
                "amount": int(purchase.price * 100),  # Convert dollars to cents
                "currency": "USD"
            },
            location_id=SQUARE_LOCATION_ID,
            note=f"Mux Minus Credit Purchase - {purchase.amount} credits",
            buyer_email_address=current_user.email,
        )
        
        # Payment successful - extract payment ID from response
        payment_id = response.payment.id
        
        # Update user credits
        current_user.credits += purchase.amount
        db.commit()
        
        # Log transaction
        transaction = CreditTransaction(
            user_id=current_user.id,
            amount=purchase.amount,
            balance_after=current_user.credits,
            description=f"Credit purchase - {purchase.amount} credits for ${purchase.price:.2f}",
            reference=payment_id
        )
        db.add(transaction)
        db.commit()
        
        logger.info(f"User {current_user.id} purchased {purchase.amount} credits for ${purchase.price:.2f}. Payment ID: {payment_id}")
        
        return {
            "message": "Credits purchased successfully",
            "credits": current_user.credits,
            "amount_added": purchase.amount,
            "payment_id": payment_id
        }
    
    except ApiError as e:
        # Handle Square API errors as per quickstart docs
        error_details = ", ".join([f"{error.category}: {error.code} - {error.detail}" for error in e.errors])
        logger.error(f"Square API error for user {current_user.id}: {error_details}")
        raise HTTPException(status_code=400, detail=f"Payment failed: {error_details}")
    except Exception as e:
        logger.error(f"Error processing payment for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment processing error: {str(e)}")


@app.get("/credits/balance")
async def get_credit_balance(current_user: User = Depends(get_current_user)):
    """Get current credit balance."""
    return {
        "credits": current_user.credits,
        "user_id": current_user.id
    }


@app.get("/credits/history")
async def get_credit_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get credit transaction history."""
    transactions = db.query(CreditTransaction)\
        .filter(CreditTransaction.user_id == current_user.id)\
        .order_by(CreditTransaction.created_at.desc())\
        .limit(50)\
        .all()
    
    return {"transactions": transactions}


# ============================================================================
# Job Management (Audio Processing)
# ============================================================================

@app.post("/upload", response_model=JobResponse)
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model: str = Form("htdemucs"),
    stem_count: int = Form(4),
    two_stem_type: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload an audio file for processing.
    
    Requires authentication. Costs 1 credit per job.
    
    Args:
        file: Audio file to process
        model: Demucs model to use (htdemucs, htdemucs_ft, htdemucs_6s)
        stem_count: Number of stems (2 or 4)
        two_stem_type: For 2-stem mode, which stem to isolate (vocals, drums, bass)
    """
    # Check if user has enough credits
    if current_user.credits < CREDIT_COST_PER_JOB:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. You need {CREDIT_COST_PER_JOB} credit(s). Current balance: {current_user.credits}"
        )
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    allowed_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_path = UPLOAD_DIR / f"{job_id}{file_ext}"
    
    try:
        async with aiofiles.open(upload_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"File uploaded: {file.filename} -> {upload_path}")
        
    except Exception as e:
        logger.exception("Error saving uploaded file")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Deduct credits
    current_user.credits -= CREDIT_COST_PER_JOB
    db.commit()
    
    # Log credit usage
    transaction = CreditTransaction(
        user_id=current_user.id,
        amount=-CREDIT_COST_PER_JOB,
        balance_after=current_user.credits,
        description=f"Audio separation job",
        reference=job_id
    )
    db.add(transaction)
    
    # Create job in database
    job = Job(
        id=job_id,
        user_id=current_user.id,
        filename=file.filename,
        model=model,
        stem_count=stem_count,
        two_stem_type=two_stem_type if stem_count == 2 else None,
        status=JobStatus.PENDING,
        cost=CREDIT_COST_PER_JOB
    )
    db.add(job)
    db.commit()
    
    logger.info(f"Job {job_id} created for user {current_user.id}: model={model}, stem_count={stem_count}, two_stem_type={two_stem_type}")
    
    # Start background processing
    from database import SessionLocal
    background_tasks.add_task(process_audio_file, job_id, upload_path, SessionLocal)
    
    return JobResponse(
        id=job.id,
        filename=job.filename,
        model=job.model,
        status=job.status.value,
        cost=job.cost,
        created_at=job.created_at
    )


@app.get("/status/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the status of a processing job."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    download_url = f"/download/{job_id}" if job.status == JobStatus.COMPLETED else None
    
    return JobResponse(
        id=job.id,
        filename=job.filename,
        model=job.model,
        status=job.status.value,
        error_message=job.error_message,
        cost=job.cost,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        download_url=download_url
    )


@app.get("/download/{job_id}")
async def download_result(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download the processed audio tracks as a ZIP file."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Current status: {job.status.value}"
        )
    
    zip_path = COMPLETED_DIR / f"{job_id}.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    return FileResponse(
        path=zip_path,
        filename=f"{Path(job.filename).stem}_separated.zip",
        media_type="application/zip"
    )


@app.get("/stems/{job_id}")
async def get_stems_list(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of available stems for a completed job."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Current status: {job.status.value}"
        )
    
    zip_path = COMPLETED_DIR / f"{job_id}.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    # Extract stem names from the zip file
    import zipfile
    stems = []
    with zipfile.ZipFile(zip_path, 'r') as zip_file:
        for filename in zip_file.namelist():
            if filename.endswith('.mp3'):
                stem_name = Path(filename).stem
                stems.append({
                    "name": stem_name,
                    "filename": filename,
                    "url": f"/stems/{job_id}/{stem_name}"
                })
    
    return {"job_id": job_id, "stems": stems}


@app.get("/stems/{job_id}/{stem_name}")
async def stream_stem(
    job_id: str,
    stem_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stream an individual stem audio file."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Current status: {job.status.value}"
        )
    
    zip_path = COMPLETED_DIR / f"{job_id}.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    # Extract the specific stem from the zip file to a temp location
    import zipfile
    import tempfile
    
    with zipfile.ZipFile(zip_path, 'r') as zip_file:
        # Find the file matching the stem name
        matching_file = None
        for filename in zip_file.namelist():
            if Path(filename).stem == stem_name and filename.endswith('.mp3'):
                matching_file = filename
                break
        
        if not matching_file:
            raise HTTPException(status_code=404, detail=f"Stem '{stem_name}' not found")
        
        # Extract to temp file
        temp_dir = Path(tempfile.gettempdir()) / "muxminus_stems"
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / f"{job_id}_{stem_name}.mp3"
        
        # Only extract if not already cached
        if not temp_file.exists():
            with zip_file.open(matching_file) as source:
                with open(temp_file, 'wb') as target:
                    shutil.copyfileobj(source, target)
    
    return FileResponse(
        path=temp_file,
        filename=f"{stem_name}.mp3",
        media_type="audio/mpeg"
    )


@app.delete("/job/{job_id}")
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a job and its associated files."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete files
    zip_path = COMPLETED_DIR / f"{job_id}.zip"
    if zip_path.exists():
        zip_path.unlink()
    
    # Delete from database
    db.delete(job)
    db.commit()
    
    logger.info(f"Job {job_id} deleted by user {current_user.id}")
    
    return {"message": "Job deleted successfully"}


@app.get("/jobs")
async def list_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all jobs for the current user."""
    jobs = db.query(Job)\
        .filter(Job.user_id == current_user.id)\
        .order_by(Job.created_at.desc())\
        .limit(50)\
        .all()
    
    return {
        "jobs": [
            JobResponse(
                id=job.id,
                filename=job.filename,
                model=job.model,
                status=job.status.value,
                error_message=job.error_message,
                cost=job.cost,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                download_url=f"/download/{job.id}" if job.status == JobStatus.COMPLETED else None
            )
            for job in jobs
        ]
    }


# ============================================================================
# General Endpoints
# ============================================================================

@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "service": "Mux Minus Audio Separation API",
        "status": "running",
        "version": "2.0.0",
        "features": ["authentication", "credit_system", "job_tracking"]
    }


# ============================================================================
# Frontend Routes
# ============================================================================

@app.get("/app.js")
async def serve_js():
    """Serve the main JavaScript file."""
    try:
        file_location = Path("/app/frontend/app.js")
        if file_location.exists():
            return FileResponse(file_location)
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Error serving JS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/styles.css")
async def serve_css():
    """Serve the main CSS file."""
    try:
        file_location = Path("/app/frontend/styles.css")
        if file_location.exists():
            return FileResponse(file_location)
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Error serving CSS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend application."""
    try:
        frontend_path = Path("/app/frontend/index.html")
        logger.info(f"Attempting to serve frontend from: {frontend_path}")
        logger.info(f"File exists: {frontend_path.exists()}")
        
        if frontend_path.exists():
            with open(frontend_path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"Successfully read {len(content)} characters")
                return HTMLResponse(content=content)
        else:
            logger.error(f"Frontend file not found at {frontend_path}")
            raise HTTPException(status_code=404, detail="Frontend not found")
    except Exception as e:
        logger.error(f"Error serving frontend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Catch-all route for SPA routing - must be last!
# This allows refreshing on any page like /dashboard, /upload, etc.
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def catch_all(full_path: str):
    """Catch-all route to serve index.html for SPA routing."""
    # Skip if this looks like an API call or static file
    if full_path.startswith(("api/", "auth/", "upload", "jobs", "status/", "download/", 
                             "stems/", "credits/", "demo/")) or "." in full_path:
        raise HTTPException(status_code=404, detail="Not Found")
    
    # Serve index.html for all other routes (SPA routing)
    try:
        frontend_path = Path("/app/frontend/index.html")
        if frontend_path.exists():
            with open(frontend_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        raise HTTPException(status_code=404, detail="Frontend not found")
    except Exception as e:
        logger.error(f"Error in catch-all route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
