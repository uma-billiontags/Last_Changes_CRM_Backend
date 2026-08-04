from django.urls import path
from .views import LeadListAPIView, LeadCategoryListAPIView, LeadCategorizeAPIView, LeadDeleteAPIView

urlpatterns = [
    path("get_leads/", LeadListAPIView.as_view(), name="get-leads"),
    path("get_lead_categories/", LeadCategoryListAPIView.as_view(), name="get-lead-categories"),
    path("categorize_lead/<int:pk>/", LeadCategorizeAPIView.as_view(), name="categorize-lead"),
    path("delete_lead/<int:pk>/", LeadDeleteAPIView.as_view(), name="delete-lead"),  # ← NEW
]