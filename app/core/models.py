from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid


class User(AbstractUser):
    """Custom user model for Mux Minus."""
    email = models.EmailField(unique=True)
    credits = models.PositiveIntegerField(default=3)  # New users get 3 free credits
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Required for email-based authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
    def has_credits(self, amount=1):
        """Check if user has enough credits."""
        from django.conf import settings
        if getattr(settings, 'UNLIMITED_CREDITS', False):
            return True
        return self.credits >= amount
    
    def use_credits(self, amount=1):
        """Deduct credits from user account."""
        from django.conf import settings
        if getattr(settings, 'UNLIMITED_CREDITS', False):
            return True  # Don't deduct in unlimited mode
        if self.has_credits(amount):
            self.credits -= amount
            self.save()
            return True
        return False
    
    def add_credits(self, amount):
        """Add credits to user account."""
        self.credits += amount
        self.save()


class StemChoice(models.TextChoices):
    """Available stem isolation options."""
    VOCALS = 'vocals', 'Vocals'
    DRUMS = 'drums', 'Drums'
    BASS = 'bass', 'Bass'
    OTHER = 'other', 'Other'
    GUITAR = 'guitar', 'Guitar'
    PIANO = 'piano', 'Piano'


class ModelChoice(models.TextChoices):
    """Available Demucs models."""
    HTDEMUCS = 'htdemucs', 'HT Demucs (4 stems)'
    HTDEMUCS_FT = 'htdemucs_ft', 'HT Demucs Fine-tuned (4 stems)'
    HTDEMUCS_6S = 'htdemucs_6s', 'HT Demucs 6-stem'
    HDEMUCS_MMI = 'hdemucs_mmi', 'Hybrid Demucs MMI'


class OutputFormat(models.TextChoices):
    """Output audio format."""
    MP3 = 'mp3', 'MP3 (Smaller files)'
    WAV = 'wav', 'WAV (Lossless quality)'


class JobType(models.TextChoices):
    """Job processing type."""
    SEPARATION = 'separation', 'Audio Separation'
    TRANSCRIPTION = 'transcription', 'Transcription'


class TranscriptionType(models.TextChoices):
    """Transcription job types."""
    BASIC = 'basic', 'Basic Text'
    TIMESTAMPED = 'timestamped', 'Timestamped JSON'
    SUBTITLES = 'subtitles', 'Subtitles (SRT/VTT)'
    LYRICS = 'lyrics', 'Lyrics (LRC)'


class TranscriptionFormat(models.TextChoices):
    """Output format for transcription."""
    TEXT = 'txt', 'Plain Text'
    JSON = 'json', 'JSON with Timestamps'
    SRT = 'srt', 'SubRip Subtitles'
    VTT = 'vtt', 'WebVTT Subtitles'
    LRC = 'lrc', 'LRC Lyrics'


class JobStatus(models.TextChoices):
    """Job processing status."""
    QUEUED = 'queued', 'Queued'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class Job(models.Model):
    """Represents a processing job (separation, transcription, or lyrics pipeline)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs')
    
    # Job type and configuration
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.SEPARATION,
                                 help_text='Type of processing job')
    original_filename = models.CharField(max_length=255)
    
    # Separation-specific fields
    model = models.CharField(max_length=50, choices=ModelChoice.choices, blank=True, null=True,
                            help_text='Demucs model for separation jobs')
    two_stem = models.CharField(max_length=20, choices=StemChoice.choices, blank=True, null=True,
                                 help_text='If set, performs 2-stem separation isolating this stem')
    output_format = models.CharField(max_length=10, choices=OutputFormat.choices, default=OutputFormat.MP3,
                                      help_text='Output audio format for separation')
    
    # Transcription-specific fields
    transcription_type = models.CharField(max_length=20, choices=TranscriptionType.choices, blank=True, null=True,
                                          help_text='Type of transcription to perform')
    transcription_format = models.CharField(max_length=10, choices=TranscriptionFormat.choices, blank=True, null=True,
                                            help_text='Output format for transcription')
    language = models.CharField(max_length=10, blank=True, null=True,
                               help_text='Language code for transcription (e.g., en, es)')
    
    # Status tracking
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.QUEUED)
    error_message = models.TextField(blank=True, null=True)
    
    # File paths (relative to shared volume)
    input_path = models.CharField(max_length=500)
    output_path = models.CharField(max_length=500, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.original_filename} - {self.get_job_type_display()} - {self.status}"
    
    def save(self, *args, **kwargs):
        # Set expiration to 24 hours after completion
        if self.status == JobStatus.COMPLETED and not self.expires_at:
            self.completed_at = timezone.now()
            self.expires_at = self.completed_at + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if the job output files have expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def files_available(self):
        """Check if output files are still available for download."""
        return self.status == JobStatus.COMPLETED and not self.is_expired
    
    @property
    def credit_cost(self):
        """Calculate the credit cost for this job type."""
        return 1  # All jobs cost 1 credit


class CreditPackage(models.Model):
    """Available credit packages for purchase."""
    name = models.CharField(max_length=100)
    credits = models.PositiveIntegerField()
    price_cents = models.PositiveIntegerField()  # Price in cents
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['credits']
    
    def __str__(self):
        return f"{self.name} - {self.credits} credits (${self.price_cents / 100:.2f})"
    
    @property
    def price_dollars(self):
        return self.price_cents / 100
    
    @property
    def price_per_credit(self):
        if self.credits > 0:
            return self.price_cents / 100 / self.credits
        return 0


class Purchase(models.Model):
    """Record of credit purchases."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    package = models.ForeignKey(CreditPackage, on_delete=models.PROTECT)
    
    # Square payment details
    square_payment_id = models.CharField(max_length=255, blank=True, null=True)
    amount_cents = models.PositiveIntegerField()
    
    # Status
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.package.name}"


class SiteSettings(models.Model):
    """
    Singleton model for site-wide configuration.
    
    This model stores configurable settings that can be edited
    through the Django admin interface.
    """
    default_credits = models.PositiveIntegerField(
        default=3,
        help_text="Number of free credits given to new users upon registration."
    )
    
    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"
    
    def __str__(self):
        return "Site Settings"
    
    def save(self, *args, **kwargs):
        """Ensure only one instance exists (singleton pattern)."""
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get the site settings instance, creating it if needed."""
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
    
    @classmethod
    def get_default_credits(cls):
        """Get the default credits for new users."""
        return cls.get_settings().default_credits
