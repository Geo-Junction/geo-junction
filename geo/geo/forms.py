# geo_junction/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from django.utils import timezone

from . import models


# ===========================================================================
# 1. USER AUTHENTICATION FORMS
# ===========================================================================

class UserRegistrationForm(UserCreationForm):
    """Form for registering new users."""
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Email Address',
            'autofocus': True
        }),
        help_text=_('Required. Enter a valid email address.')
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username (Optional)'
        }),
        help_text=_('Optional. Choose a unique username.')
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number'
        })
    )
    job_title = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Job Title'
        })
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Department'
        })
    )

    class Meta:
        model = models.User
        fields = (
            'email', 'username', 'first_name', 'last_name', 'phone',
            'job_title', 'department', 'password1', 'password2'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
        # Add password help text
        self.fields['password1'].help_text = _(
            '<ul class="text-muted small">'
            '<li>Your password must be at least 8 characters.</li>'
            '<li>It cannot be entirely numeric.</li>'
            '<li>It must not be too similar to your personal information.</li>'
            '</ul>'
        )

    def clean_email(self):
        """Ensure email is unique."""
        email = self.cleaned_data.get('email')
        if models.User.objects.filter(email=email).exists():
            raise ValidationError(_('A user with this email already exists.'))
        return email


class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form using email as the username field."""
    username = forms.EmailField(
        label=_('Email'),
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Email Address',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Password'
        })
    )

    error_messages = {
        'invalid_login': _(
            'Please enter a correct email and password. '
            'Note that both fields may be case-sensitive.'
        ),
        'inactive': _('This account is inactive.'),
    }


class CustomPasswordResetForm(PasswordResetForm):
    """Custom password reset form."""
    email = forms.EmailField(
        label=_('Email'),
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email address',
            'autocomplete': 'email'
        })
    )


class CustomSetPasswordForm(SetPasswordForm):
    """Custom set password form."""
    new_password1 = forms.CharField(
        label=_('New Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New Password',
            'autocomplete': 'new-password'
        }),
        help_text=_(
            '<ul class="text-muted small">'
            '<li>Your password must be at least 8 characters.</li>'
            '<li>It cannot be entirely numeric.</li>'
            '<li>It must not be too similar to your personal information.</li>'
            '</ul>'
        )
    )
    new_password2 = forms.CharField(
        label=_('Confirm New Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm New Password',
            'autocomplete': 'new-password'
        })
    )


# ===========================================================================
# 2. CONTACT FORM
# ===========================================================================

class ContactForm(forms.ModelForm):
    """Contact form for website visitors."""
    class Meta:
        model = models.ContactMessage
        fields = ('name', 'email', 'subject', 'message')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Full Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Email Address'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subject'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Your Message'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Pre-fill fields if user is authenticated
        if self.user and self.user.is_authenticated:
            self.fields['name'].initial = self.user.get_full_name() or self.user.email
            self.fields['email'].initial = self.user.email

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and self.user.is_authenticated:
            # Optionally link to user if you add a user FK to ContactMessage
            pass
        if commit:
            instance.save()
        return instance


# ===========================================================================
# 3. JOB APPLICATION FORM
# ===========================================================================

class JobApplicationForm(forms.ModelForm):
    """Form for applying to job postings."""
    class Meta:
        model = models.JobApplication
        fields = ('first_name', 'last_name', 'email', 'phone', 'resume', 'cover_letter')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Email Address'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number'
            }),
            'resume': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'cover_letter': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us why you\'re a great fit for this role...'
            }),
        }
        help_texts = {
            'resume': 'Upload your resume (PDF, DOC, or DOCX format)',
        }

    def __init__(self, *args, **kwargs):
        self.job = kwargs.pop('job', None)
        super().__init__(*args, **kwargs)

        if self.job:
            self.fields['cover_letter'].help_text = f'Tell us why you\'re interested in the {self.job.title} position.'

    def clean_resume(self):
        """Validate resume file type and size."""
        resume = self.cleaned_data.get('resume')
        if resume:
            # Check file extension
            valid_extensions = ['pdf', 'doc', 'docx', 'txt']
            ext = resume.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError(
                    f'Unsupported file format. Please upload a file with one of these extensions: {", ".join(valid_extensions)}'
                )
            # Check file size (max 5MB)
            if resume.size > 5 * 1024 * 1024:
                raise ValidationError('File size exceeds 5MB. Please upload a smaller file.')
        return resume

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.job:
            instance.job = self.job
        if commit:
            instance.save()
        return instance


# ===========================================================================
# 4. NEWSLETTER SUBSCRIBER FORM
# ===========================================================================

class SubscriberForm(forms.ModelForm):
    """Form for newsletter subscription."""
    class Meta:
        model = models.Subscriber
        fields = ('email',)
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address'
            }),
        }

    def clean_email(self):
        """Check if email is already subscribed."""
        email = self.cleaned_data.get('email')
        if models.Subscriber.objects.filter(email=email, is_active=True).exists():
            raise ValidationError(_('This email is already subscribed to our newsletter.'))
        return email

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.is_active = True
        if commit:
            instance.save()
        return instance


# ===========================================================================
# 5. SITE SEARCH FORM
# ===========================================================================

class SearchForm(forms.Form):
    """Site-wide search form."""
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search...',
            'aria-label': 'Search'
        })
    )
    model_type = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All'),
            ('project', 'Projects'),
            ('news', 'News'),
            ('job', 'Jobs'),
            ('page', 'Pages'),
            ('document', 'Documents'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


# ===========================================================================
# 6. ADMIN CONTENT FORMS
# ===========================================================================

class PageAdminForm(forms.ModelForm):
    """Custom form for Page admin with better content editing."""
    class Meta:
        model = models.Page
        fields = '__all__'
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
                'placeholder': 'Enter page content (HTML supported)'
            }),
            'meta_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Meta description for SEO (max 160 characters)'
            }),
        }
        help_texts = {
            'content': 'You can use HTML tags for formatting. Rich text editor integration recommended.',
            'meta_description': 'Keep under 160 characters for optimal SEO.',
        }

    def clean_meta_description(self):
        """Validate meta description length."""
        meta = self.cleaned_data.get('meta_description')
        if meta and len(meta) > 160:
            raise ValidationError('Meta description should be under 160 characters.')
        return meta


class NewsArticleAdminForm(forms.ModelForm):
    """Custom form for NewsArticle admin."""
    class Meta:
        model = models.NewsArticle
        fields = '__all__'
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Enter article content (HTML supported)'
            }),
        }


class JobPostingAdminForm(forms.ModelForm):
    """Custom form for JobPosting admin."""
    class Meta:
        model = models.JobPosting
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Job description (HTML supported)'
            }),
            'requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Job requirements (HTML supported)'
            }),
            'responsibilities': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Job responsibilities (HTML supported)'
            }),
        }


# ===========================================================================
# 7. PROJECT TASK FORM (for internal use)
# ===========================================================================

class ProjectTaskForm(forms.ModelForm):
    """Form for creating/updating project tasks."""
    class Meta:
        model = models.ProjectTask
        fields = ('title', 'description', 'assigned_to', 'due_date', 'status')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_due_date(self):
        """Validate due date is not in the past (except for updates)."""
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now().date():
            # Check if we're updating an existing task
            if not self.instance.pk:
                raise ValidationError('Due date cannot be in the past.')
        return due_date


# ===========================================================================
# 8. PROJECT NOTE FORM (for internal use)
# ===========================================================================

class ProjectNoteForm(forms.ModelForm):
    """Form for adding notes to projects."""
    class Meta:
        model = models.ProjectNote
        fields = ('content', 'is_internal')
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter your note...'
            }),
            'is_internal': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        self.author = kwargs.pop('author', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if self.author:
            instance.author = self.author
        if commit:
            instance.save()
        return instance


# ===========================================================================
# 9. JOB APPLICATION STATUS UPDATE FORM (for HR)
# ===========================================================================

class JobApplicationStatusForm(forms.ModelForm):
    """Form for HR to update job application status."""
    class Meta:
        model = models.JobApplication
        fields = ('status', 'notes')
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add internal notes...'
            }),
        }


# ===========================================================================
# 10. PROFILE UPDATE FORMS
# ===========================================================================

class UserProfileForm(forms.ModelForm):
    """Form for users to update their profile."""
    class Meta:
        model = models.User
        fields = ('first_name', 'last_name', 'phone', 'job_title', 'department')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserProfileSettingsForm(forms.ModelForm):
    """Form for users to update their profile settings."""
    class Meta:
        model = models.UserProfile
        fields = ('timezone', 'notification_preferences')
        widgets = {
            'timezone': forms.Select(attrs={'class': 'form-select'}),
            'notification_preferences': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'JSON preferences'
            }),
        }


# ===========================================================================
# 11. REPORT UPLOAD FORM (for admin)
# ===========================================================================

class ReportUploadForm(forms.ModelForm):
    """Form for uploading reports."""
    class Meta:
        model = models.Report
        fields = ('title', 'project', 'report_type', 'file', 'publication_date', 'is_public')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'publication_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_file(self):
        """Validate file type and size."""
        file = self.cleaned_data.get('file')
        if file:
            # Check file extension
            valid_extensions = ['pdf', 'doc', 'docx', 'xlsx', 'xls', 'ppt', 'pptx', 'txt', 'zip']
            ext = file.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError(
                    f'Unsupported file format. Please upload: {", ".join(valid_extensions)}'
                )
            # Check file size (max 20MB)
            if file.size > 20 * 1024 * 1024:
                raise ValidationError('File size exceeds 20MB. Please upload a smaller file.')
        return file


# ===========================================================================
# 12. DOCUMENT UPLOAD FORM (for admin)
# ===========================================================================

class DocumentUploadForm(forms.ModelForm):
    """Form for uploading documents."""
    class Meta:
        model = models.Document
        fields = ('title', 'description', 'file', 'document_type', 'is_public')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_file(self):
        """Validate file type and size."""
        file = self.cleaned_data.get('file')
        if file:
            # Check file extension
            valid_extensions = ['pdf', 'doc', 'docx', 'xlsx', 'xls', 'ppt', 'pptx', 'txt', 'zip', 'jpg', 'jpeg', 'png', 'gif']
            ext = file.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError(
                    f'Unsupported file format. Please upload: {", ".join(valid_extensions)}'
                )
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError('File size exceeds 10MB. Please upload a smaller file.')
        return file


# ===========================================================================
# 13. HEROSLIDE ADMIN FORM (for admin)
# ===========================================================================

class HeroSlideAdminForm(forms.ModelForm):
    """Custom form for HeroSlide admin."""
    class Meta:
        model = models.HeroSlide
        fields = '__all__'
        widgets = {
            'cta_url': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '/about/ or https://example.com'
            }),
        }


# ===========================================================================
# 14. GALLERY IMAGE UPLOAD FORM (for admin)
# ===========================================================================

class GalleryImageUploadForm(forms.ModelForm):
    """Form for uploading gallery images."""
    class Meta:
        model = models.GalleryImage
        fields = ('title', 'image', 'caption', 'category', 'is_featured')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'caption': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_image(self):
        """Validate image file."""
        image = self.cleaned_data.get('image')
        if image:
            # Check file extension
            valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']
            ext = image.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError(
                    f'Unsupported image format. Please upload: {", ".join(valid_extensions)}'
                )
            # Check file size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError('Image size exceeds 5MB. Please upload a smaller image.')
        return image


# ===========================================================================
# 15. SITE CONFIG FORM (for admin)
# ===========================================================================

class SiteConfigForm(forms.ModelForm):
    """Form for site configuration."""
    class Meta:
        model = models.SiteConfig
        fields = ('key', 'value', 'is_active', 'description')
        widgets = {
            'key': forms.TextInput(attrs={'class': 'form-control'}),
            'value': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }


# ===========================================================================
# 16. MENU ITEM FORM (for admin)
# ===========================================================================

class MenuItemForm(forms.ModelForm):
    """Form for menu items."""
    class Meta:
        model = models.MenuItem
        fields = ('title', 'parent', 'url', 'route_name', 'page', 'order', 'is_active', 'new_window', 'css_class')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '/about/'}),
            'route_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'pages:about'}),
            'page': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'new_window': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'css_class': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'nav-link'}),
        }


# ===========================================================================
# 17. FILTER FORMS (for public listing pages)
# ===========================================================================

class ProjectFilterForm(forms.Form):
    """Form for filtering projects on public listing page."""
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + models.ExplorationProject.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    client = forms.ModelChoiceField(
        required=False,
        queryset=models.Client.objects.filter(is_active=True),
        empty_label="All Clients",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    country = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by country...'
        })
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search projects...'
        })
    )


class NewsFilterForm(forms.Form):
    """Form for filtering news articles."""
    category = forms.ModelChoiceField(
        required=False,
        queryset=models.NewsCategory.objects.all(),
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search news...'
        })
    )


class JobFilterForm(forms.Form):
    """Form for filtering job postings."""
    category = forms.ModelChoiceField(
        required=False,
        queryset=models.JobCategory.objects.all(),
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    job_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + models.JobPosting.JOB_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by location...'
        })
    )
    department = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by department...'
        })
    )
    is_remote = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )