from django.urls import path
from . import views

urlpatterns = [
    path('add_daily_entry/<str:ticket_id>/', views.add_daily_entry, name='add_daily_entry'),
    path('get_daily_entries/<str:ticket_id>/', views.get_daily_entries, name='get_daily_entries'),
    path('generate_daily_report_excel/<str:ticket_id>/', views.generate_daily_report_excel, name='generate_daily_report_excel'),
    path('download_daily_report_excel/<str:ticket_id>/', views.download_daily_report_excel, name='download_daily_report_excel'),
    path('bulk_upload_daily_entries/', views.bulk_upload_daily_entries, name='bulk_upload_daily_entries'),

    # ← ADD THESE
    path('send-email-preview/<str:ticket_id>/', views.daily_report_send_email_preview, name='daily_report_send_email_preview'),
    path('send-email/<str:ticket_id>/', views.daily_report_send_email, name='daily_report_send_email'),
]