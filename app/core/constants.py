"""
Constants used across the Mux Minus application.
"""

# File size limits (in bytes)
MAX_UPLOAD_SIZE_SEPARATION = 100 * 1024 * 1024  # 100MB for separation jobs
MAX_UPLOAD_SIZE_TRANSCRIPTION = 5 * 1024 * 1024 * 1024  # 5GB for transcription jobs

# Credit costs by job type
CREDIT_COST_SEPARATION = 1
CREDIT_COST_TRANSCRIPTION = 1
CREDIT_COST_LYRICS_PIPELINE = 2  # Demucs + Whisper
