from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import Job, ModelChoice, StemChoice, OutputFormat

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    """Form for new user registration."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email',
            'autocomplete': 'email',
        })
    )
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Choose a username',
            'autocomplete': 'username',
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a password',
            'autocomplete': 'new-password',
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password',
        })
    )

    class Meta:
        model = User
        fields = ('email', 'username', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    """Form for user login."""
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email',
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        })
    )


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile."""
    class Meta:
        model = User
        fields = ('email', 'username')
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-input',
            }),
        }


class PasswordChangeForm(forms.Form):
    """Form for changing password."""
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Current password',
        })
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'New password',
        })
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm new password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("New passwords don't match.")
        
        return cleaned_data


class JobCreateForm(forms.Form):
    """Form for creating a new separation job."""
    
    SEPARATION_TYPE_CHOICES = [
        ('full', 'Full Separation'),
        ('two_stem', 'Two-Stem (Karaoke Mode)'),
    ]
    
    MODEL_CHOICES = [
        ('htdemucs', '4-Stem (Standard) - Fastest'),
        ('htdemucs_ft', '4-Stem (Fine-tuned) - Best Quality'),
        ('htdemucs_6s', '6-Stem - Includes Guitar & Piano'),
    ]
    
    TWO_STEM_CHOICES = [
        ('vocals', 'Vocals (isolate vocals from instrumental)'),
        ('drums', 'Drums (isolate drums from the rest)'),
        ('bass', 'Bass (isolate bass from the rest)'),
    ]
    
    OUTPUT_FORMAT_CHOICES = [
        ('mp3', 'MP3 (Smaller files, good quality)'),
        ('wav', 'WAV (Lossless quality, larger files)'),
    ]
    
    audio_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': 'audio/*,.mp3,.wav,.flac,.ogg,.m4a,.aac',
        }),
        help_text='Supported formats: MP3, WAV, FLAC, OGG, M4A, AAC'
    )
    
    separation_type = forms.ChoiceField(
        choices=SEPARATION_TYPE_CHOICES,
        initial='full',
        widget=forms.RadioSelect(attrs={'class': 'form-radio'}),
    )
    
    model = forms.ChoiceField(
        choices=MODEL_CHOICES,
        initial='htdemucs',
        widget=forms.RadioSelect(attrs={'class': 'form-radio'}),
    )
    
    two_stem = forms.ChoiceField(
        choices=TWO_STEM_CHOICES,
        initial='vocals',
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'form-radio'}),
    )
    
    output_format = forms.ChoiceField(
        choices=OUTPUT_FORMAT_CHOICES,
        initial='mp3',
        widget=forms.RadioSelect(attrs={'class': 'form-radio'}),
        help_text='MP3 is recommended for most users. WAV provides lossless quality but larger file sizes.',
    )
    
    def clean_audio_file(self):
        audio_file = self.cleaned_data.get('audio_file')
        if audio_file:
            # Check file size (max 100MB)
            max_size = 100 * 1024 * 1024  # 100MB
            if audio_file.size > max_size:
                raise forms.ValidationError('File size must be under 100MB.')
            
            # Check file extension
            allowed_extensions = ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.aiff']
            ext = '.' + audio_file.name.lower().split('.')[-1] if '.' in audio_file.name else ''
            if ext not in allowed_extensions:
                raise forms.ValidationError(f'Unsupported file format. Allowed: {", ".join(allowed_extensions)}')
        
        return audio_file
    
    def clean(self):
        cleaned_data = super().clean()
        separation_type = cleaned_data.get('separation_type')
        model = cleaned_data.get('model')
        two_stem = cleaned_data.get('two_stem')
        
        # Validate two-stem selection
        if separation_type == 'two_stem' and not two_stem:
            raise forms.ValidationError('Please select which stem to isolate for two-stem separation.')
        
        # Clear two_stem if doing full separation
        if separation_type == 'full':
            cleaned_data['two_stem'] = None
        
        # Validate model choice for two-stem (6-stem model doesn't make sense for 2-stem)
        if separation_type == 'two_stem' and model == 'htdemucs_6s':
            # Allow it, but user should know 6-stem is not optimal for 2-stem
            pass
        
        return cleaned_data
