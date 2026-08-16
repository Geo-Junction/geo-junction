# geo/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages

from django.db import models as django_models
from django.forms import Textarea

from . import models


# ===========================================================================
# Custom User Admin
# ===========================================================================

class UserProfileInline(admin.StackedInline):
    model = models.UserProfile
    can_delete = False
    verbose_name_plural = "User Profile"
    fk_name = 'user'
    fieldsets = (
        (None, {
            'fields': ('role', 'timezone', 'notification_preferences')
        }),
    )
    exclude = ('id',)


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = (
        'email', 'username', 'first_name', 'last_name',
        'is_active', 'is_staff', 'is_verified', 'last_activity'
    )
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'username', 'phone', 'job_title', 'department')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'last_activity')}),
        ('Verification', {'fields': ('is_verified',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )


admin.site.register(models.User, UserAdmin)


# ===========================================================================
# Base Admin Classes for Reuse
# ===========================================================================

class BaseModelAdmin(admin.ModelAdmin):
    """Common configuration for models with TimestampMixin."""
    readonly_fields = ('created_at', 'updated_at', 'id')
    save_on_top = True


class SlugAdmin(BaseModelAdmin):
    """For models with 'title', 'slug', and TimestampMixin."""
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = BaseModelAdmin.readonly_fields + ('slug',)


class NameSlugAdmin(admin.ModelAdmin):
    """For models with 'name' and 'slug' (no timestamps)."""
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('id',)
    save_on_top = True


class NameSlugAdminWithTimestamps(BaseModelAdmin):
    """For models with 'name', 'slug', and TimestampMixin."""
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = BaseModelAdmin.readonly_fields + ('slug',)


class SimpleAdmin(admin.ModelAdmin):
    """For models without slug or timestamps (e.g., SampleType)."""
    readonly_fields = ('id',)
    save_on_top = True


class PublishableAdmin(BaseModelAdmin):
    """For models with publishing fields (is_published, publish_at, expires_at)."""
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('is_published', 'publish_at')
    readonly_fields = BaseModelAdmin.readonly_fields + ('is_publicly_visible',)


# ===========================================================================
# Company Profile
# ===========================================================================

@admin.register(models.CompanyProfile)
class CompanyProfileAdmin(BaseModelAdmin):
    fieldsets = (
        ('Company Basics', {'fields': ('name', 'tagline', 'logo', 'banner')}),
        ('About Content', {'fields': ('mission', 'vision', 'history', 'core_values')}),
        ('Contact Details', {'fields': ('address', 'phone', 'email', 'website', 'map_embed')}),
        ('Social Media', {'fields': ('facebook', 'twitter', 'linkedin', 'instagram', 'youtube')}),
        ('SEO', {'fields': ('meta_title', 'meta_description', 'meta_keywords')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at', 'id')


# ===========================================================================
# Services
# ===========================================================================

@admin.register(models.ServiceCategory)
class ServiceCategoryAdmin(NameSlugAdmin):  # uses 'name' and 'slug', no timestamps
    list_display = ('name', 'slug', 'icon', 'order')
    list_editable = ('order',)
    search_fields = ('name',)
    ordering = ('order',)


@admin.register(models.Service)
class ServiceAdmin(NameSlugAdminWithTimestamps):  # uses 'name' and 'slug', has timestamps
    list_display = ('name', 'category', 'is_featured', 'is_active', 'order')
    list_filter = ('category', 'is_featured', 'is_active')
    search_fields = ('name', 'short_description', 'description')
    list_editable = ('order', 'is_featured', 'is_active')
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'category')}),
        ('Content', {'fields': ('short_description', 'description', 'icon', 'image')}),
        ('Display', {'fields': ('is_featured', 'is_active', 'order')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Clients and Projects
# ===========================================================================

@admin.register(models.Client)
class ClientAdmin(NameSlugAdminWithTimestamps):
    list_display = ('name', 'industry', 'is_active')
    list_filter = ('is_active', 'industry')
    search_fields = ('name', 'website')
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'logo', 'website')}),
        ('Details', {'fields': ('industry', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


class ProjectNoteInline(admin.TabularInline):
    model = models.ProjectNote
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('author', 'content', 'is_internal', 'created_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.author = request.user
        super().save_model(request, obj, form, change)


class ProjectTaskInline(admin.TabularInline):
    model = models.ProjectTask
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('title', 'assigned_to', 'due_date', 'status', 'created_by', 'completed_at')


class SurveyJobInline(admin.TabularInline):
    model = models.SurveyJob
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('method', 'start_date', 'end_date', 'line_km', 'is_completed')


class DrillHoleInline(admin.TabularInline):
    model = models.DrillHole
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('hole_id', 'total_depth', 'start_date', 'end_date')


class ResourceEstimateInline(admin.TabularInline):
    model = models.ResourceEstimate
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('commodity', 'category', 'tonnage', 'grade', 'effective_date', 'is_public')


@admin.register(models.ExplorationProject)
class ExplorationProjectAdmin(SlugAdmin):
    list_display = ('title', 'client', 'status', 'location', 'start_date', 'is_public', 'is_featured')
    list_filter = ('status', 'is_public', 'is_featured', 'client', 'services')
    search_fields = ('title', 'description', 'location', 'country')
    list_editable = ('status', 'is_public', 'is_featured')
    filter_horizontal = ('services',)
    raw_id_fields = ('client',)
    inlines = [ProjectNoteInline, ProjectTaskInline, SurveyJobInline, DrillHoleInline, ResourceEstimateInline]
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'client', 'services')}),
        ('Status & Location', {'fields': ('status', 'location', 'country', 'coordinates')}),
        ('Details', {'fields': ('description', 'image', 'start_date', 'end_date', 'budget', 'project_website')}),
        ('Visibility', {'fields': ('is_public', 'is_featured')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at', 'id')

    def view_on_site(self, obj):
        return obj.get_absolute_url()


# ===========================================================================
# Personnel & Assignments
# ===========================================================================

@admin.register(models.Personnel)
class PersonnelAdmin(BaseModelAdmin):
    list_display = ('user', 'specialisation', 'is_field_staff', 'is_office_staff', 'display_order', 'is_active')
    list_filter = ('is_field_staff', 'is_office_staff', 'is_active')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'specialisation', 'certifications')
    list_editable = ('display_order', 'is_active')
    fieldsets = (
        (None, {'fields': ('user', 'photo')}),
        ('Professional', {'fields': ('specialisation', 'years_experience', 'certifications', 'bio')}),
        ('Contact (Public)', {'fields': ('email_public', 'phone_public', 'linkedin_url')}),
        ('Role', {'fields': ('is_field_staff', 'is_office_staff', 'display_order', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(models.ProjectAssignment)
class ProjectAssignmentAdmin(BaseModelAdmin):
    list_display = ('project', 'personnel', 'role', 'start_date', 'end_date', 'is_lead')
    list_filter = ('is_lead', 'project', 'personnel')
    search_fields = ('project__title', 'personnel__user__email', 'role')
    fieldsets = (
        (None, {'fields': ('project', 'personnel', 'role', 'is_lead')}),
        ('Dates', {'fields': ('start_date', 'end_date')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Equipment (Fleet)
# ===========================================================================

@admin.register(models.Equipment)
class EquipmentAdmin(BaseModelAdmin):
    list_display = ('name', 'equipment_type', 'model', 'serial_number', 'is_operational', 'current_location')
    list_filter = ('equipment_type', 'is_operational')
    search_fields = ('name', 'model', 'serial_number', 'current_location')
    list_editable = ('is_operational',)
    fieldsets = (
        (None, {'fields': ('name', 'equipment_type', 'model', 'serial_number', 'image')}),
        ('Specs & Location', {'fields': ('specifications', 'current_location', 'purchase_date', 'is_operational')}),
        ('Notes', {'fields': ('notes',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Instruments & Survey Methods
# ===========================================================================

@admin.register(models.Instrument)
class InstrumentAdmin(BaseModelAdmin):
    list_display = ('instrument_type', 'model', 'serial_number', 'is_operational', 'calibration_date')
    list_filter = ('instrument_type', 'is_operational')
    search_fields = ('model', 'serial_number', 'notes')
    list_editable = ('is_operational',)
    fieldsets = (
        (None, {'fields': ('instrument_type', 'model', 'serial_number')}),
        ('Status', {'fields': ('is_operational', 'calibration_date', 'notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(models.SurveyMethod)
class SurveyMethodAdmin(NameSlugAdmin):  # no timestamps
    list_display = ('name', 'slug')
    search_fields = ('name', 'description')
    filter_horizontal = ('typical_instruments',)


@admin.register(models.SurveyJob)
class SurveyJobAdmin(BaseModelAdmin):
    list_display = ('project', 'method', 'start_date', 'end_date', 'line_km', 'is_completed', 'data_quality')
    list_filter = ('is_completed', 'data_quality', 'method')
    search_fields = ('project__title', 'method__name', 'survey_area', 'report_reference')
    filter_horizontal = ('instruments',)
    fieldsets = (
        (None, {'fields': ('project', 'method', 'instruments')}),
        ('Survey Details', {'fields': ('survey_area', 'line_km', 'stations', 'start_date', 'end_date')}),
        ('Results', {'fields': ('data_quality', 'report_reference', 'is_completed')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Offices
# ===========================================================================

@admin.register(models.Office)
class OfficeAdmin(NameSlugAdminWithTimestamps):
    list_display = ('name', 'phone', 'email', 'is_headquarters', 'is_active', 'display_order')
    list_filter = ('is_headquarters', 'is_active')
    search_fields = ('name', 'address', 'phone', 'email')
    list_editable = ('display_order', 'is_active')
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'image')}),
        ('Contact', {'fields': ('address', 'phone', 'email', 'map_embed')}),
        ('Settings', {'fields': ('is_headquarters', 'is_active', 'display_order')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Sampling & Drilling
# ===========================================================================

@admin.register(models.SampleType)
class SampleTypeAdmin(SimpleAdmin):  # no slug field
    list_display = ('name',)
    search_fields = ('name', 'description')


@admin.register(models.SamplingProgram)
class SamplingProgramAdmin(BaseModelAdmin):
    list_display = ('name', 'project', 'sample_type', 'start_date', 'end_date', 'sample_count')
    list_filter = ('sample_type', 'project')
    search_fields = ('name', 'project__title', 'description')
    fieldsets = (
        (None, {'fields': ('project', 'name', 'sample_type')}),
        ('Schedule', {'fields': ('start_date', 'end_date', 'sample_count')}),
        ('Description', {'fields': ('description',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


class SampleInline(admin.TabularInline):
    model = models.Sample
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('sample_id', 'depth_from', 'depth_to', 'weight_kg', 'assay_result')


@admin.register(models.Sample)
class SampleAdmin(BaseModelAdmin):
    list_display = ('sample_id', 'program', 'depth_from', 'depth_to', 'weight_kg')
    list_filter = ('program',)
    search_fields = ('sample_id', 'notes')
    formfield_overrides = {
        django_models.JSONField: {
            "widget": Textarea(attrs={"rows": 3}),
        },
    }
    fieldsets = (
        (None, {'fields': ('program', 'sample_id')}),
        ('Location', {'fields': ('location_easting', 'location_northing', 'elevation')}),
        ('Depth & Weight', {'fields': ('depth_from', 'depth_to', 'weight_kg')}),
        ('Results', {'fields': ('assay_result', 'notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(models.DrillHole)
class DrillHoleAdmin(BaseModelAdmin):
    list_display = ('hole_id', 'project', 'total_depth', 'start_date', 'end_date', 'drill_rig')
    list_filter = ('project',)
    search_fields = ('hole_id', 'project__title')
    fieldsets = (
        (None, {'fields': ('project', 'hole_id', 'drill_rig')}),
        ('Location', {'fields': ('collar_easting', 'collar_northing', 'collar_elevation')}),
        ('Geometry', {'fields': ('azimuth', 'dip', 'total_depth')}),
        ('Dates', {'fields': ('start_date', 'end_date')}),
        ('Files', {'fields': ('logs',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


class DrillLogEntryInline(admin.TabularInline):
    model = models.DrillLogEntry
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('from_depth', 'to_depth', 'lithology', 'mineralisation', 'recovery', 'assays')


@admin.register(models.DrillLogEntry)
class DrillLogEntryAdmin(BaseModelAdmin):
    list_display = ('drill_hole', 'from_depth', 'to_depth', 'lithology', 'recovery')
    list_filter = ('drill_hole',)
    search_fields = ('drill_hole__hole_id', 'lithology', 'mineralisation')
    formfield_overrides = {
        django_models.JSONField: {
            "widget": Textarea(attrs={"rows": 3}),
        },
    }
    fieldsets = (
        (None, {'fields': ('drill_hole', 'from_depth', 'to_depth')}),
        ('Geology', {'fields': ('lithology', 'mineralisation', 'recovery')}),
        ('Assays', {'fields': ('assays',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Resource Estimates
# ===========================================================================

@admin.register(models.ResourceEstimate)
class ResourceEstimateAdmin(BaseModelAdmin):
    list_display = ('project', 'commodity', 'category', 'tonnage', 'grade', 'effective_date', 'is_public')
    list_filter = ('category', 'commodity', 'is_public', 'confidence')
    search_fields = ('project__title', 'commodity')
    fieldsets = (
        (None, {'fields': ('project', 'report', 'commodity', 'category')}),
        ('Estimation', {'fields': ('tonnage', 'grade', 'contained_metal', 'confidence')}),
        ('Dates', {'fields': ('effective_date', 'is_public')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Reports & Documents
# ===========================================================================

@admin.register(models.Report)
class ReportAdmin(SlugAdmin):
    list_display = ('title', 'project', 'report_type', 'publication_date', 'is_public', 'download_count')
    list_filter = ('report_type', 'is_public', 'project')
    search_fields = ('title', 'project__title', 'author__email')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'project', 'report_type')}),
        ('File', {'fields': ('file', 'file_size')}),
        ('Metadata', {'fields': ('author', 'publication_date', 'is_public', 'download_count')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(models.Document)
class DocumentAdmin(SlugAdmin):
    list_display = ('title', 'document_type', 'is_public', 'download_count', 'created_at')
    list_filter = ('document_type', 'is_public')
    search_fields = ('title', 'description')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'document_type', 'file')}),
        ('Details', {'fields': ('description', 'is_public', 'download_count')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# News
# ===========================================================================

@admin.register(models.NewsCategory)
class NewsCategoryAdmin(NameSlugAdmin):  # no timestamps
    list_display = ('name', 'slug')
    search_fields = ('name',)


@admin.register(models.NewsArticle)
class NewsArticleAdmin(PublishableAdmin):
    list_display = ('title', 'category', 'author', 'publish_at', 'is_published', 'is_featured')
    list_filter = ('category', 'is_published', 'is_featured', 'publish_at')
    search_fields = ('title', 'content', 'author__email')
    list_editable = ('is_published', 'is_featured')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'category', 'image')}),
        ('Content', {'fields': ('content',)}),
        ('Publishing', {'fields': ('is_published', 'publish_at', 'expires_at')}),
        ('Metadata', {'fields': ('author', 'is_featured')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.author = request.user if request.user.is_authenticated else None
        super().save_model(request, obj, form, change)


# ===========================================================================
# Careers
# ===========================================================================

@admin.register(models.JobCategory)
class JobCategoryAdmin(NameSlugAdmin):  # no timestamps
    list_display = ('name', 'slug')
    search_fields = ('name',)


@admin.register(models.JobPosting)
class JobPostingAdmin(PublishableAdmin):
    list_display = ('title', 'category', 'job_type', 'location', 'application_deadline', 'is_published', 'is_featured')
    list_filter = ('category', 'job_type', 'experience_level', 'is_published', 'is_featured', 'is_remote')
    search_fields = ('title', 'location', 'description', 'department')
    list_editable = ('is_published', 'is_featured')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'category', 'job_type', 'experience_level')}),
        ('Location & Department', {'fields': ('location', 'department', 'is_remote')}),
        ('Description', {'fields': ('description', 'requirements', 'responsibilities', 'salary_range')}),
        ('Publishing', {'fields': ('is_published', 'publish_at', 'expires_at', 'application_deadline')}),
        ('Metrics', {'fields': ('is_featured', 'views')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(models.JobApplication)
class JobApplicationAdmin(BaseModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'job', 'status', 'created_at')
    list_filter = ('status', 'job')
    search_fields = ('first_name', 'last_name', 'email', 'phone')
    list_editable = ('status',)
    fieldsets = (
        (None, {'fields': ('job', 'first_name', 'last_name', 'email', 'phone')}),
        ('Application', {'fields': ('resume', 'cover_letter', 'status', 'notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    @admin.action(description='Mark selected as Shortlisted')
    def mark_shortlisted(self, request, queryset):
        updated = queryset.update(status='shortlisted')
        self.message_user(request, f'{updated} applications marked as shortlisted.')

    @admin.action(description='Mark selected as Rejected')
    def mark_rejected(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} applications rejected.')

    actions = [mark_shortlisted, mark_rejected]


# ===========================================================================
# Policies
# ===========================================================================

@admin.register(models.Policy)
class PolicyAdmin(SlugAdmin):
    list_display = ('title', 'policy_type', 'effective_date', 'version', 'is_active')
    list_filter = ('policy_type', 'is_active')
    search_fields = ('title', 'content')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'policy_type', 'content')}),
        ('Versioning', {'fields': ('version', 'effective_date', 'last_reviewed', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Sustainability Reports
# ===========================================================================

@admin.register(models.SustainabilityReport)
class SustainabilityReportAdmin(SlugAdmin):
    list_display = ('title', 'publication_date', 'is_public')
    list_filter = ('is_public', 'publication_date')
    search_fields = ('title', 'summary', 'initiatives')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'summary', 'report_file')}),
        ('Initiatives', {'fields': ('initiatives',)}),
        ('Metrics', {'fields': ('carbon_footprint', 'energy_consumption', 'water_usage', 'waste_recycled', 'community_investment')}),
        ('Publishing', {'fields': ('publication_date', 'is_public')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Gallery
# ===========================================================================

@admin.register(models.GalleryImage)
class GalleryImageAdmin(BaseModelAdmin):
    list_display = ('title', 'category', 'is_featured', 'created_at')
    list_filter = ('category', 'is_featured')
    search_fields = ('title', 'caption')
    list_editable = ('is_featured',)
    fieldsets = (
        (None, {'fields': ('title', 'image', 'caption', 'category', 'is_featured')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Events
# ===========================================================================

@admin.register(models.Event)
class EventAdmin(PublishableAdmin):
    list_display = ('title', 'start_date', 'end_date', 'location', 'is_online', 'is_published')
    list_filter = ('is_published', 'is_online', 'start_date')
    search_fields = ('title', 'description', 'location')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'description', 'image')}),
        ('Event Details', {'fields': ('start_date', 'end_date', 'location', 'is_online', 'registration_url')}),
        ('Publishing', {'fields': ('is_published', 'publish_at', 'expires_at')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Contact, Testimonials, Awards, Partners, Case Studies, FAQs, Subscribers
# ===========================================================================

@admin.register(models.ContactMessage)
class ContactMessageAdmin(BaseModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at', 'is_read', 'replied')
    list_filter = ('is_read', 'replied')
    search_fields = ('name', 'email', 'subject', 'message')
    list_editable = ('is_read', 'replied')
    readonly_fields = ('created_at', 'updated_at', 'id')
    fieldsets = (
        (None, {'fields': ('name', 'email', 'subject', 'message')}),
        ('Status', {'fields': ('is_read', 'replied')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(models.Testimonial)
class TestimonialAdmin(BaseModelAdmin):
    list_display = ('author', 'company', 'is_featured', 'created_at')
    list_filter = ('is_featured',)
    search_fields = ('author', 'company', 'content')
    list_editable = ('is_featured',)
    fieldsets = (
        (None, {'fields': ('author', 'role', 'company', 'content', 'image', 'is_featured')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(models.Award)
class AwardAdmin(BaseModelAdmin):
    list_display = ('title', 'issuing_body', 'year', 'is_active', 'display_order')
    list_filter = ('is_active', 'year')
    search_fields = ('title', 'issuing_body', 'description')
    list_editable = ('display_order', 'is_active')
    fieldsets = (
        (None, {'fields': ('title', 'issuing_body', 'year', 'logo', 'description', 'is_active', 'display_order')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(models.Partner)
class PartnerAdmin(NameSlugAdminWithTimestamps):
    list_display = ('name', 'partner_type', 'is_active', 'display_order')
    list_filter = ('partner_type', 'is_active')
    search_fields = ('name', 'description', 'website')
    list_editable = ('display_order', 'is_active')
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'partner_type', 'logo', 'website')}),
        ('Description', {'fields': ('description', 'is_active', 'display_order')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(models.CaseStudy)
class CaseStudyAdmin(PublishableAdmin):
    list_display = ('title', 'client_name', 'project', 'is_published', 'is_featured')
    list_filter = ('is_published', 'is_featured')
    search_fields = ('title', 'client_name', 'challenge', 'solution')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'project', 'client_name', 'featured_image')}),
        ('Content', {'fields': ('challenge', 'solution', 'result')}),
        ('Publishing', {'fields': ('is_published', 'publish_at', 'expires_at', 'is_featured')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(models.FAQCategory)
class FAQCategoryAdmin(NameSlugAdmin):  # no timestamps
    list_display = ('name', 'slug')
    search_fields = ('name',)


@admin.register(models.FAQ)
class FAQAdmin(BaseModelAdmin):
    list_display = ('question', 'category', 'order', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('question', 'answer')
    list_editable = ('order', 'is_active')
    fieldsets = (
        (None, {'fields': ('category', 'question', 'answer', 'order', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(models.Subscriber)
class SubscriberAdmin(BaseModelAdmin):
    list_display = ('email', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('email',)
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at', 'id')
    fieldsets = (
        (None, {'fields': ('email', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Site Alerts
# ===========================================================================

@admin.register(models.SiteAlert)
class SiteAlertAdmin(BaseModelAdmin):
    list_display = ('title', 'alert_type', 'start_date', 'end_date', 'is_active', 'is_dismissible')
    list_filter = ('alert_type', 'is_active')
    search_fields = ('title', 'message')
    list_editable = ('is_active', 'is_dismissible')
    fieldsets = (
        (None, {'fields': ('title', 'message', 'alert_type')}),
        ('Schedule', {'fields': ('start_date', 'end_date', 'is_active')}),
        ('Behavior', {'fields': ('is_dismissible',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Dynamic Pages (with Versioning)
# ===========================================================================

class PageAttachmentInline(admin.TabularInline):
    model = models.PageAttachment
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('title', 'file', 'description', 'order')


class PageRevisionInline(admin.TabularInline):
    model = models.PageRevision
    extra = 0
    readonly_fields = ('version_number', 'created_at', 'created_by')
    fields = ('version_number', 'content', 'meta_title', 'meta_description', 'meta_keywords', 'revision_note')
    can_delete = False
    max_num = 0  # Show only existing revisions


@admin.register(models.Page)
class PageAdmin(PublishableAdmin):
    list_display = ('title', 'parent', 'template', 'is_published', 'publish_at', 'in_nav', 'version_number')
    list_filter = ('is_published', 'in_nav', 'template', 'parent')
    search_fields = ('title', 'content', 'meta_title', 'meta_description')
    list_editable = ('in_nav', 'is_published')
    inlines = [PageAttachmentInline, PageRevisionInline]
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'parent', 'template')}),
        ('Content', {'fields': ('content', 'featured_image')}),
        ('Publishing', {'fields': ('is_published', 'publish_at', 'expires_at', 'in_nav', 'nav_order')}),
        ('SEO', {'fields': ('meta_title', 'meta_description', 'meta_keywords')}),
        ('Versioning', {'fields': ('version_number', 'last_edited_by')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ('version_number', 'created_at', 'updated_at', 'id', 'is_publicly_visible')

    def save_model(self, request, obj, form, change):
        if change:
            # Create a revision if content or meta changed
            if obj.pk:
                old = models.Page.objects.get(pk=obj.pk)
                if (old.content != obj.content or
                    old.meta_title != obj.meta_title or
                    old.meta_description != obj.meta_description or
                    old.meta_keywords != obj.meta_keywords):
                    # Save revision
                    models.PageRevision.objects.create(
                        page=obj,
                        content=old.content,
                        meta_title=old.meta_title,
                        meta_description=old.meta_description,
                        meta_keywords=old.meta_keywords,
                        version_number=obj.version_number,
                        created_by=request.user if request.user.is_authenticated else None,
                        revision_note=f"Auto-revision by {request.user.email}"
                    )
                    obj.version_number += 1
            obj.last_edited_by = request.user if request.user.is_authenticated else None
        super().save_model(request, obj, form, change)


@admin.register(models.PageRevision)
class PageRevisionAdmin(BaseModelAdmin):
    list_display = ('page', 'version_number', 'created_by', 'created_at')
    list_filter = ('page',)
    search_fields = ('page__title', 'revision_note', 'content')
    readonly_fields = ('page', 'content', 'meta_title', 'meta_description', 'meta_keywords', 'version_number', 'created_at', 'created_by')
    fieldsets = (
        (None, {'fields': ('page', 'version_number', 'revision_note')}),
        ('Content', {'fields': ('content', 'meta_title', 'meta_description', 'meta_keywords')}),
        ('Metadata', {'fields': ('created_by', 'created_at')}),
    )


# ===========================================================================
# Hero Slides
# ===========================================================================

@admin.register(models.HeroSlide)
class HeroSlideAdmin(BaseModelAdmin):
    list_display = ('title', 'order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'subtitle', 'cta_text')
    list_editable = ('order', 'is_active')
    fieldsets = (
        (None, {'fields': ('title', 'subtitle', 'image')}),
        ('Call to Action', {'fields': ('cta_text', 'cta_url')}),
        ('Display', {'fields': ('order', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Redirects
# ===========================================================================

@admin.register(models.Redirect)
class RedirectAdmin(BaseModelAdmin):
    list_display = ('old_path', 'new_path', 'is_permanent', 'active')
    list_filter = ('is_permanent', 'active')
    search_fields = ('old_path', 'new_path')
    list_editable = ('is_permanent', 'active')
    fieldsets = (
        (None, {'fields': ('old_path', 'new_path', 'is_permanent', 'active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# CMS (SiteConfig, MenuItem, SEOMetadata, ContentBlock)
# ===========================================================================

@admin.register(models.SiteConfig)
class SiteConfigAdmin(BaseModelAdmin):
    list_display = ('key', 'value_preview', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('key', 'value', 'description')
    list_editable = ('is_active',)
    fieldsets = (
        (None, {'fields': ('key', 'value', 'is_active', 'description')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    def value_preview(self, obj):
        return obj.value[:50] + '...' if len(obj.value) > 50 else obj.value
    value_preview.short_description = 'Value'


@admin.register(models.MenuItem)
class MenuItemAdmin(SlugAdmin):  # uses 'title', has timestamps
    list_display = ('title', 'parent', 'order', 'is_active', 'new_window')
    list_filter = ('is_active', 'new_window')
    search_fields = ('title', 'url', 'route_name', 'css_class')
    list_editable = ('order', 'is_active', 'new_window')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'parent', 'order')}),
        ('Link', {'fields': ('url', 'route_name', 'page')}),
        ('Display', {'fields': ('is_active', 'new_window', 'css_class')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(models.SEOMetadata)
class SEOMetadataAdmin(BaseModelAdmin):
    list_display = ('page_path', 'title', 'description_preview', 'canonical_url')
    search_fields = ('page_path', 'title', 'description', 'keywords')
    fieldsets = (
        (None, {'fields': ('page_path', 'title', 'description', 'keywords')}),
        ('Social', {'fields': ('og_image',)}),
        ('Advanced', {'fields': ('canonical_url', 'robots')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    def description_preview(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_preview.short_description = 'Description'


@admin.register(models.ContentBlock)
class ContentBlockAdmin(SlugAdmin):
    list_display = ('title', 'page', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'content')
    list_editable = ('order', 'is_active')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'page', 'content', 'image', 'order', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


# ===========================================================================
# Audit Log (Read-only)
# ===========================================================================

@admin.register(models.AuditLog)
class AuditLogAdmin(BaseModelAdmin):
    list_display = ('user', 'action', 'model_name', 'object_repr', 'created_at', 'ip_address')
    list_filter = ('action', 'model_name', 'created_at')
    search_fields = ('user__email', 'object_repr', 'object_id', 'ip_address')
    readonly_fields = (
        'user', 'action', 'model_name', 'object_id', 'object_repr',
        'changes', 'ip_address', 'user_agent', 'created_at', 'updated_at', 'id'
    )
    fieldsets = (
        (None, {'fields': ('user', 'action', 'model_name', 'object_id', 'object_repr')}),
        ('Details', {'fields': ('changes', 'ip_address', 'user_agent')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False