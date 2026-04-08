from django.urls import path
from .views import confirmation_view, health_view, send_emails_view, upload_view, verification_view

urlpatterns = [
    path('health/', health_view, name='health'),
    path('', upload_view, name='upload'),
    path('verification/', verification_view, name='verification'),
    path('send/', send_emails_view, name='send_emails'),
    path('confirmation/', confirmation_view, name='confirmation'),
]
