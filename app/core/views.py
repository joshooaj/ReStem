from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.conf import settings
import os
import uuid
from typing import Optional

from .forms import UserRegistrationForm, UserLoginForm, ProfileUpdateForm, PasswordChangeForm, JobCreateForm
from .models import Job, CreditPackage, JobStatus, SiteSettings


def health_check(request: HttpRequest) -> JsonResponse:
    """Health check endpoint for container orchestration."""
    return JsonResponse({"status": "healthy"})


def landing_page(request: HttpRequest) -> HttpResponse:
    """
    Public landing page with product information and demo.
    
    Redirects authenticated users to their dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/landing.html', {
        'default_credits': SiteSettings.get_default_credits(),
    })


def register(request: HttpRequest) -> HttpResponse:
    """
    User registration view.
    
    Creates a new user account with 3 free credits.
    Redirects to dashboard on successful registration.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to Mux Minus! You have {user.credits} free credits to get started.')
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'core/register.html', {
        'form': form,
        'default_credits': SiteSettings.get_default_credits(),
    })


def user_login(request: HttpRequest) -> HttpResponse:
    """
    User login view.
    
    Authenticates user and redirects to 'next' URL or dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
    else:
        form = UserLoginForm()
    
    return render(request, 'core/login.html', {'form': form})


@login_required
def user_logout(request: HttpRequest) -> HttpResponse:
    """Log out the current user and redirect to landing page."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('landing')


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """
    User dashboard showing recent jobs and credit balance.
    
    Displays the 10 most recent jobs and indicates whether
    the user can upload new files (max 5 queued jobs).
    """
    jobs = Job.objects.filter(user=request.user)[:10]
    queued_jobs = Job.objects.filter(user=request.user, status__in=[JobStatus.QUEUED, JobStatus.PROCESSING]).count()
    
    context = {
        'jobs': jobs,
        'queued_jobs': queued_jobs,
        'can_upload': queued_jobs < 5,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def profile(request: HttpRequest) -> HttpResponse:
    """User profile management view for updating account details."""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'core/profile.html', {'form': form})


@login_required
def change_password(request: HttpRequest) -> HttpResponse:
    """
    Change password view.
    
    Validates current password before allowing password change.
    Keeps user logged in after successful change.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            if not request.user.check_password(form.cleaned_data['current_password']):
                messages.error(request, 'Current password is incorrect.')
            else:
                request.user.set_password(form.cleaned_data['new_password1'])
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully.')
                return redirect('profile')
    else:
        form = PasswordChangeForm()
    
    return render(request, 'core/change_password.html', {'form': form})


@login_required
@require_http_methods(['POST'])
def delete_account(request: HttpRequest) -> HttpResponse:
    """
    Delete user account and all associated data.
    
    This action is irreversible. Logs out the user and deletes
    their account, jobs, and uploaded files.
    """
    user = request.user
    logout(request)
    user.delete()
    messages.info(request, 'Your account has been deleted.')
    return redirect('landing')


@login_required
def credits(request: HttpRequest) -> HttpResponse:
    """Display available credit packages for purchase."""
    packages = CreditPackage.objects.filter(is_active=True)
    return render(request, 'core/credits.html', {'packages': packages})


@login_required
def jobs_list(request: HttpRequest) -> HttpResponse:
    """Display all jobs for the current user."""
    jobs = Job.objects.filter(user=request.user)
    return render(request, 'core/jobs_list.html', {'jobs': jobs})


@login_required
def job_detail(request: HttpRequest, job_id: uuid.UUID) -> HttpResponse:
    """
    Display job details and output files.
    
    Syncs job status with backend if still processing.
    Shows waveform players for completed jobs with available files.
    
    Args:
        request: The HTTP request
        job_id: UUID of the job to display
    """
    try:
        job = Job.objects.get(id=job_id, user=request.user)
    except Job.DoesNotExist:
        messages.error(request, 'Job not found.')
        return redirect('dashboard')
    
    # Sync status from backend if job is still processing
    if job.status in [JobStatus.QUEUED, JobStatus.PROCESSING]:
        try:
            from .backend_client import backend_client
            status = backend_client.get_job_status(str(job.id))
            if status:
                # Update local job status
                status_map = {
                    'queued': JobStatus.QUEUED,
                    'processing': JobStatus.PROCESSING,
                    'completed': JobStatus.COMPLETED,
                    'failed': JobStatus.FAILED,
                }
                new_status = status_map.get(status.status, job.status)
                
                if new_status != job.status:
                    job.status = new_status
                    if new_status == JobStatus.COMPLETED and status.output_files:
                        # Set output path
                        output_dir = os.path.join(settings.MEDIA_ROOT, 'outputs', str(job.id))
                        job.output_path = output_dir
                        # Set expiration (24 hours from completion)
                        from django.utils import timezone
                        from datetime import timedelta
                        job.expires_at = timezone.now() + timedelta(hours=24)
                    elif new_status == JobStatus.FAILED:
                        job.error_message = status.error_message or 'Unknown error'
                    job.save()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync job status: {e}")
    
    # Get list of output files if job is completed
    output_files = []
    transcription_content = None
    
    if job.status == JobStatus.COMPLETED and job.files_available:
        output_dir = job.output_path
        if output_dir and os.path.isdir(output_dir):
            from .models import JobType
            
            if job.job_type == JobType.SEPARATION:
                # Audio stem files
                for filename in os.listdir(output_dir):
                    if filename.endswith(('.wav', '.mp3', '.flac')):
                        stem_name = os.path.splitext(filename)[0]
                        output_files.append({
                            'name': stem_name.title(),
                            'filename': filename,
                            'stem': stem_name,
                            'type': 'audio',
                        })
            
            elif job.job_type == JobType.TRANSCRIPTION:
                # Transcription output files
                for filename in os.listdir(output_dir):
                    if filename.endswith(('.txt', '.json', '.srt', '.vtt', '.lrc')):
                        # Get filename without extension for the stem parameter
                        stem_name = os.path.splitext(filename)[0]
                        output_files.append({
                            'name': filename,
                            'filename': filename,
                            'stem': stem_name,
                            'type': 'transcription',
                        })
                        
                        # Load text content for preview
                        if filename.endswith(('.txt', '.lrc', '.srt', '.vtt')):
                            try:
                                with open(os.path.join(output_dir, filename), 'r', encoding='utf-8') as f:
                                    transcription_content = f.read()
                            except Exception:
                                pass
    
    return render(request, 'core/job_detail.html', {
        'job': job,
        'output_files': output_files,
        'transcription_content': transcription_content,
    })


def demo(request: HttpRequest) -> HttpResponse:
    """Demo page showcasing sample processed audio with waveform players."""
    return render(request, 'core/demo.html', {
        'default_credits': SiteSettings.get_default_credits(),
    })


@login_required
def create_job(request: HttpRequest) -> HttpResponse:
    """
    Create a new processing job (separation, transcription, or lyrics).
    
    Validates:
    - User has fewer than 5 queued jobs
    - User has enough credits for the job type
    
    On success:
    - Saves uploaded file to user's upload directory
    - Creates job record in database
    - Submits job to backend service
    - Deducts 1 credit
    """
    # Check if user can upload (less than 5 queued jobs)
    from .models import JobType, TranscriptionType, TranscriptionFormat
    from .constants import CREDIT_COST_SEPARATION, CREDIT_COST_TRANSCRIPTION
    
    queued_jobs = Job.objects.filter(
        user=request.user, 
        status__in=[JobStatus.QUEUED, JobStatus.PROCESSING]
    ).count()
    
    if queued_jobs >= 5:
        messages.error(request, 'You have too many jobs in the queue. Please wait for some to complete.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = JobCreateForm(request.POST, request.FILES)
        if form.is_valid():
            # Get common form data
            audio_file = form.cleaned_data['audio_file']
            job_type_str = form.cleaned_data['job_type']
            
            # Map job_type string to JobType enum for credit calculation
            job_type_map = {
                'separation': JobType.SEPARATION,
                'transcription': JobType.TRANSCRIPTION,
            }
            job_type_enum = job_type_map[job_type_str]
            
            # Calculate credit cost using constants
            credit_cost_map = {
                JobType.SEPARATION: CREDIT_COST_SEPARATION,
                JobType.TRANSCRIPTION: CREDIT_COST_TRANSCRIPTION,
            }
            credit_cost = credit_cost_map[job_type_enum]
            
            # Check if user has enough credits
            if not request.user.has_credits(credit_cost):
                messages.error(request, f'You need {credit_cost} credits to create this job.')
                return redirect('credits')
            
            # Create upload directory if it doesn't exist
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(request.user.id))
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            file_ext = os.path.splitext(audio_file.name)[1].lower()
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Save the uploaded file
            with open(file_path, 'wb+') as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)
            
            # Map job_type string to JobType enum
            job_type_map = {
                'separation': JobType.SEPARATION,
                'transcription': JobType.TRANSCRIPTION,
            }
            job_type = job_type_map[job_type_str]
            
            # Create the job in the database based on type
            if job_type == JobType.SEPARATION:
                model = form.cleaned_data['model']
                separation_type = form.cleaned_data['separation_type']
                two_stem = form.cleaned_data['two_stem'] if separation_type == 'two_stem' else None
                output_format = form.cleaned_data['output_format']
                
                job = Job.objects.create(
                    user=request.user,
                    job_type=job_type,
                    original_filename=audio_file.name,
                    model=model,
                    two_stem=two_stem,
                    output_format=output_format,
                    input_path=file_path,
                    status=JobStatus.QUEUED,
                )
            
            elif job_type == JobType.TRANSCRIPTION:
                # Get the output format and map to transcription_type and transcription_format
                transcription_output_format = form.cleaned_data['transcription_output_format']
                language = form.cleaned_data.get('language') or None
                
                # Map output format to internal transcription_type and transcription_format
                output_format_mapping = {
                    'txt': ('basic', 'txt'),
                    'subtitles': ('subtitles', 'srt'),  # Backend generates both SRT and VTT
                    'lrc': ('lyrics', 'lrc'),
                }
                transcription_type, transcription_format = output_format_mapping[transcription_output_format]
                
                job = Job.objects.create(
                    user=request.user,
                    job_type=job_type,
                    original_filename=audio_file.name,
                    transcription_type=transcription_type,
                    transcription_format=transcription_format,
                    language=language,
                    input_path=file_path,
                    status=JobStatus.QUEUED,
                )
            
            # Submit job to backend service
            try:
                from .backend_client import backend_client
                
                # Calculate relative path for backend
                relative_path = os.path.join(str(request.user.id), unique_filename)
                
                if job_type == JobType.SEPARATION:
                    backend_client.submit_job(
                        job_id=str(job.id),
                        input_path=relative_path,
                        model=model,
                        two_stem=two_stem,
                        output_format=output_format,
                    )
                elif job_type == JobType.TRANSCRIPTION:
                    backend_client.submit_transcription_job(
                        job_id=str(job.id),
                        input_path=relative_path,
                        transcription_type=transcription_type,
                        transcription_format=transcription_format,
                        language=language,
                    )
            except Exception as e:
                # Log error but don't fail - job is queued locally
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to submit job to backend: {e}")
            
            # Deduct credits
            request.user.use_credits(credit_cost)
            
            job_type_name = job.get_job_type_display()
            messages.success(request, f'{job_type_name} job created! "{audio_file.name}" is now in the queue. ({credit_cost} credit{"s" if credit_cost > 1 else ""} used)')
            return redirect('job_detail', job_id=job.id)
    else:
        form = JobCreateForm()
    
    context = {
        'form': form,
        'credits': request.user.credits,
        'queued_jobs': queued_jobs,
    }
    return render(request, 'core/create_job.html', context)


@login_required
@require_http_methods(["GET"])
def job_status_api(request: HttpRequest, job_id: uuid.UUID) -> JsonResponse:
    """
    API endpoint to get job status for polling.
    
    Used by the frontend to poll for job completion.
    Syncs status with backend and returns current state.
    
    Returns JSON:
        - status: Current job status
        - files_available: Whether output files can be downloaded
        - output_files: List of stem files (if completed)
        - error_message: Error details (if failed)
    """
    try:
        job = Job.objects.get(id=job_id, user=request.user)
    except Job.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)
    
    # Sync status from backend if job is still processing
    if job.status in [JobStatus.QUEUED, JobStatus.PROCESSING]:
        try:
            from .backend_client import backend_client
            status = backend_client.get_job_status(str(job.id))
            if status:
                status_map = {
                    'queued': JobStatus.QUEUED,
                    'processing': JobStatus.PROCESSING,
                    'completed': JobStatus.COMPLETED,
                    'failed': JobStatus.FAILED,
                }
                new_status = status_map.get(status.status, job.status)
                
                if new_status != job.status:
                    job.status = new_status
                    if new_status == JobStatus.COMPLETED and status.output_files:
                        output_dir = os.path.join(settings.MEDIA_ROOT, 'outputs', str(job.id))
                        job.output_path = output_dir
                        from django.utils import timezone
                        from datetime import timedelta
                        job.expires_at = timezone.now() + timedelta(hours=24)
                    elif new_status == JobStatus.FAILED:
                        job.error_message = status.error_message or 'Unknown error'
                    job.save()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync job status: {e}")
    
    # Build response
    response_data = {
        'status': job.status,
        'files_available': job.files_available,
        'error_message': job.error_message if job.status == JobStatus.FAILED else None,
    }
    
    # Include output files if completed
    if job.status == JobStatus.COMPLETED and job.files_available:
        output_dir = job.output_path
        output_files = []
        transcription_content = None
        job_type = job.job_type
        
        if output_dir and os.path.isdir(output_dir):
            from .models import JobType
            
            if job_type == JobType.SEPARATION:
                # Audio stem files
                for filename in os.listdir(output_dir):
                    if filename.endswith(('.wav', '.mp3', '.flac')):
                        stem_name = os.path.splitext(filename)[0]
                        output_files.append({
                            'name': stem_name.title(),
                            'filename': filename,
                            'stem': stem_name,
                            'type': 'audio',
                            'download_url': f'/jobs/{job_id}/download/{stem_name}/',
                        })
            
            elif job_type == JobType.TRANSCRIPTION:
                # Transcription output files
                for filename in os.listdir(output_dir):
                    if filename.endswith(('.txt', '.json', '.srt', '.vtt', '.lrc')):
                        stem_name = os.path.splitext(filename)[0]
                        output_files.append({
                            'name': filename,
                            'filename': filename,
                            'stem': stem_name,
                            'type': 'transcription',
                            'download_url': f'/jobs/{job_id}/download/{stem_name}/',
                        })
                        
                        # Load text content for preview (prefer .txt, then .srt/.vtt/.lrc)
                        if transcription_content is None and filename.endswith(('.txt', '.lrc', '.srt', '.vtt')):
                            try:
                                with open(os.path.join(output_dir, filename), 'r', encoding='utf-8') as f:
                                    transcription_content = f.read()
                            except Exception:
                                pass
        
        response_data['output_files'] = output_files
        response_data['job_type'] = job_type
        if transcription_content:
            response_data['transcription_content'] = transcription_content
    
    return JsonResponse(response_data)


@login_required
def download_stem(request: HttpRequest, job_id: uuid.UUID, stem: str) -> HttpResponse:
    """
    Download a specific file from a completed job (audio stem or transcription).
    
    Args:
        request: The HTTP request
        job_id: UUID of the job
        stem: Name of the file to download (e.g., 'vocals', 'drums', 'lyrics', 'transcription')
    
    Returns:
        FileResponse with the file
        
    Raises:
        Http404: If job not found, files expired, or file doesn't exist
    """
    from django.http import FileResponse, Http404
    
    try:
        job = Job.objects.get(id=job_id, user=request.user)
    except Job.DoesNotExist:
        raise Http404("Job not found")
    
    if not job.files_available:
        raise Http404("Files are no longer available")
    
    # Find the file
    output_dir = job.output_path
    if not output_dir or not os.path.isdir(output_dir):
        raise Http404("Output directory not found")
    
    # Look for the file - could be audio or transcription
    file_path = None
    
    # Try audio extensions
    for ext in ['.wav', '.mp3', '.flac']:
        potential_path = os.path.join(output_dir, f"{stem}{ext}")
        if os.path.isfile(potential_path):
            file_path = potential_path
            break
    
    # Try transcription extensions if not found
    if not file_path:
        for ext in ['.txt', '.json', '.srt', '.vtt', '.lrc']:
            potential_path = os.path.join(output_dir, f"{stem}{ext}")
            if os.path.isfile(potential_path):
                file_path = potential_path
                break
    
    if not file_path:
        raise Http404("File not found")
    
    # Serve the file
    response = FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=f"{job.original_filename.rsplit('.', 1)[0]}_{stem}{os.path.splitext(file_path)[1]}"
    )
    return response


@login_required
def download_all_stems(request: HttpRequest, job_id: uuid.UUID) -> HttpResponse:
    """
    Download all output files from a completed job as a ZIP file.
    
    Creates a temporary ZIP file containing all output files (audio and/or transcription),
    named appropriately based on the job type.
    
    Args:
        request: The HTTP request
        job_id: UUID of the job
        
    Returns:
        FileResponse with ZIP archive
        
    Raises:
        Http404: If job not found or files expired
    """
    from django.http import FileResponse, Http404
    from .models import JobType
    import zipfile
    import tempfile
    
    try:
        job = Job.objects.get(id=job_id, user=request.user)
    except Job.DoesNotExist:
        raise Http404("Job not found")
    
    if not job.files_available:
        raise Http404("Files are no longer available")
    
    output_dir = job.output_path
    if not output_dir or not os.path.isdir(output_dir):
        raise Http404("Output directory not found")
    
    # Create a temporary ZIP file
    base_name = job.original_filename.rsplit('.', 1)[0]
    
    # Determine ZIP filename suffix based on job type
    if job.job_type == JobType.TRANSCRIPTION:
        zip_suffix = "transcription"
    else:
        zip_suffix = "stems"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
        with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add all files from output directory
            for filename in os.listdir(output_dir):
                # Include audio files
                if filename.endswith(('.wav', '.mp3', '.flac')):
                    file_path = os.path.join(output_dir, filename)
                    stem_name = os.path.splitext(filename)[0]
                    ext = os.path.splitext(filename)[1]
                    archive_name = f"{base_name}_{stem_name}{ext}"
                    zf.write(file_path, archive_name)
                # Include transcription files
                elif filename.endswith(('.txt', '.json', '.srt', '.vtt', '.lrc')):
                    file_path = os.path.join(output_dir, filename)
                    # Keep the original transcription filename
                    zf.write(file_path, filename)
        
        tmp_path = tmp_file.name
    
    # Serve the ZIP file
    response = FileResponse(
        open(tmp_path, 'rb'),
        as_attachment=True,
        filename=f"{base_name}_{zip_suffix}.zip"
    )
    # Clean up temp file after response is sent
    response._resource_closers.append(lambda: os.unlink(tmp_path))
    return response


@login_required
def purchase_credits(request: HttpRequest, package_id: int) -> HttpResponse:
    """
    Display the Square payment form for purchasing a credit package.
    
    Verifies Square is configured before showing the payment form.
    
    Args:
        request: The HTTP request
        package_id: ID of the CreditPackage to purchase
    """
    from .models import CreditPackage
    
    try:
        package = CreditPackage.objects.get(id=package_id, is_active=True)
    except CreditPackage.DoesNotExist:
        messages.error(request, 'Credit package not found.')
        return redirect('credits')
    
    # Check if Square is configured
    square_configured = all([
        settings.SQUARE_APPLICATION_ID,
        settings.SQUARE_LOCATION_ID,
        settings.SQUARE_ACCESS_TOKEN
    ])
    
    if not square_configured:
        messages.error(request, 'Payment processing is not available at this time.')
        return redirect('credits')
    
    context = {
        'package': package,
        'square_app_id': settings.SQUARE_APPLICATION_ID,
        'square_location_id': settings.SQUARE_LOCATION_ID,
        'square_environment': settings.SQUARE_ENVIRONMENT,
    }
    return render(request, 'core/purchase.html', context)


@login_required
def process_payment(request: HttpRequest, package_id: int) -> JsonResponse:
    """
    Process a payment from the Square Web Payments SDK.
    
    Receives a payment token from the frontend, creates a payment
    with Square, and on success adds credits to the user's account.
    
    Args:
        request: POST request with JSON body containing:
            - sourceId: Payment token from Square SDK
            - idempotencyKey: Unique key to prevent duplicate charges
        package_id: ID of the CreditPackage being purchased
        
    Returns:
        JSON response with success status and new credit balance,
        or error message on failure.
    """
    import json
    from .models import CreditPackage, Purchase
    from .payments import payment_service
    from django.utils import timezone
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        package = CreditPackage.objects.get(id=package_id, is_active=True)
    except CreditPackage.DoesNotExist:
        return JsonResponse({'error': 'Credit package not found'}, status=404)
    
    try:
        data = json.loads(request.body)
        source_id = data.get('sourceId')  # Payment token from Web Payments SDK
        idempotency_key = data.get('idempotencyKey')
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid request data'}, status=400)
    
    if not source_id:
        return JsonResponse({'error': 'Payment token is required'}, status=400)
    
    # Create a pending purchase record
    purchase = Purchase.objects.create(
        user=request.user,
        package=package,
        amount_cents=package.price_cents,
        is_completed=False
    )
    
    # Process payment with Square
    result = payment_service.create_payment(
        source_id=source_id,
        amount_cents=package.price_cents,
        idempotency_key=idempotency_key,
        note=f"MuxMinus Credits: {package.name} ({package.credits} credits)"
    )
    
    if result.success:
        # Update purchase record
        purchase.square_payment_id = result.payment_id
        purchase.is_completed = True
        purchase.completed_at = timezone.now()
        purchase.save()
        
        # Add credits to user
        request.user.add_credits(package.credits)
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully purchased {package.credits} credits!',
            'credits': request.user.credits,
            'receipt_url': result.receipt_url
        })
    else:
        # Payment failed - delete the pending purchase
        purchase.delete()
        
        return JsonResponse({
            'success': False,
            'error': result.error_message or 'Payment failed'
        }, status=400)