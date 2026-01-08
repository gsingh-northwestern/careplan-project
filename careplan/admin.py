"""
Admin interface configuration for the Care Plan Generator.
"""

from django.contrib import admin
from .models import Provider, Patient, Order, CarePlan


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'npi', 'created_at']
    search_fields = ['name', 'npi']
    ordering = ['name']


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'mrn', 'dob', 'created_at']
    search_fields = ['first_name', 'last_name', 'mrn']
    list_filter = ['created_at']
    ordering = ['last_name', 'first_name']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'provider', 'medication_name', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__mrn', 'medication_name']
    raw_id_fields = ['patient', 'provider']
    ordering = ['-created_at']


@admin.register(CarePlan)
class CarePlanAdmin(admin.ModelAdmin):
    list_display = ['order', 'model_used', 'generation_time_ms', 'generated_at']
    list_filter = ['model_used', 'generated_at']
    raw_id_fields = ['order']
    ordering = ['-generated_at']
