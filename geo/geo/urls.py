# geo/urls.py (App-level)

from django.urls import path
from . import views

app_name = 'geo'

urlpatterns = [
    # ==============================================================
    # 1. PUBLIC PAGES (No Authentication Required)
    # ==============================================================
    
    # Homepage
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    
    # Services
    path('services/', views.service_list, name='service_list'),
    path('services/<slug:slug>/', views.service_detail, name='service_detail'),
    path('services/category/<slug:slug>/', views.service_category, name='service_category'),
    
    # Projects
    path('projects/', views.project_list, name='project_list'),
    path('projects/<slug:slug>/', views.project_detail, name='project_detail'),
    
    # Offices
    path('offices/', views.office_list, name='office_list'),
    path('offices/<slug:slug>/', views.office_detail, name='office_detail'),
    
    # Team / Personnel
    path('team/', views.team_list, name='team_list'),
    path('team/<uuid:id>/', views.team_detail, name='team_detail'),
    
    # News
    path('news/', views.news_list, name='news_list'),
    path('news/<slug:slug>/', views.news_detail, name='news_detail'),
    path('news/category/<slug:slug>/', views.news_category, name='news_category'),
    
    # Careers / Jobs
    path('careers/', views.job_list, name='job_list'),
    path('careers/<slug:slug>/', views.job_detail, name='job_detail'),
    path('careers/<slug:slug>/apply/', views.job_apply, name='job_apply'),
    
    # Resources
    path('resources/documents/', views.document_list, name='document_list'),
    path('resources/reports/', views.report_list, name='report_list'),
    path('resources/reports/<slug:slug>/', views.report_detail, name='report_detail'),
    
    # Gallery
    path('gallery/', views.gallery_list, name='gallery_list'),
    path('gallery/category/<slug:category>/', views.gallery_category, name='gallery_category'),
    
    # Events
    path('events/', views.event_list, name='event_list'),
    path('events/<slug:slug>/', views.event_detail, name='event_detail'),
    
    # Sustainability
    path('sustainability/', views.sustainability_list, name='sustainability_list'),
    path('sustainability/<slug:slug>/', views.sustainability_detail, name='sustainability_detail'),
    
    # Awards
    path('awards/', views.award_list, name='award_list'),
    
    # Partners
    path('partners/', views.partner_list, name='partner_list'),
    
    # Testimonials
    path('testimonials/', views.testimonial_list, name='testimonial_list'),
    
    # Case Studies
    path('case-studies/', views.case_study_list, name='case_study_list'),
    path('case-studies/<slug:slug>/', views.case_study_detail, name='case_study_detail'),
    
    # FAQ
    path('faq/', views.faq_list, name='faq_list'),
    
    # Dynamic Pages
    path('pages/<slug:slug>/', views.page_detail, name='page_detail'),
    
    # Policies
    path('policies/', views.policy_list, name='policy_list'),
    path('policies/<slug:slug>/', views.policy_detail, name='policy_detail'),
    
    # ==============================================================
    # 2. AUTHENTICATION
    # ==============================================================
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/register/', views.register, name='register'),
    
    # ==============================================================
    # 3. USER PROFILE (Requires Login)
    # ==============================================================
    path('accounts/profile/', views.profile_view, name='profile'),
    path('accounts/profile/edit/', views.profile_edit, name='profile_edit'),
    
    # ==============================================================
    # 4. NEWSLETTER
    # ==============================================================
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('newsletter/unsubscribe/', views.newsletter_unsubscribe, name='newsletter_unsubscribe'),
    
    # ==============================================================
    # 5. SEARCH
    # ==============================================================
    path('search/', views.search, name='search'),
    
    # ==============================================================
    # 6. SITEMAP & ROBOTS
    # ==============================================================
    path('sitemap.xml/', views.sitemap, name='sitemap'),
    path('robots.txt/', views.robots, name='robots'),
]