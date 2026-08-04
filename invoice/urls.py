from django.urls import path
from . import views

urlpatterns = [
    path('generate_monthly_invoice/', views.generate_monthly_invoice, name='generate_monthly_invoice'),
    path('set_invoice_discount/<str:invoice_id>/', views.set_invoice_discount, name='set_invoice_discount'),
    path('set_invoice_tax/<str:invoice_id>/', views.set_invoice_tax, name='set_invoice_tax'),
    path('record_payment/<str:invoice_id>/', views.record_payment, name='record_payment'),
    path('get_invoices_by_client/<str:client_id>/', views.get_invoices_by_client, name='get_invoices_by_client'),
    path('get_all_clients/', views.get_all_clients, name='get_all_clients'),
    path('get_client_invoice_info/<str:client_id>/', views.get_client_invoice_info, name='get_client_invoice_info'),
    path('get_available_campaigns/<str:client_id>/', views.get_available_campaigns, name='get_available_campaigns'),
    path('get_invoice_detail/<str:invoice_id>/', views.get_invoice_detail, name='get_invoice_detail'),

    # ← ADD THESE — this is what was missing, causing the 404
    path('view_invoice_pdf/<str:invoice_id>/', views.view_invoice_pdf, name='view_invoice_pdf'),
    path('download_invoice_pdf/<str:invoice_id>/', views.download_invoice_pdf, name='download_invoice_pdf'),
]