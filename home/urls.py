from django.urls import path
from django.contrib import admin  # Admin panel
from django.conf import settings  # Access settings
from django.conf.urls.static import static  # Serve static & media files
from . import views  # Import views

app_name = 'home'  # Namespace for URL reversal

urlpatterns = [
    # ✅ Admin Panel (Optional, already in main `urls.py`)
    path('admin/', admin.site.urls),

    # ✅ Home and Main Pages
    path('', views.index, name='index'),  # Homepage
    path('main/', views.main, name='main'),  # Main Dashboard

    # ✅ Information Pages
    path('about/', views.about, name='about'),
    path('how-it-works/', views.how_it_works, name='how_it_works'),
    path('service/', views.service, name='service'),
    path('contact/', views.contact, name='contact'),

    # ✅ Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # ✅ Help Page (Chatbot)
    path('help/', views.help_view, name='help'),

    # ✅ Detection Page & APIs
    path("detection/", views.detection, name='detection'),
    path('detect-image/', views.detect_ambulance, name='detect_ambulance'),
    path('upload-image/', views.upload_image, name='upload_image'),
    path('upload-video/', views.upload_video, name='upload_video'),

    # ✅ Add missing CCTV stream route
    path('cctv-stream/', views.cctv_stream, name='cctv_stream'),
    
]

# ✅ Serve static and media files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
