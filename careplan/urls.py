"""
URL configuration for the Care Plan Generator app.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Main views
    path('', views.index, name='index'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/new/', views.order_create, name='order_create'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/generate/', views.generate_care_plan_view, name='generate_care_plan'),
    path('orders/<int:order_id>/download/', views.download_care_plan, name='download_care_plan'),

    # HTMX API endpoints
    path('api/check-provider/', views.check_provider_api, name='check_provider_api'),
    path('api/check-patient/', views.check_patient_api, name='check_patient_api'),

    # Care plan editing endpoints (HTMX)
    path('api/care-plan/<int:care_plan_id>/edit-form/', views.care_plan_edit_form, name='care_plan_edit_form'),
    path('api/care-plan/<int:care_plan_id>/save/', views.save_care_plan_edit, name='save_care_plan_edit'),
    path('api/care-plan/<int:care_plan_id>/display/', views.care_plan_display, name='care_plan_display'),

    # Export
    path('export/csv/', views.export_orders_csv, name='export_orders_csv'),
]
