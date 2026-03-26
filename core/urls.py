from django.urls import path
from .views import upload_view, verification_view, send_emails_view, confirmation_view

urlpatterns = [
    path('', upload_view, name='upload'),
    path('verification/', verification_view, name='verification'),
    path('send/', send_emails_view, name='send_emails'),
    path('confirmation/', confirmation_view, name='confirmation'),
]
