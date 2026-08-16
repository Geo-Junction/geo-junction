# geo/views.py

"""
Geo‑Junction – Main Views
Enhanced with pagination, caching, RBAC, email verification, rate limiting, and logging.
Complete view layer for the corporate website.
"""

import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Q, Count, Avg, Prefetch
from django.db import transaction
from django.http import Http404, FileResponse, HttpResponse, JsonResponse
from django.utils import timezone
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.vary import vary_on_headers, vary_on_cookie
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import uuid

from .models import (
    # Core
    User, UserProfile,
    
    # Content
    CompanyProfile, Service, ServiceCategory,
    Client, ExplorationProject, ProjectNote, ProjectTask,
    Equipment, Instrument, SurveyMethod, SurveyJob,
    Office, Personnel, ProjectAssignment,
    SampleType, SamplingProgram, Sample, DrillHole, DrillLogEntry,
    ResourceEstimate, Report, Document,
    NewsCategory, NewsArticle,
    JobCategory, JobPosting, JobApplication,
    Policy, SustainabilityReport,
    GalleryImage, Event,
    ContactMessage, Testimonial, Award, Partner,
    CaseStudy, FAQCategory, FAQ, Subscriber,
    SiteAlert, Page, PageRevision, PageAttachment,
    HeroSlide, Redirect, SiteConfig, MenuItem, SEOMetadata, ContentBlock,
)

from .forms import (
    ContactForm, JobApplicationForm, SubscriberForm,
    UserRegistrationForm, CustomAuthenticationForm,
    UserProfileForm, UserProfileSettingsForm,
    ProjectFilterForm, NewsFilterForm, JobFilterForm,
    SearchForm
)

# Set up logging
logger = logging.getLogger(__name__)

User = get_user_model()


# ==============================================================
# UTILITY FUNCTIONS
# ==============================================================

def paginate_queryset(request, queryset, per_page=12, allow_empty=True):
    """Reusable pagination utility."""
    paginator = Paginator(queryset, per_page)
    page = request.GET.get('page')
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        if allow_empty:
            page_obj = paginator.page(paginator.num_pages)
        else:
            raise Http404("Page does not exist")
    return page_obj


def get_breadcrumbs(request):
    """Generate breadcrumbs from request path."""
    path = request.path
    crumbs = [{'title': 'Home', 'url': reverse('geo:home')}]
    parts = path.strip('/').split('/')
    current_path = ''
    for part in parts:
        if part:
            current_path += f'/{part}'
            crumbs.append({
                'title': part.replace('-', ' ').title(),
                'url': current_path
            })
    return crumbs


def send_verification_email(request, user):
    """Send email verification link."""
    current_site = get_current_site(request)
    mail_subject = 'Verify your Geo‑Junction account'
    message = render_to_string('geo/auth/verification_email.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
    })
    try:
        send_mail(mail_subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        logger.info(f"Verification email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")


# ==============================================================
# DECORATORS FOR ROLE-BASED ACCESS
# ==============================================================

def role_required(allowed_roles=[]):
    """Decorator to restrict access to specific roles."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("You must be logged in to access this page.")
            try:
                profile = request.user.profile
                if profile.role not in allowed_roles:
                    raise PermissionDenied(f"Access denied. Required roles: {', '.join(allowed_roles)}")
            except UserProfile.DoesNotExist:
                raise PermissionDenied("User profile not found.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def viewer_required(view_func):
    """Allow access to all authenticated users (viewers and above)."""
    return role_required(['viewer', 'geologist', 'surveyor', 'project_manager', 'admin', 'super_admin'])(view_func)


def staff_required(view_func):
    """Allow access to staff roles only."""
    return role_required(['geologist', 'surveyor', 'project_manager', 'admin', 'super_admin'])(view_func)


def admin_required(view_func):
    """Allow access to admin roles only."""
    return role_required(['admin', 'super_admin'])(view_func)


# ==============================================================
# 1. PUBLIC VIEWS (No Authentication Required)
# ==============================================================

@cache_page(60 * 15)  # Cache for 15 minutes
@vary_on_headers('Cookie')
def home(request):
    """Homepage with hero slides, featured content, and stats."""
    # Hero slides
    hero_slides = HeroSlide.objects.filter(is_active=True).order_by('order')
    
    # Featured services
    featured_services = Service.objects.filter(
        is_active=True,
        is_featured=True
    ).select_related('category')[:6]
    
    # Featured projects
    featured_projects = ExplorationProject.objects.filter(
        is_public=True,
        is_featured=True
    ).select_related('client')[:6]
    
    # Latest news
    latest_news = NewsArticle.objects.filter(
        is_published=True,
        publish_at__lte=timezone.now()
    ).order_by('-publish_at')[:3]
    
    # Statistics
    stats = {
        'projects': ExplorationProject.objects.filter(is_public=True).count(),
        'clients': Client.objects.filter(is_active=True).count(),
        'offices': Office.objects.filter(is_active=True).count(),
        'team': Personnel.objects.filter(is_active=True).count(),
    }
    
    # Featured testimonials
    testimonials = Testimonial.objects.filter(is_featured=True)[:3]
    
    # Site alerts
    site_alerts = SiteAlert.objects.filter(
        is_active=True,
        start_date__lte=timezone.now()
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=timezone.now())
    )
    
    context = {
        'page_title': 'Geo‑Junction – Geophysical Exploration & Mining Services',
        'meta_description': 'World-class geophysical exploration, surveying, and mining consultancy services. Trusted by leading mining companies worldwide.',
        'hero_slides': hero_slides,
        'featured_services': featured_services,
        'featured_projects': featured_projects,
        'latest_news': latest_news,
        'stats': stats,
        'testimonials': testimonials,
        'site_alerts': site_alerts,
        'breadcrumbs': [{'title': 'Home', 'url': '/'}],
    }
    return render(request, 'geo/pages/home.html', context)


def about(request):
    """About page with company profile and team highlights."""
    profile = CompanyProfile.objects.first()
    if not profile:
        profile = CompanyProfile.objects.create(name='Geo‑Junction')
    
    # Team members
    team = Personnel.objects.filter(is_active=True).select_related('user').order_by('display_order')[:12]
    
    # Awards
    awards = Award.objects.filter(is_active=True).order_by('-year', 'display_order')
    
    # Partners
    partners = Partner.objects.filter(is_active=True).order_by('display_order')
    
    context = {
        'page_title': 'About Us – Geo‑Junction',
        'meta_description': profile.meta_description or 'Learn about Geo‑Junction\'s history, mission, and expert team of geophysicists and geologists.',
        'profile': profile,
        'team': team,
        'awards': awards,
        'partners': partners,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/pages/about.html', context)


def contact(request):
    """Contact page with form and office locations."""
    # Rate limiting check (5 minutes between submissions)
    last_submit = request.session.get('last_contact_submit')
    if request.method == 'POST' and last_submit:
        if (timezone.now() - last_submit).total_seconds() < 300:
            messages.error(request, 'You have already sent a message. Please wait 5 minutes.')
            return redirect('geo:contact')
    
    if request.method == 'POST':
        form = ContactForm(request.POST, user=request.user if request.user.is_authenticated else None)
        if form.is_valid():
            try:
                message = form.save()
                
                # Send email notification
                send_mail(
                    subject=f"Geo‑Junction Contact: {message.subject}",
                    message=f"From: {message.name} ({message.email})\n\n{message.message}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.CONTACT_EMAIL],
                    fail_silently=False,
                )
                
                # Store submission time for rate limiting
                request.session['last_contact_submit'] = timezone.now()
                
                messages.success(request, 'Your message has been sent! We\'ll get back to you soon.')
                return redirect('geo:contact')
            except Exception as e:
                logger.error(f"Contact form submission failed: {e}")
                messages.error(request, 'There was an error sending your message. Please try again later.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ContactForm(user=request.user if request.user.is_authenticated else None)
    
    offices = Office.objects.filter(is_active=True).order_by('display_order')
    profile = CompanyProfile.objects.first()
    
    context = {
        'page_title': 'Contact Us – Geo‑Junction',
        'meta_description': 'Get in touch with Geo‑Junction for geophysical exploration, surveying, and mining consultancy services.',
        'form': form,
        'offices': offices,
        'profile': profile,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/pages/contact.html', context)


# ==============================================================
# 2. SERVICES VIEWS
# ==============================================================

def service_list(request):
    """List all services with pagination and filtering."""
    services = Service.objects.filter(is_active=True).select_related('category')
    
    # Search
    q = request.GET.get('q')
    if q:
        services = services.filter(
            Q(name__icontains=q) | 
            Q(short_description__icontains=q) |
            Q(description__icontains=q)
        )
    
    # Filter by category
    category_slug = request.GET.get('category')
    if category_slug:
        services = services.filter(category__slug=category_slug)
    
    # Pagination
    page_obj = paginate_queryset(request, services, per_page=9)
    
    # Featured services (outside pagination)
    featured_services = Service.objects.filter(is_active=True, is_featured=True)[:6]
    
    # All categories for filter dropdown
    categories = ServiceCategory.objects.all()
    
    context = {
        'page_title': 'Our Services – Geo‑Junction',
        'meta_description': 'Geo‑Junction provides magnetometry, gravity surveys, resistivity, electromagnetics, radiometrics, and GIS integration services.',
        'page_obj': page_obj,
        'categories': categories,
        'featured_services': featured_services,
        'breadcrumbs': get_breadcrumbs(request),
        'current_category': category_slug,
        'search_query': q,
    }
    return render(request, 'geo/services/list.html', context)


@cache_page(60 * 15)
def service_detail(request, slug):
    """Detailed view of a single service."""
    try:
        service = get_object_or_404(
            Service.objects.select_related('category'),
            slug=slug,
            is_active=True
        )
    except Service.DoesNotExist:
        logger.warning(f"Service not found: {slug}")
        raise Http404("Service not found or inactive.")
    
    # Related services in same category
    related = Service.objects.filter(
        category=service.category,
        is_active=True
    ).exclude(id=service.id)[:4]
    
    # Meta description
    meta_description = service.meta_description or service.short_description or f"Learn about {service.name} – Geo‑Junction's geophysical exploration service."
    
    context = {
        'page_title': f"{service.name} – Geo‑Junction",
        'meta_description': meta_description,
        'service': service,
        'related': related,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/services/detail.html', context)


def service_category(request, slug):
    """List services in a specific category."""
    category = get_object_or_404(ServiceCategory, slug=slug)
    services = category.services.filter(is_active=True)
    
    # Pagination
    page_obj = paginate_queryset(request, services, per_page=12)
    
    context = {
        'page_title': f"{category.name} – Geo‑Junction",
        'meta_description': f"Explore {category.name} services offered by Geo‑Junction for geophysical exploration.",
        'category': category,
        'page_obj': page_obj,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/services/category.html', context)


# ==============================================================
# 3. PROJECTS VIEWS
# ==============================================================

def project_list(request):
    """List all public projects with filtering and pagination."""
    projects = ExplorationProject.objects.filter(
        is_public=True
    ).select_related('client').prefetch_related('services')
    
    # Filtering
    form = ProjectFilterForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('status'):
            projects = projects.filter(status=form.cleaned_data['status'])
        if form.cleaned_data.get('client'):
            projects = projects.filter(client=form.cleaned_data['client'])
        if form.cleaned_data.get('country'):
            projects = projects.filter(country__icontains=form.cleaned_data['country'])
        if form.cleaned_data.get('search'):
            projects = projects.filter(
                Q(title__icontains=form.cleaned_data['search']) |
                Q(description__icontains=form.cleaned_data['search']) |
                Q(location__icontains=form.cleaned_data['search'])
            )
    
    # Pagination
    page_obj = paginate_queryset(request, projects, per_page=12)
    
    context = {
        'page_title': 'Projects – Geo‑Junction',
        'meta_description': 'Explore Geo‑Junction\'s featured geophysical exploration projects across Africa and beyond.',
        'page_obj': page_obj,
        'form': form,
        'status_choices': ExplorationProject.STATUS_CHOICES,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/projects/list.html', context)


def project_detail(request, slug):
    """Detailed view of a single project."""
    project = get_object_or_404(
        ExplorationProject.objects.select_related('client').prefetch_related(
            'services',
            Prefetch('surveys', queryset=SurveyJob.objects.filter(is_completed=True)),
            Prefetch('drill_holes'),
            Prefetch('resource_estimates', queryset=ResourceEstimate.objects.filter(is_public=True)),
            Prefetch('reports', queryset=Report.objects.filter(is_public=True)),
            Prefetch('assignments__personnel__user'),
        ),
        slug=slug,
        is_public=True
    )
    
    # Get related content
    surveys = project.surveys.all()
    drill_holes = project.drill_holes.all()
    resource_estimates = project.resource_estimates.all()
    reports = project.reports.all()
    assignments = project.assignments.select_related('personnel__user')
    
    # Related projects (same country or client)
    related_projects = ExplorationProject.objects.filter(
        is_public=True,
        is_featured=True
    ).exclude(id=project.id)[:4]
    
    context = {
        'page_title': f"{project.title} – Geo‑Junction",
        'meta_description': f"{project.title}: {project.location} – {project.client.name}",
        'project': project,
        'surveys': surveys,
        'drill_holes': drill_holes,
        'resource_estimates': resource_estimates,
        'reports': reports,
        'assignments': assignments,
        'related_projects': related_projects,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/projects/detail.html', context)


# ==============================================================
# 4. OFFICES VIEWS
# ==============================================================

def office_list(request):
    """List all offices with pagination."""
    offices = Office.objects.filter(is_active=True).order_by('display_order')
    headquarters = offices.filter(is_headquarters=True).first()
    
    context = {
        'page_title': 'Our Offices – Geo‑Junction',
        'meta_description': 'Find Geo‑Junction offices worldwide, including headquarters and regional offices.',
        'offices': offices,
        'headquarters': headquarters,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/offices/list.html', context)


def office_detail(request, slug):
    """Detailed view of a single office."""
    office = get_object_or_404(Office, slug=slug, is_active=True)
    
    context = {
        'page_title': f"{office.name} – Geo‑Junction",
        'meta_description': f"Contact Geo‑Junction's {office.name} for geophysical exploration services.",
        'office': office,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/offices/detail.html', context)


# ==============================================================
# 5. TEAM VIEWS
# ==============================================================

def team_list(request):
    """List all team members with filtering and pagination."""
    team = Personnel.objects.filter(
        is_active=True
    ).select_related('user').order_by('display_order')
    
    # Filter by staff type
    staff_type = request.GET.get('type')
    if staff_type == 'field':
        team = team.filter(is_field_staff=True)
    elif staff_type == 'office':
        team = team.filter(is_office_staff=True)
    
    # Search
    q = request.GET.get('q')
    if q:
        team = team.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(specialisation__icontains=q)
        )
    
    # Pagination
    page_obj = paginate_queryset(request, team, per_page=12)
    
    context = {
        'page_title': 'Our Team – Geo‑Junction',
        'meta_description': 'Meet Geo‑Junction\'s expert team of geophysicists, geologists, and surveyors.',
        'page_obj': page_obj,
        'staff_type': staff_type,
        'search_query': q,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/team/list.html', context)


def team_detail(request, id):
    """Detailed profile of a team member."""
    personnel = get_object_or_404(
        Personnel.objects.select_related('user'),
        id=id,
        is_active=True
    )
    
    # Get projects this person has worked on
    assignments = personnel.projectassignment_set.select_related('project')
    
    context = {
        'page_title': f"{personnel.user.get_full_name()} – Geo‑Junction",
        'meta_description': f"Profile of {personnel.user.get_full_name()}, {personnel.specialisation} at Geo‑Junction.",
        'personnel': personnel,
        'assignments': assignments,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/team/detail.html', context)


# ==============================================================
# 6. NEWS VIEWS
# ==============================================================

def news_list(request):
    """List all published news articles with pagination and filtering."""
    articles = NewsArticle.objects.filter(
        is_published=True,
        publish_at__lte=timezone.now()
    ).select_related('category', 'author').order_by('-publish_at')
    
    # Filtering
    form = NewsFilterForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('category'):
            articles = articles.filter(category=form.cleaned_data['category'])
        if form.cleaned_data.get('search'):
            articles = articles.filter(
                Q(title__icontains=form.cleaned_data['search']) |
                Q(content__icontains=form.cleaned_data['search'])
            )
    
    # Pagination
    page_obj = paginate_queryset(request, articles, per_page=10)
    
    # Featured articles
    featured = articles.filter(is_featured=True)[:3]
    
    context = {
        'page_title': 'News – Geo‑Junction',
        'meta_description': 'Latest news and updates from Geo‑Junction about geophysical exploration and mining.',
        'page_obj': page_obj,
        'featured': featured,
        'form': form,
        'categories': NewsCategory.objects.all(),
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/news/list.html', context)


def news_detail(request, slug):
    """Detailed view of a single news article."""
    article = get_object_or_404(
        NewsArticle.objects.select_related('category', 'author'),
        slug=slug,
        is_published=True,
        publish_at__lte=timezone.now()
    )
    
    # Related articles (same category)
    related = NewsArticle.objects.filter(
        category=article.category,
        is_published=True
    ).exclude(id=article.id)[:5]
    
    context = {
        'page_title': article.title,
        'meta_description': article.content[:160],
        'article': article,
        'related': related,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/news/detail.html', context)


def news_category(request, slug):
    """List news articles in a specific category."""
    category = get_object_or_404(NewsCategory, slug=slug)
    articles = NewsArticle.objects.filter(
        category=category,
        is_published=True,
        publish_at__lte=timezone.now()
    ).order_by('-publish_at')
    
    # Pagination
    page_obj = paginate_queryset(request, articles, per_page=12)
    
    context = {
        'page_title': f"{category.name} News – Geo‑Junction",
        'meta_description': f"Read {category.name} news from Geo‑Junction about geophysical exploration.",
        'category': category,
        'page_obj': page_obj,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/news/category.html', context)


# ==============================================================
# 7. CAREERS VIEWS
# ==============================================================

def job_list(request):
    """List all published job postings with pagination and filtering."""
    jobs = JobPosting.objects.filter(
        is_published=True,
        publish_at__lte=timezone.now()
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gte=timezone.now())
    ).filter(
        Q(application_deadline__isnull=True) | Q(application_deadline__gte=timezone.now().date())
    ).select_related('category').order_by('-created_at')
    
    # Filtering
    form = JobFilterForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('category'):
            jobs = jobs.filter(category=form.cleaned_data['category'])
        if form.cleaned_data.get('job_type'):
            jobs = jobs.filter(job_type=form.cleaned_data['job_type'])
        if form.cleaned_data.get('location'):
            jobs = jobs.filter(location__icontains=form.cleaned_data['location'])
        if form.cleaned_data.get('department'):
            jobs = jobs.filter(department__icontains=form.cleaned_data['department'])
        if form.cleaned_data.get('is_remote'):
            jobs = jobs.filter(is_remote=True)
        if form.cleaned_data.get('search'):
            jobs = jobs.filter(
                Q(title__icontains=form.cleaned_data['search']) |
                Q(description__icontains=form.cleaned_data['search']) |
                Q(location__icontains=form.cleaned_data['search'])
            )
    
    # Pagination
    page_obj = paginate_queryset(request, jobs, per_page=10)
    
    context = {
        'page_title': 'Careers – Geo‑Junction',
        'meta_description': 'Explore career opportunities at Geo‑Junction in geophysics, surveying, and mining consultancy.',
        'page_obj': page_obj,
        'form': form,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/careers/list.html', context)


def job_detail(request, slug):
    """Detailed view of a single job posting."""
    job = get_object_or_404(
        JobPosting.objects.select_related('category'),
        slug=slug,
        is_published=True,
        publish_at__lte=timezone.now()
    )
    
    # Increment view count
    job.views += 1
    job.save(update_fields=['views'])
    
    # Related jobs
    related = JobPosting.objects.filter(
        category=job.category,
        is_published=True
    ).exclude(id=job.id)[:5]
    
    context = {
        'page_title': f"{job.title} – Geo‑Junction Careers",
        'meta_description': f"Apply for {job.title} at Geo‑Junction. {job.location}.",
        'job': job,
        'related': related,
        'apply_form': JobApplicationForm(job=job),
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/careers/detail.html', context)


@require_POST
def job_apply(request, slug):
    """Process a job application."""
    job = get_object_or_404(
        JobPosting,
        slug=slug,
        is_published=True,
        publish_at__lte=timezone.now()
    )
    
    form = JobApplicationForm(request.POST, request.FILES, job=job)
    if form.is_valid():
        try:
            application = form.save()
            logger.info(f"Job application submitted for {job.title} by {application.email}")
            messages.success(
                request,
                f'Your application for "{job.title}" has been submitted successfully! '
                'We will review it and get back to you.'
            )
            return redirect('geo:job_detail', slug=job.slug)
        except Exception as e:
            logger.error(f"Job application failed for {job.title}: {e}")
            messages.error(request, 'There was an error submitting your application. Please try again.')
    else:
        messages.error(request, 'Please correct the errors below.')
    
    return render(request, 'geo/careers/detail.html', {
        'job': job,
        'apply_form': form,
        'breadcrumbs': get_breadcrumbs(request),
    })


# ==============================================================
# 8. RESOURCES VIEWS (Documents & Reports)
# ==============================================================

def document_list(request):
    """List all public documents with pagination and filtering."""
    documents = Document.objects.filter(
        is_public=True
    ).order_by('-created_at')
    
    # Filter by type
    doc_type = request.GET.get('type')
    if doc_type:
        documents = documents.filter(document_type=doc_type)
    
    # Search
    q = request.GET.get('q')
    if q:
        documents = documents.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q)
        )
    
    # Pagination
    page_obj = paginate_queryset(request, documents, per_page=12)
    
    context = {
        'page_title': 'Documents – Geo‑Junction',
        'meta_description': 'Download Geo‑Junction documents, brochures, fact sheets, and technical papers.',
        'page_obj': page_obj,
        'doc_types': Document.DOCUMENT_TYPES,
        'current_type': doc_type,
        'search_query': q,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/resources/documents.html', context)


def report_list(request):
    """List all public reports with pagination and filtering."""
    reports = Report.objects.filter(
        is_public=True
    ).select_related('project', 'author').order_by('-publication_date')
    
    # Filter by type
    report_type = request.GET.get('type')
    if report_type:
        reports = reports.filter(report_type=report_type)
    
    # Search
    q = request.GET.get('q')
    if q:
        reports = reports.filter(
            Q(title__icontains=q) |
            Q(project__title__icontains=q)
        )
    
    # Pagination
    page_obj = paginate_queryset(request, reports, per_page=12)
    
    context = {
        'page_title': 'Reports – Geo‑Junction',
        'meta_description': 'Access Geo‑Junction technical reports, executive summaries, and investor presentations.',
        'page_obj': page_obj,
        'report_types': Report.REPORT_TYPES,
        'current_type': report_type,
        'search_query': q,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/resources/reports.html', context)


def report_detail(request, slug):
    """Detailed view of a single report."""
    report = get_object_or_404(
        Report.objects.select_related('project', 'author'),
        slug=slug,
        is_public=True
    )
    
    # Increment download count (if requested)
    if request.GET.get('download'):
        report.download_count += 1
        report.save(update_fields=['download_count'])
    
    context = {
        'page_title': report.title,
        'meta_description': report.title,
        'report': report,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/resources/report_detail.html', context)


# ==============================================================
# 9. GALLERY VIEWS
# ==============================================================

def gallery_list(request):
    """List all gallery images with pagination and filtering."""
    images = GalleryImage.objects.all().order_by('-created_at')
    
    # Filter by category
    category = request.GET.get('category')
    if category:
        images = images.filter(category=category)
    
    # Search
    q = request.GET.get('q')
    if q:
        images = images.filter(
            Q(title__icontains=q) |
            Q(caption__icontains=q)
        )
    
    # Pagination
    page_obj = paginate_queryset(request, images, per_page=24)
    
    context = {
        'page_title': 'Gallery – Geo‑Junction',
        'meta_description': 'View Geo‑Junction gallery images from fieldwork, equipment, team events, and offices.',
        'page_obj': page_obj,
        'categories': GalleryImage.CATEGORY_CHOICES,
        'current_category': category,
        'search_query': q,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/gallery/list.html', context)


def gallery_category(request, category):
    """List gallery images by category."""
    # Validate category
    valid_categories = [c[0] for c in GalleryImage.CATEGORY_CHOICES]
    if category not in valid_categories:
        raise Http404
    
    images = GalleryImage.objects.filter(category=category)
    
    # Pagination
    page_obj = paginate_queryset(request, images, per_page=24)
    
    context = {
        'page_title': f"{dict(GalleryImage.CATEGORY_CHOICES).get(category, 'Gallery')} – Geo‑Junction",
        'meta_description': f"Geo‑Junction {dict(GalleryImage.CATEGORY_CHOICES).get(category, 'Gallery')} gallery.",
        'page_obj': page_obj,
        'category': category,
        'category_label': dict(GalleryImage.CATEGORY_CHOICES).get(category, 'Gallery'),
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/gallery/category.html', context)


# ==============================================================
# 10. SUSTAINABILITY VIEWS
# ==============================================================

def sustainability_list(request):
    """List sustainability reports and initiatives."""
    reports = SustainabilityReport.objects.filter(
        is_public=True
    ).order_by('-publication_date')
    
    # Pagination
    page_obj = paginate_queryset(request, reports, per_page=10)
    
    context = {
        'page_title': 'Sustainability – Geo‑Junction',
        'meta_description': 'Geo‑Junction\'s sustainability reports, ESG initiatives, and environmental commitment.',
        'page_obj': page_obj,
        'policies': Policy.objects.filter(
            policy_type__in=['sustainability', 'hse'],
            is_active=True
        ),
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/sustainability/list.html', context)


def sustainability_detail(request, slug):
    """Detailed view of a sustainability report."""
    report = get_object_or_404(
        SustainabilityReport,
        slug=slug,
        is_public=True
    )
    
    context = {
        'page_title': report.title,
        'meta_description': report.summary,
        'report': report,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/sustainability/detail.html', context)


# ==============================================================
# 11. AWARDS VIEWS
# ==============================================================

def award_list(request):
    """List all awards grouped by year."""
    awards = Award.objects.filter(is_active=True).order_by('-year', 'display_order')
    
    # Group by year
    years = awards.values_list('year', flat=True).distinct().order_by('-year')
    grouped = {year: awards.filter(year=year) for year in years}
    
    context = {
        'page_title': 'Awards & Accreditations – Geo‑Junction',
        'meta_description': 'Geo‑Junction awards, accreditations, and industry recognitions.',
        'grouped_awards': grouped,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/awards/list.html', context)


# ==============================================================
# 12. PARTNERS VIEWS
# ==============================================================

def partner_list(request):
    """List all partners."""
    partners = Partner.objects.filter(is_active=True).order_by('display_order')
    
    # Filter by type
    partner_type = request.GET.get('type')
    if partner_type:
        partners = partners.filter(partner_type=partner_type)
    
    context = {
        'page_title': 'Our Partners – Geo‑Junction',
        'meta_description': 'Geo‑Junction partners, joint ventures, and industry affiliations.',
        'partners': partners,
        'partner_types': Partner.PARTNER_TYPES,
        'current_type': partner_type,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/partners/list.html', context)


# ==============================================================
# 13. TESTIMONIALS VIEWS
# ==============================================================

def testimonial_list(request):
    """List all testimonials."""
    testimonials = Testimonial.objects.all().order_by('-created_at')
    
    # Featured first
    featured = testimonials.filter(is_featured=True)
    others = testimonials.filter(is_featured=False)
    
    # Pagination for others
    page_obj = paginate_queryset(request, others, per_page=12)
    
    context = {
        'page_title': 'Testimonials – Geo‑Junction',
        'meta_description': 'Client testimonials for Geo‑Junction\'s geophysical exploration services.',
        'featured': featured,
        'page_obj': page_obj,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/testimonials/list.html', context)


# ==============================================================
# 14. CASE STUDIES VIEWS
# ==============================================================

def case_study_list(request):
    """List all case studies."""
    studies = CaseStudy.objects.filter(
        is_published=True,
        publish_at__lte=timezone.now()
    ).select_related('project').order_by('-created_at')
    
    # Featured first
    featured = studies.filter(is_featured=True)
    
    # Pagination
    page_obj = paginate_queryset(request, studies, per_page=9)
    
    context = {
        'page_title': 'Case Studies – Geo‑Junction',
        'meta_description': 'Geo‑Junction case studies showcasing successful geophysical exploration projects.',
        'featured': featured,
        'page_obj': page_obj,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/case_studies/list.html', context)


def case_study_detail(request, slug):
    """Detailed view of a case study."""
    study = get_object_or_404(
        CaseStudy,
        slug=slug,
        is_published=True,
        publish_at__lte=timezone.now()
    )
    
    # Related case studies
    related = CaseStudy.objects.filter(
        is_published=True
    ).exclude(id=study.id)[:3]
    
    context = {
        'page_title': study.title,
        'meta_description': study.challenge[:160],
        'study': study,
        'related': related,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/case_studies/detail.html', context)


# ==============================================================
# 15. FAQ VIEWS
# ==============================================================

def faq_list(request):
    """List all FAQs by category."""
    categories = FAQCategory.objects.all().prefetch_related(
        Prefetch('faqs', queryset=FAQ.objects.filter(is_active=True).order_by('order'))
    )
    
    context = {
        'page_title': 'FAQs – Geo‑Junction',
        'meta_description': 'Frequently asked questions about Geo‑Junction\'s geophysical exploration services.',
        'categories': categories,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/faqs/list.html', context)


# ==============================================================
# 16. DYNAMIC PAGES VIEWS
# ==============================================================

def page_detail(request, slug):
    """Render a dynamic page."""
    page = get_object_or_404(
        Page,
        slug=slug,
        is_published=True,
        publish_at__lte=timezone.now()
    )
    
    # Check expiration
    if page.expires_at and page.expires_at < timezone.now():
        raise Http404
    
    # Get children
    children = page.children.filter(is_published=True)
    
    # Get content blocks
    blocks = page.blocks.filter(is_active=True).order_by('order')
    
    context = {
        'page_title': page.meta_title or page.title,
        'meta_description': page.meta_description,
        'page': page,
        'children': children,
        'blocks': blocks,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, f'geo/pages/{page.template}.html', context)


# ==============================================================
# 17. POLICIES VIEWS
# ==============================================================

def policy_list(request):
    """List all policies with filtering."""
    policies = Policy.objects.filter(is_active=True).order_by('-effective_date')
    
    # Filter by type
    policy_type = request.GET.get('type')
    if policy_type:
        policies = policies.filter(policy_type=policy_type)
    
    # Pagination
    page_obj = paginate_queryset(request, policies, per_page=10)
    
    context = {
        'page_title': 'Policies – Geo‑Junction',
        'meta_description': 'Geo‑Junction policies including HSE, governance, privacy, and sustainability.',
        'page_obj': page_obj,
        'policy_types': Policy.POLICY_TYPES,
        'current_type': policy_type,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/policies/list.html', context)


def policy_detail(request, slug):
    """Detailed view of a policy."""
    policy = get_object_or_404(Policy, slug=slug, is_active=True)
    
    context = {
        'page_title': policy.title,
        'meta_description': policy.content[:160],
        'policy': policy,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/policies/detail.html', context)


# ==============================================================
# 18. EVENTS VIEWS
# ==============================================================

def event_list(request):
    """List all events with pagination."""
    events = Event.objects.filter(
        is_published=True,
        publish_at__lte=timezone.now()
    ).order_by('start_date')
    
    # Upcoming events
    upcoming = events.filter(start_date__gte=timezone.now().date())
    past = events.filter(start_date__lt=timezone.now().date())
    
    # Pagination for upcoming
    upcoming_page_obj = paginate_queryset(request, upcoming, per_page=6)
    past_page_obj = paginate_queryset(request, past, per_page=6)
    
    context = {
        'page_title': 'Events – Geo‑Junction',
        'meta_description': 'Upcoming and past Geo‑Junction events, conferences, and workshops.',
        'upcoming_page_obj': upcoming_page_obj,
        'past_page_obj': past_page_obj,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/events/list.html', context)


def event_detail(request, slug):
    """Detailed view of an event."""
    event = get_object_or_404(
        Event,
        slug=slug,
        is_published=True,
        publish_at__lte=timezone.now()
    )
    
    context = {
        'page_title': event.title,
        'meta_description': event.description[:160],
        'event': event,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/events/detail.html', context)


# ==============================================================
# 19. AUTHENTICATION VIEWS
# ==============================================================

@never_cache
def register(request):
    """User registration view with email verification."""
    if request.user.is_authenticated:
        return redirect('geo:home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.is_active = True
                    user.is_verified = False
                    user.save()
                    
                    # Create user profile with viewer role
                    UserProfile.objects.create(user=user, role='viewer')
                    
                    # Send verification email
                    send_verification_email(request, user)
                    
                    messages.success(
                        request,
                        'Account created successfully! Please check your email to verify your address before logging in.'
                    )
                    return redirect('geo:login')
            except Exception as e:
                logger.error(f"Registration failed: {e}")
                messages.error(request, 'There was an error creating your account. Please try again.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = UserRegistrationForm()
    
    context = {
        'form': form,
        'page_title': 'Register – Geo‑Junction',
        'meta_description': 'Create a Geo‑Junction viewer account to access project reports, news, and exploration insights.',
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/auth/register.html', context)


def verify_email(request, uidb64, token):
    """Verify the user's email address."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user and default_token_generator.check_token(user, token):
        user.is_verified = True
        user.save()
        messages.success(request, 'Your email has been verified! You can now log in.')
        return redirect('geo:login')
    else:
        messages.error(request, 'The verification link is invalid or expired.')
        return redirect('geo:register')


@never_cache
def login_view(request):
    """User login view with verification check."""
    if request.user.is_authenticated:
        return redirect('geo:home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if not user.is_verified:
                    messages.warning(
                        request,
                        'Please verify your email address before logging in. Check your inbox for the verification link.'
                    )
                    return redirect('geo:login')
                login(request, user)
                # Update last activity
                user.last_activity = timezone.now()
                user.save(update_fields=['last_activity'])
                messages.success(request, f"Welcome back, {user.get_full_name() or user.email}!")
                
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('geo:home')
        messages.error(request, 'Invalid email or password.')
    else:
        form = CustomAuthenticationForm()
    
    context = {
        'form': form,
        'page_title': 'Login – Geo‑Junction',
        'meta_description': 'Log in to your Geo‑Junction account to access project data and reports.',
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/auth/login.html', context)


@login_required
def logout_view(request):
    """User logout view."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('geo:home')


# ==============================================================
# 20. USER PROFILE VIEWS (Requires Login)
# ==============================================================

@login_required
@viewer_required
def profile_view(request):
    """View user profile."""
    user = request.user
    profile = UserProfile.objects.get(user=user)
    
    context = {
        'page_title': 'My Profile – Geo‑Junction',
        'user': user,
        'profile': profile,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/profile/view.html', context)


@login_required
@viewer_required
def profile_edit(request):
    """Edit user profile."""
    user = request.user
    profile = UserProfile.objects.get(user=user)
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=user)
        profile_form = UserProfileSettingsForm(request.POST, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('geo:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = UserProfileForm(instance=user)
        profile_form = UserProfileSettingsForm(instance=profile)
    
    context = {
        'page_title': 'Edit Profile – Geo‑Junction',
        'user_form': user_form,
        'profile_form': profile_form,
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/profile/edit.html', context)


# ==============================================================
# 21. USER DASHBOARD (Requires Login)
# ==============================================================

@login_required
@viewer_required
def dashboard(request):
    """User dashboard with personalised content based on role."""
    user = request.user
    profile = UserProfile.objects.get(user=user)
    
    context = {
        'page_title': 'Dashboard – Geo‑Junction',
        'user': user,
        'profile': profile,
        'breadcrumbs': get_breadcrumbs(request),
    }
    
    # Different content based on role
    if profile.role == 'viewer':
        # Show public updates
        context['recent_news'] = NewsArticle.objects.filter(
            is_published=True,
            publish_at__lte=timezone.now()
        ).order_by('-publish_at')[:5]
        context['recent_projects'] = ExplorationProject.objects.filter(
            is_public=True,
            is_featured=True
        )[:4]
        context['dashboard_type'] = 'viewer'
    
    elif profile.role in ['geologist', 'surveyor']:
        # Show assigned tasks and projects
        context['assigned_projects'] = ExplorationProject.objects.filter(
            assignments__personnel__user=user
        ).distinct()[:5]
        context['tasks'] = ProjectTask.objects.filter(
            assigned_to=user,
            status__in=['pending', 'in_progress']
        )[:10]
        context['dashboard_type'] = 'staff'
    
    elif profile.role in ['project_manager', 'admin', 'super_admin']:
        # Show full project oversight
        context['all_projects'] = ExplorationProject.objects.all()[:5]
        context['pending_tasks'] = ProjectTask.objects.filter(status='pending').count()
        context['active_projects'] = ExplorationProject.objects.filter(
            status__in=['fieldwork', 'data_processing', 'reporting']
        ).count()
        context['dashboard_type'] = 'admin'
    
    return render(request, 'geo/dashboard.html', context)


@login_required
@staff_required
def staff_dashboard(request):
    """Staff-only dashboard for project management."""
    user = request.user
    
    # Projects where this user is involved
    my_projects = ExplorationProject.objects.filter(
        assignments__personnel__user=user
    ).distinct()
    
    # Tasks assigned to this user
    my_tasks = ProjectTask.objects.filter(
        assigned_to=user
    ).order_by('due_date')
    
    context = {
        'page_title': 'Staff Dashboard – Geo‑Junction',
        'my_projects': my_projects,
        'my_tasks': my_tasks,
        'pending_tasks': my_tasks.filter(status='pending').count(),
        'in_progress_tasks': my_tasks.filter(status='in_progress').count(),
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/dashboard/staff.html', context)


@login_required
@admin_required
def admin_dashboard(request):
    """Admin-only dashboard with system overview."""
    context = {
        'page_title': 'Admin Dashboard – Geo‑Junction',
        'total_users': User.objects.count(),
        'total_projects': ExplorationProject.objects.count(),
        'total_services': Service.objects.filter(is_active=True).count(),
        'total_news': NewsArticle.objects.filter(is_published=True).count(),
        'total_jobs': JobPosting.objects.filter(is_published=True).count(),
        'pending_applications': JobApplication.objects.filter(status='received').count(),
        'unread_messages': ContactMessage.objects.filter(is_read=False).count(),
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/dashboard/admin.html', context)


# ==============================================================
# 22. NEWSLETTER VIEWS
# ==============================================================

@require_POST
def newsletter_subscribe(request):
    """Subscribe to the newsletter."""
    form = SubscriberForm(request.POST)
    if form.is_valid():
        try:
            form.save()
            messages.success(request, 'You have been subscribed to our newsletter!')
            logger.info(f"Newsletter subscription: {form.cleaned_data['email']}")
        except Exception as e:
            logger.error(f"Newsletter subscription failed: {e}")
            messages.error(request, 'There was an error subscribing. Please try again.')
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect(request.META.get('HTTP_REFERER', 'geo:home'))


def newsletter_unsubscribe(request):
    """Unsubscribe from the newsletter."""
    email = request.GET.get('email')
    if email:
        try:
            subscriber = Subscriber.objects.get(email=email, is_active=True)
            subscriber.is_active = False
            subscriber.save()
            messages.success(request, 'You have been unsubscribed from our newsletter.')
            logger.info(f"Newsletter unsubscription: {email}")
        except Subscriber.DoesNotExist:
            messages.warning(request, 'Email not found in our subscriber list.')
    else:
        messages.error(request, 'Please provide an email address.')
    return redirect('geo:home')


# ==============================================================
# 23. SEARCH VIEW
# ==============================================================

@require_GET
def search(request):
    """Site-wide search with pagination and type filtering."""
    form = SearchForm(request.GET)
    results = {}
    total_results = 0
    
    if form.is_valid():
        query = form.cleaned_data.get('q')
        model_type = form.cleaned_data.get('model_type')
        
        if query:
            # Search in Projects
            if not model_type or model_type == 'project':
                projects = ExplorationProject.objects.filter(
                    is_public=True
                ).filter(
                    Q(title__icontains=query) |
                    Q(description__icontains=query) |
                    Q(location__icontains=query)
                ).select_related('client')[:10]
                results['projects'] = projects
                total_results += projects.count()
            
            # Search in News
            if not model_type or model_type == 'news':
                news = NewsArticle.objects.filter(
                    is_published=True
                ).filter(
                    Q(title__icontains=query) |
                    Q(content__icontains=query)
                ).select_related('category')[:10]
                results['news'] = news
                total_results += news.count()
            
            # Search in Jobs
            if not model_type or model_type == 'job':
                jobs = JobPosting.objects.filter(
                    is_published=True
                ).filter(
                    Q(title__icontains=query) |
                    Q(description__icontains=query) |
                    Q(location__icontains=query)
                ).select_related('category')[:10]
                results['jobs'] = jobs
                total_results += jobs.count()
            
            # Search in Pages
            if not model_type or model_type == 'page':
                pages = Page.objects.filter(
                    is_published=True
                ).filter(
                    Q(title__icontains=query) |
                    Q(content__icontains=query)
                )[:10]
                results['pages'] = pages
                total_results += pages.count()
            
            # Search in Documents
            if not model_type or model_type == 'document':
                docs = Document.objects.filter(
                    is_public=True
                ).filter(
                    Q(title__icontains=query) |
                    Q(description__icontains=query)
                )[:10]
                results['documents'] = docs
                total_results += docs.count()
    
    context = {
        'page_title': 'Search Results – Geo‑Junction',
        'form': form,
        'results': results,
        'total_results': total_results,
        'query': form.cleaned_data.get('q', ''),
        'breadcrumbs': get_breadcrumbs(request),
    }
    return render(request, 'geo/search/results.html', context)


# ==============================================================
# 24. SITEMAP & ROBOTS
# ==============================================================

@require_GET
def sitemap(request):
    """Generate a sitemap.xml."""
    urls = []
    
    # Static pages
    static_pages = [
        {'loc': '/', 'priority': '1.0'},
        {'loc': '/about/', 'priority': '0.8'},
        {'loc': '/contact/', 'priority': '0.8'},
        {'loc': '/services/', 'priority': '0.9'},
        {'loc': '/projects/', 'priority': '0.9'},
        {'loc': '/news/', 'priority': '0.8'},
        {'loc': '/careers/', 'priority': '0.7'},
        {'loc': '/sustainability/', 'priority': '0.6'},
        {'loc': '/gallery/', 'priority': '0.5'},
        {'loc': '/faq/', 'priority': '0.5'},
        {'loc': '/testimonials/', 'priority': '0.6'},
        {'loc': '/case-studies/', 'priority': '0.7'},
        {'loc': '/partners/', 'priority': '0.5'},
        {'loc': '/awards/', 'priority': '0.5'},
    ]
    for url in static_pages:
        urls.append(url)
    
    # Dynamic pages - Projects
    for project in ExplorationProject.objects.filter(is_public=True):
        urls.append({
            'loc': project.get_absolute_url(),
            'priority': '0.7',
            'lastmod': project.updated_at.date().isoformat() if hasattr(project, 'updated_at') else None
        })
    
    # News
    for article in NewsArticle.objects.filter(is_published=True):
        urls.append({
            'loc': article.get_absolute_url(),
            'priority': '0.6',
            'lastmod': article.updated_at.date().isoformat() if hasattr(article, 'updated_at') else None
        })
    
    # Jobs
    for job in JobPosting.objects.filter(is_published=True):
        urls.append({
            'loc': job.get_absolute_url(),
            'priority': '0.5',
            'lastmod': job.updated_at.date().isoformat() if hasattr(job, 'updated_at') else None
        })
    
    # Pages
    for page in Page.objects.filter(is_published=True):
        urls.append({
            'loc': page.get_absolute_url(),
            'priority': '0.6',
            'lastmod': page.updated_at.date().isoformat() if hasattr(page, 'updated_at') else None
        })
    
    # Build XML response
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        xml += f'  <url>\n'
        xml += f'    <loc>https://geojunction.com{url["loc"]}</loc>\n'
        xml += f'    <priority>{url["priority"]}</priority>\n'
        if url.get('lastmod'):
            xml += f'    <lastmod>{url["lastmod"]}</lastmod>\n'
        xml += f'  </url>\n'
    xml += '</urlset>'
    
    return HttpResponse(xml, content_type='application/xml')


@require_GET
def robots(request):
    """Generate robots.txt."""
    content = """User-agent: *
Allow: /
Disallow: /admin/
Disallow: /accounts/
Disallow: /password-*
Disallow: /profile/
Disallow: /dashboard/

Sitemap: https://geojunction.com/sitemap.xml/
"""
    return HttpResponse(content, content_type='text/plain')


# ==============================================================
# 25. HEALTH CHECK (For Render/Uptime Monitoring)
# ==============================================================

@require_GET
def health_check(request):
    """Simple health check endpoint for monitoring."""
    return JsonResponse({
        'status': 'ok',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0'
    })