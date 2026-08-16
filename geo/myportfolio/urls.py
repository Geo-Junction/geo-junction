# geo_junction/urls.py (Project-level)

"""
Geo‑Junction – Project-Level URL Configuration
Routes all incoming requests to the appropriate app views.
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from geo.forms import CustomPasswordResetForm, CustomSetPasswordForm


urlpatterns = [
    # Admin Panel
    path('admin/', admin.site.urls),
    
    # Main Application (all routes under app namespace 'geo')
    path('', include('geo.urls', namespace='geo')),
    
    # Authentication Routes (project-level)
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             form_class=CustomPasswordResetForm,
             template_name='registration/password_reset_form.html',
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt',
         ),
         name='password_reset'),
    
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ),
         name='password_reset_done'),
    
    path('password-reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             form_class=CustomSetPasswordForm,
             template_name='registration/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),
    
    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    
    # Password Change (for authenticated users)
    path('password-change/',
         auth_views.PasswordChangeView.as_view(
             template_name='registration/password_change_form.html'
         ),
         name='password_change'),
    
    path('password-change/done/',
         auth_views.PasswordChangeDoneView.as_view(
             template_name='registration/password_change_done.html'
         ),
         name='password_change_done'),
    
    
    
    
    
    
    
    path('password-reset/',
     auth_views.PasswordResetView.as_view(
         form_class=CustomPasswordResetForm,
         template_name='geo/auth/password_reset_form.html',   # <-- changed
         email_template_name='registration/password_reset_email.html',
     ),
     name='password_reset'),
    
    
    
    
    
    
    
    
]


# Development-only static & media file serving
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Enable Django Debug Toolbar if installed
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns