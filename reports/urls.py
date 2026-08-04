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
    
    # Added by charu
    path('generate_campaign_excel/<str:ticket_id>/', views.generate_campaign_excel, name='generate_campaign_excel'),
    path('download_campaign_excel/<str:ticket_id>/', views.download_campaign_excel, name='download_campaign_excel'),
    path('get_campaigns_excel_list/', views.get_campaigns_excel_list, name='get_campaigns_excel_list'),
    path('save_excel_edits_to_db/<str:ticket_id>/', views.save_excel_edits_to_db),
    path('publish_campaign_excel/<str:ticket_id>/', views.publish_campaign_excel, name='publish_campaign_excel'),
    path('get_line_item_excel_data/<str:ticket_id>/', views.get_line_item_excel_data, name='get_line_item_excel_data'),
    path('add_daily_entry/<str:ticket_id>/', views.add_daily_entry, name='add_daily_entry'),
    path('get_daily_entries/<str:ticket_id>/', views.get_daily_entries, name='get_daily_entries'),
    path('generate_daily_report_excel/<str:ticket_id>/', views.generate_daily_report_excel, name='generate_daily_report_excel'),
    path('download_daily_report_excel/<str:ticket_id>/', views.download_daily_report_excel, name='download_daily_report_excel'),
    path('bulk_upload_daily_entries/', views.bulk_upload_daily_entries, name='bulk_upload_daily_entries'),
    path('get_pacing_report/', views.get_pacing_report, name='get_pacing_report'),
    path('preview_campaign_excel_original/<str:ticket_id>/', views.preview_campaign_excel_original, name='preview_campaign_excel_original'),

    
]