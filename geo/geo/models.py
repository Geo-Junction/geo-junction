# geo_junction/models.py
# Complete models.py for Geo-Junction corporate website

# setup all imports 
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import ValidationError

# ===========================================================================
# ABSTRACT BASE MIXINS (DRY)
# ===========================================================================

class UUIDPrimaryKeyMixin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

class TimestampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class SlugMixin(models.Model):
    slug = models.SlugField(unique=True, blank=True, max_length=255, db_index=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug and hasattr(self, 'title'):
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class SoftDeleteMixin(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self):
        super().delete()

class PublishableMixin(models.Model):
    """Scheduled publishing and expiration for content."""
    is_published = models.BooleanField(default=False, db_index=True)
    publish_at = models.DateTimeField(default=timezone.now, db_index=True, 
                                      help_text="When this content should go live")
    expires_at = models.DateTimeField(null=True, blank=True, 
                                      help_text="Leave blank to never expire")

    class Meta:
        abstract = True

    @property
    def is_publicly_visible(self):
        now = timezone.now()
        if not self.is_published:
            return False
        if self.publish_at and self.publish_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True

# ===========================================================================
# USER MODEL & ROLES / PERMISSIONS (CRITICAL - NEW)
# ===========================================================================

class User(AbstractUser, UUIDPrimaryKeyMixin, TimestampMixin):
    """Custom user model using email as the primary login field."""
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    last_activity = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    class Meta:
        indexes = [models.Index(fields=['email'])]

class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin):
    """Extends User with fine-grained roles for the platform."""
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('admin', 'Admin'),
        ('project_manager', 'Project Manager'),
        ('geologist', 'Geologist'),
        ('surveyor', 'Surveyor'),
        ('editor', 'Content Editor'),
        ('hr', 'HR Manager'),
        ('viewer', 'Read-Only Viewer'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer', db_index=True)
    timezone = models.CharField(max_length=50, default='UTC')
    notification_preferences = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.user.email} ({self.get_role_display()})"

    def has_role(self, *roles):
        return self.role in roles

# ===========================================================================
# AUDIT LOG (CRITICAL - NEW)
# ===========================================================================

class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks every critical action in the system for compliance (NI 43-101 / JORC)."""
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('download', 'Download'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    model_name = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=255, db_index=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(null=True, blank=True, help_text="JSON diff of before/after")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['user', 'action']),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} - {self.object_repr}"

# ===========================================================================
# ABOUT / COMPANY PROFILE
# ===========================================================================

class CompanyProfile(UUIDPrimaryKeyMixin, TimestampMixin):
    name = models.CharField(max_length=200, default='Geo‑Junction')
    tagline = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to='company/', blank=True, null=True)
    banner = models.ImageField(upload_to='company/', blank=True, null=True)
    mission = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    history = models.TextField(blank=True)
    core_values = models.TextField(blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    map_embed = models.TextField(blank=True, help_text='Google Maps iframe')
    facebook = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    youtube = models.URLField(blank=True)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Company Profile'

# ===========================================================================
# SERVICES (Geophysical Methods)
# ===========================================================================

class ServiceCategory(UUIDPrimaryKeyMixin):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True, db_index=True)
    icon = models.CharField(max_length=50, blank=True, help_text='FontAwesome class')
    order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['order']

class Service(UUIDPrimaryKeyMixin, SlugMixin, TimestampMixin):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name='services')
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['category', 'order']

# ===========================================================================
# CLIENTS, PROJECTS & COLLABORATION (Tasks & Notes - NEW)
# ===========================================================================

class Client(UUIDPrimaryKeyMixin, TimestampMixin):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, db_index=True)
    logo = models.ImageField(upload_to='clients/', blank=True, null=True)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class ExplorationProject(UUIDPrimaryKeyMixin, SlugMixin, TimestampMixin):
    STATUS_CHOICES = [
        ('proposal', 'Proposal'),
        ('mobilisation', 'Mobilisation'),
        ('fieldwork', 'Fieldwork'),
        ('data_processing', 'Data Processing'),
        ('reporting', 'Reporting'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ]
    title = models.CharField(max_length=200)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='projects')
    services = models.ManyToManyField(Service, related_name='projects')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='proposal', db_index=True)
    location = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=100, blank=True)
    coordinates = models.CharField(max_length=50, blank=True, help_text='Central Lat/Long')
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='projects/', blank=True, null=True)
    start_date = models.DateField(blank=True, null=True, db_index=True)
    end_date = models.DateField(blank=True, null=True)
    budget = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    is_public = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    project_website = models.URLField(blank=True, help_text="External project microsite")

    def __str__(self):
        return f"{self.title} ({self.client.name})"

    def get_absolute_url(self):
        return reverse('geo:project_detail', kwargs={'slug': self.slug})

    class Meta:
        ordering = ['-created_at']

class ProjectNote(UUIDPrimaryKeyMixin, TimestampMixin):
    """Internal collaboration - notes attached to projects."""
    project = models.ForeignKey(ExplorationProject, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name='project_notes')
    content = models.TextField()
    is_internal = models.BooleanField(default=True, help_text="If false, visible to client (if portal exists)")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note on {self.project.title} by {self.author.email[:20]}"

class ProjectTask(UUIDPrimaryKeyMixin, TimestampMixin):
    """Assignable tasks within a project."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('review', 'In Review'),
        ('completed', 'Completed'),
        ('blocked', 'Blocked'),
    ]
    project = models.ForeignKey(ExplorationProject, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='assigned_tasks')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_tasks')
    due_date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['due_date', 'status']

    def __str__(self):
        return self.title

# ===========================================================================
# FLEET & OPERATIONS
# ===========================================================================

class Equipment(UUIDPrimaryKeyMixin, TimestampMixin):
    EQUIPMENT_TYPES = [
        ('drill_rig', 'Drill Rig'),
        ('excavator', 'Excavator'),
        ('loader', 'Loader'),
        ('truck', 'Haul Truck'),
        ('support_vehicle', 'Support Vehicle'),
        ('generator', 'Generator'),
        ('camp', 'Camp Equipment'),
        ('other', 'Other'),
    ]
    name = models.CharField(max_length=200)
    equipment_type = models.CharField(max_length=20, choices=EQUIPMENT_TYPES, db_index=True)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='equipment/', blank=True, null=True)
    specifications = models.JSONField(blank=True, null=True)
    purchase_date = models.DateField(blank=True, null=True)
    is_operational = models.BooleanField(default=True, db_index=True)
    current_location = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_equipment_type_display()})"

    class Meta:
        verbose_name_plural = 'Equipment'
        ordering = ['equipment_type', 'name']

# ===========================================================================
# INSTRUMENTS & SURVEYS
# ===========================================================================

class Instrument(UUIDPrimaryKeyMixin, TimestampMixin):
    INSTRUMENT_TYPES = [
        ('magnetometer', 'Magnetometer'),
        ('gravimeter', 'Gravimeter'),
        ('radiometer', 'Radiometer'),
        ('ip_system', 'IP/Resistivity System'),
        ('em_system', 'EM System'),
        ('seismic', 'Seismic'),
        ('gnss', 'GNSS'),
        ('drill_rig', 'Drill Rig'),
        ('sampling_tools', 'Sampling Tools'),
        ('other', 'Other'),
    ]
    instrument_type = models.CharField(max_length=20, choices=INSTRUMENT_TYPES, db_index=True)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, unique=True, blank=True)
    is_operational = models.BooleanField(default=True, db_index=True)
    calibration_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_instrument_type_display()} – {self.model}"

class SurveyMethod(UUIDPrimaryKeyMixin):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True, db_index=True)
    description = models.TextField(blank=True)
    typical_instruments = models.ManyToManyField(Instrument, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class SurveyJob(UUIDPrimaryKeyMixin, TimestampMixin):
    project = models.ForeignKey(ExplorationProject, on_delete=models.CASCADE, related_name='surveys')
    method = models.ForeignKey(SurveyMethod, on_delete=models.PROTECT)
    instruments = models.ManyToManyField(Instrument, blank=True)
    survey_area = models.TextField(blank=True)
    line_km = models.FloatField(blank=True, null=True)
    stations = models.PositiveIntegerField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True, db_index=True)
    end_date = models.DateField(blank=True, null=True)
    data_quality = models.CharField(max_length=50, blank=True, choices=[
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ])
    report_reference = models.CharField(max_length=100, blank=True)
    is_completed = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f"{self.project.title} – {self.method.name}"

    class Meta:
        ordering = ['-start_date']

# ===========================================================================
# REGIONAL OFFICES
# ===========================================================================

class Office(UUIDPrimaryKeyMixin, TimestampMixin):
    name = models.CharField(max_length=200, help_text="e.g., 'Africa Regional Office'")
    slug = models.SlugField(unique=True, blank=True, db_index=True)
    address = models.TextField()
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    map_embed = models.TextField(blank=True, help_text='Google Maps iframe')
    image = models.ImageField(upload_to='offices/', blank=True, null=True)
    is_headquarters = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['display_order']

# ===========================================================================
# PERSONNEL (TEAM)
# ===========================================================================

class Personnel(UUIDPrimaryKeyMixin, TimestampMixin):
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='personnel')
    specialisation = models.CharField(max_length=100, blank=True)
    years_experience = models.PositiveIntegerField(default=0)
    certifications = models.TextField(blank=True)
    is_field_staff = models.BooleanField(default=False, db_index=True)
    is_office_staff = models.BooleanField(default=False, db_index=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to='team/', blank=True, null=True)
    linkedin_url = models.URLField(blank=True)
    email_public = models.EmailField(blank=True, help_text="Public-facing email")
    phone_public = models.CharField(max_length=20, blank=True, help_text="Public-facing phone")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.email

    class Meta:
        ordering = ['display_order']

class ProjectAssignment(UUIDPrimaryKeyMixin, TimestampMixin):
    project = models.ForeignKey(ExplorationProject, on_delete=models.CASCADE, related_name='assignments')
    personnel = models.ForeignKey(Personnel, on_delete=models.PROTECT)
    role = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_lead = models.BooleanField(default=False)

    class Meta:
        unique_together = [['project', 'personnel']]

# ===========================================================================
# SAMPLING & DRILLING
# ===========================================================================

class SampleType(UUIDPrimaryKeyMixin):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class SamplingProgram(UUIDPrimaryKeyMixin, TimestampMixin):
    project = models.ForeignKey(ExplorationProject, on_delete=models.CASCADE, related_name='sampling_programs')
    name = models.CharField(max_length=200)
    sample_type = models.ForeignKey(SampleType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    sample_count = models.PositiveIntegerField(blank=True, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.project.title} – {self.name}"

class Sample(UUIDPrimaryKeyMixin, TimestampMixin):
    program = models.ForeignKey(SamplingProgram, on_delete=models.CASCADE, related_name='samples')
    sample_id = models.CharField(max_length=50, unique=True, db_index=True)
    location_easting = models.FloatField(blank=True, null=True)
    location_northing = models.FloatField(blank=True, null=True)
    elevation = models.FloatField(blank=True, null=True)
    depth_from = models.FloatField(blank=True, null=True, help_text='m')
    depth_to = models.FloatField(blank=True, null=True, help_text='m')
    weight_kg = models.FloatField(blank=True, null=True)
    notes = models.TextField(blank=True)
    assay_result = models.JSONField(blank=True, null=True, help_text='Key-value store of element results')

    def __str__(self):
        return self.sample_id

    class Meta:
        ordering = ['sample_id']

class DrillHole(UUIDPrimaryKeyMixin, TimestampMixin):
    project = models.ForeignKey(ExplorationProject, on_delete=models.CASCADE, related_name='drill_holes')
    hole_id = models.CharField(max_length=50, unique=True, db_index=True)
    collar_easting = models.FloatField()
    collar_northing = models.FloatField()
    collar_elevation = models.FloatField(blank=True, null=True)
    azimuth = models.FloatField(blank=True, null=True, help_text='Degrees')
    dip = models.FloatField(blank=True, null=True, help_text='Degrees from horizontal')
    total_depth = models.FloatField(help_text='m')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    drill_rig = models.ForeignKey(Instrument, on_delete=models.SET_NULL, null=True, blank=True, related_name='drill_holes')
    logs = models.FileField(upload_to='drilling/logs/', blank=True, null=True)

    def __str__(self):
        return self.hole_id

    class Meta:
        ordering = ['hole_id']

class DrillLogEntry(UUIDPrimaryKeyMixin, TimestampMixin):
    drill_hole = models.ForeignKey(DrillHole, on_delete=models.CASCADE, related_name='log_entries')
    from_depth = models.FloatField()
    to_depth = models.FloatField()
    lithology = models.CharField(max_length=100, blank=True)
    mineralisation = models.TextField(blank=True)
    recovery = models.FloatField(blank=True, null=True, help_text='%')
    assays = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.drill_hole.hole_id} – {self.from_depth}-{self.to_depth}m"

    class Meta:
        ordering = ['from_depth']

# ===========================================================================
# RESOURCE ESTIMATION
# ===========================================================================

class ResourceEstimate(UUIDPrimaryKeyMixin, TimestampMixin):
    project = models.ForeignKey(ExplorationProject, on_delete=models.CASCADE, related_name='resource_estimates')
    report = models.ForeignKey('Report', on_delete=models.CASCADE, null=True, blank=True)
    commodity = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=[
        ('inferred', 'Inferred'),
        ('indicated', 'Indicated'),
        ('measured', 'Measured'),
    ], db_index=True)
    tonnage = models.FloatField(help_text='Million tonnes (Mt)')
    grade = models.FloatField(help_text='Grade (e.g., g/t, %)')
    contained_metal = models.FloatField(blank=True, null=True)
    effective_date = models.DateField(db_index=True)
    confidence = models.CharField(max_length=50, blank=True, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ])
    is_public = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return f"{self.project.title} – {self.commodity} ({self.category})"

    class Meta:
        ordering = ['-effective_date']

# ===========================================================================
# REPORTS & DELIVERABLES
# ===========================================================================

class Report(UUIDPrimaryKeyMixin, SlugMixin, TimestampMixin):
    REPORT_TYPES = [
        ('technical', 'Technical Report'),
        ('summary', 'Executive Summary'),
        ('data', 'Data Release'),
        ('proposal', 'Proposal'),
        ('presentation', 'Presentation'),
        ('investor', 'Investor Presentation'),
        ('sustainability', 'Sustainability Report'),
        ('other', 'Other'),
    ]
    project = models.ForeignKey(ExplorationProject, on_delete=models.CASCADE, related_name='reports')
    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, default='technical', db_index=True)
    file = models.FileField(upload_to='reports/')
    file_size = models.PositiveIntegerField(blank=True, null=True, help_text='KB')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    publication_date = models.DateField(db_index=True)
    is_public = models.BooleanField(default=True, db_index=True)
    download_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-publication_date']

# ===========================================================================
# NEWS / OPERATIONS (With Scheduled Publishing)
# ===========================================================================

class NewsCategory(UUIDPrimaryKeyMixin):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class NewsArticle(UUIDPrimaryKeyMixin, SlugMixin, PublishableMixin, TimestampMixin):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(NewsCategory, on_delete=models.PROTECT, related_name='articles')
    image = models.ImageField(upload_to='news/', blank=True, null=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    
    def get_absolute_url(self):
        return reverse('geo:news_detail', kwargs={'slug': self.slug})

    class Meta:
        ordering = ['-publish_at']

# ===========================================================================
# CAREERS (JOBS)
# ===========================================================================

class JobCategory(UUIDPrimaryKeyMixin):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class JobPosting(UUIDPrimaryKeyMixin, SlugMixin, PublishableMixin, TimestampMixin):
    JOB_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('fly_in_fly_out', 'Fly‑In‑Fly‑Out'),
    ]
    EXPERIENCE_CHOICES = [
        ('entry', 'Entry Level'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior'),
        ('manager', 'Manager'),
        ('executive', 'Executive'),
    ]
    title = models.CharField(max_length=200)
    category = models.ForeignKey(JobCategory, on_delete=models.PROTECT, related_name='jobs')
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default='full_time', db_index=True)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, default='mid')
    location = models.CharField(max_length=200, blank=True)
    department = models.CharField(max_length=100, blank=True, help_text="e.g., Geophysics, Drilling")
    description = models.TextField()
    requirements = models.TextField(blank=True)
    responsibilities = models.TextField(blank=True)
    salary_range = models.CharField(max_length=100, blank=True)
    application_deadline = models.DateField(db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_remote = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)

    def get_absolute_url(self):
        return reverse('geo:job_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

class JobApplication(UUIDPrimaryKeyMixin, TimestampMixin):
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    resume = models.FileField(upload_to='applications/resumes/')
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[
        ('received', 'Received'),
        ('reviewed', 'Reviewed'),
        ('shortlisted', 'Shortlisted'),
        ('interviewed', 'Interviewed'),
        ('offered', 'Offered'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    ], default='received', db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

# ===========================================================================
# POLICIES (HSE, GOVERNANCE, SUSTAINABILITY)
# ===========================================================================

class Policy(UUIDPrimaryKeyMixin, SlugMixin, TimestampMixin):
    POLICY_TYPES = [
        ('hse', 'Health, Safety & Environment'),
        ('governance', 'Corporate Governance'),
        ('conduct', 'Code of Conduct'),
        ('privacy', 'Privacy Policy'),
        ('terms', 'Terms of Use'),
        ('sustainability', 'Sustainability Policy'),
        ('other', 'Other'),
    ]
    title = models.CharField(max_length=200)
    policy_type = models.CharField(max_length=20, choices=POLICY_TYPES, default='hse', db_index=True)
    content = models.TextField()
    version = models.CharField(max_length=20, blank=True)
    effective_date = models.DateField(db_index=True)
    last_reviewed = models.DateField()
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-effective_date']

# ===========================================================================
# SUSTAINABILITY REPORTS (ESG)
# ===========================================================================

class SustainabilityReport(UUIDPrimaryKeyMixin, TimestampMixin):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, db_index=True)
    summary = models.TextField(blank=True)
    report_file = models.FileField(upload_to='sustainability/', blank=True, null=True)
    initiatives = models.TextField(blank=True, help_text="Key sustainability initiatives taken this year")
    carbon_footprint = models.FloatField(blank=True, null=True, help_text='tCO2e')
    energy_consumption = models.FloatField(blank=True, null=True, help_text='MWh')
    water_usage = models.FloatField(blank=True, null=True, help_text='m³')
    waste_recycled = models.FloatField(blank=True, null=True, help_text='%')
    community_investment = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text='USD')
    publication_date = models.DateField(db_index=True)
    is_public = models.BooleanField(default=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-publication_date']

# ===========================================================================
# DOCUMENT REPOSITORY
# ===========================================================================

class Document(UUIDPrimaryKeyMixin, SlugMixin, TimestampMixin):
    DOCUMENT_TYPES = [
        ('brochure', 'Brochure'),
        ('fact_sheet', 'Fact Sheet'),
        ('presentation', 'Presentation'),
        ('technical', 'Technical Document'),
        ('investor', 'Investor Document'),
        ('sustainability', 'Sustainability Document'),
        ('other', 'Other'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='documents/')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='other', db_index=True)
    is_public = models.BooleanField(default=True, db_index=True)
    download_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

# ===========================================================================
# GALLERY
# ===========================================================================

class GalleryImage(UUIDPrimaryKeyMixin, TimestampMixin):
    CATEGORY_CHOICES = [
        ('fieldwork', 'Fieldwork'),
        ('equipment', 'Equipment'),
        ('team', 'Team'),
        ('office', 'Office'),
        ('event', 'Event'),
        ('other', 'Other'),
    ]
    title = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='gallery/')
    caption = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='fieldwork', db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-created_at']

# ===========================================================================
# EVENTS
# ===========================================================================

class Event(UUIDPrimaryKeyMixin, SlugMixin, PublishableMixin, TimestampMixin):
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='events/', blank=True, null=True)
    is_online = models.BooleanField(default=False)
    registration_url = models.URLField(blank=True)

    class Meta:
        ordering = ['start_date']

# ===========================================================================
# CONTACT MESSAGES
# ===========================================================================

class ContactMessage(UUIDPrimaryKeyMixin, TimestampMixin):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    replied = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

# ===========================================================================
# TESTIMONIALS
# ===========================================================================

class Testimonial(UUIDPrimaryKeyMixin, TimestampMixin):
    author = models.CharField(max_length=100)
    role = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=100, blank=True)
    content = models.TextField()
    image = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-created_at']

# ===========================================================================
# AWARDS & ACCREDITATIONS
# ===========================================================================

class Award(UUIDPrimaryKeyMixin, TimestampMixin):
    title = models.CharField(max_length=200)
    issuing_body = models.CharField(max_length=200, blank=True)
    year = models.PositiveIntegerField(db_index=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='awards/', blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-year', 'display_order']

# ===========================================================================
# PARTNERS & AFFILIATIONS
# ===========================================================================

class Partner(UUIDPrimaryKeyMixin, TimestampMixin):
    PARTNER_TYPES = [
        ('joint_venture', 'Joint Venture'),
        ('subcontractor', 'Subcontractor'),
        ('industry_body', 'Industry Body'),
        ('research', 'Research Institution'),
        ('supplier', 'Supplier'),
        ('other', 'Other'),
    ]
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, db_index=True)
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPES, default='other', db_index=True)
    logo = models.ImageField(upload_to='partners/', blank=True, null=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['display_order']

# ===========================================================================
# CASE STUDIES (Marketing success stories)
# ===========================================================================

class CaseStudy(UUIDPrimaryKeyMixin, SlugMixin, PublishableMixin, TimestampMixin):
    project = models.ForeignKey(ExplorationProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='case_studies')
    title = models.CharField(max_length=200)
    client_name = models.CharField(max_length=200, blank=True)
    challenge = models.TextField()
    solution = models.TextField()
    result = models.TextField()
    featured_image = models.ImageField(upload_to='case_studies/', blank=True, null=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = 'Case Studies'
        ordering = ['-created_at']

# ===========================================================================
# FAQ
# ===========================================================================

class FAQCategory(UUIDPrimaryKeyMixin):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'FAQ Categories'

class FAQ(UUIDPrimaryKeyMixin, TimestampMixin):
    category = models.ForeignKey(FAQCategory, on_delete=models.PROTECT, related_name='faqs')
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return self.question

    class Meta:
        ordering = ['category', 'order']

# ===========================================================================
# NEWSLETTER SUBSCRIBERS
# ===========================================================================

class Subscriber(UUIDPrimaryKeyMixin, TimestampMixin):
    email = models.EmailField(unique=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return self.email

# ===========================================================================
# SITE ALERTS (NEW - Emergency / UX banners)
# ===========================================================================

class SiteAlert(UUIDPrimaryKeyMixin, TimestampMixin):
    ALERT_TYPES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('danger', 'Emergency'),
        ('success', 'Success'),
    ]
    title = models.CharField(max_length=200)
    message = models.TextField()
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, default='info')
    start_date = models.DateTimeField(default=timezone.now, db_index=True)
    end_date = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_dismissible = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-start_date']

# ===========================================================================
# DYNAMIC PAGES (With Versioning)
# ===========================================================================

class Page(UUIDPrimaryKeyMixin, SlugMixin, PublishableMixin, TimestampMixin):
    TEMPLATE_CHOICES = [
        ('default', 'Default'),
        ('full_width', 'Full Width'),
        ('sidebar_left', 'Sidebar Left'),
        ('sidebar_right', 'Sidebar Right'),
        ('landing', 'Landing Page'),
    ]
    title = models.CharField(max_length=200)
    content = models.TextField(help_text='Use HTML or a rich text editor (e.g., CKEditor)')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    template = models.CharField(max_length=50, choices=TEMPLATE_CHOICES, default='default')
    featured_image = models.ImageField(upload_to='pages/', blank=True, null=True)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=200, blank=True)
    in_nav = models.BooleanField(default=False, help_text='Show in main navigation')
    nav_order = models.PositiveIntegerField(default=0)
    
    # Versioning fields
    version_number = models.PositiveIntegerField(default=1)
    last_edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def get_absolute_url(self):
        return reverse('geo:page_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['nav_order', 'title']

class PageRevision(UUIDPrimaryKeyMixin, TimestampMixin):
    """Stores historical versions of Page content for rollback."""
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='revisions')
    content = models.TextField()
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=200, blank=True)
    version_number = models.PositiveIntegerField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    revision_note = models.CharField(max_length=255, blank=True, help_text="Short note on what changed")

    class Meta:
        ordering = ['-version_number']
        unique_together = [['page', 'version_number']]

    def __str__(self):
        return f"{self.page.title} - v{self.version_number}"

class PageAttachment(UUIDPrimaryKeyMixin, TimestampMixin):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='attachments')
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='page_attachments/')
    description = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.page.title} – {self.title}"

    class Meta:
        ordering = ['order']

# ===========================================================================
# HERO SLIDES (Homepage carousel)
# ===========================================================================

class HeroSlide(UUIDPrimaryKeyMixin, TimestampMixin):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to='hero/')
    cta_text = models.CharField(max_length=50, blank=True)
    cta_url = models.CharField(max_length=255, blank=True, help_text="Relative or absolute URL")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['order']

# ===========================================================================
# URL REDIRECTS (SEO)
# ===========================================================================

class Redirect(UUIDPrimaryKeyMixin, TimestampMixin):
    old_path = models.CharField(max_length=255, unique=True, db_index=True, help_text="Absolute path, e.g., /old-page/")
    new_path = models.CharField(max_length=255, help_text="Absolute path, e.g., /new-page/")
    is_permanent = models.BooleanField(default=True, help_text="301 (permanent) vs 302 (temporary)")
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.old_path} → {self.new_path}"

    class Meta:
        ordering = ['old_path']

# ===========================================================================
# CMS / SITE CONFIGURATION
# ===========================================================================

class SiteConfig(UUIDPrimaryKeyMixin, TimestampMixin):
    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.key

    class Meta:
        verbose_name_plural = 'Site Configurations'

class MenuItem(UUIDPrimaryKeyMixin, SlugMixin, TimestampMixin):
    title = models.CharField(max_length=100)
    url = models.CharField(max_length=255, blank=True)
    route_name = models.CharField(max_length=100, blank=True)
    page = models.ForeignKey(Page, on_delete=models.SET_NULL, null=True, blank=True, related_name='menu_items')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    new_window = models.BooleanField(default=False)
    css_class = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['order']
        verbose_name_plural = 'Menu Items'

    def __str__(self):
        return self.title

class SEOMetadata(UUIDPrimaryKeyMixin, TimestampMixin):
    page_path = models.CharField(max_length=255, unique=True, db_index=True)
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    keywords = models.CharField(max_length=200, blank=True)
    og_image = models.ImageField(upload_to='seo/', blank=True, null=True)
    canonical_url = models.URLField(blank=True)
    robots = models.CharField(max_length=50, default='index, follow')

    class Meta:
        verbose_name_plural = 'SEO Metadata'

class ContentBlock(UUIDPrimaryKeyMixin, SlugMixin, TimestampMixin):
    """Reusable content components for landing pages."""
    page = models.ForeignKey(Page, on_delete=models.CASCADE, null=True, blank=True, related_name='blocks')
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='blocks/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title