from django.urls import path
from . import views

urlpatterns = [
    path('create_campaign/', views.create_campaign, name='create_campaign'),
    path('get_campaigns/', views.get_campaigns, name='get_campaigns'),

    path('get_io_list/', views.get_io_list, name='get_io_list'),
    path('download_io_pdf/<str:ticket_id>/', views.download_io_pdf, name='download_io_pdf'),
    path('generate_io_pdf/<str:ticket_id>/', views.generate_io_pdf, name='generate_io_pdf'),  # ← ADD THIS
    
    path("io/<str:ticket_id>/send-email-preview/", views.io_send_email_preview, name="io_send_email_preview"),
    path("io/<str:ticket_id>/send-email/", views.io_send_email, name="io_send_email"),
]   