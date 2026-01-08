"""
View handlers for the Care Plan Generator application.

Provides:
- Order CRUD operations and listing
- Care plan generation via LLM
- Real-time duplicate checking (HTMX endpoints)
- CSV export for pharma reporting
"""

import csv
import logging
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.contrib import messages
from django.utils import timezone

from .models import Provider, Patient, Order, CarePlan
from .forms import OrderForm
from .duplicates import (
    check_provider_duplicate,
    check_patient_duplicate,
    check_order_duplicate,
    get_existing_provider_by_npi,
    get_existing_patient_by_mrn,
)
from .llm_service import generate_care_plan

logger = logging.getLogger('careplan')


# =============================================================================
# Main Views
# =============================================================================

def index(request):
    """
    Home page - redirect to order creation.
    """
    return redirect('order_create')


def order_list(request):
    """
    List all orders with their status.
    """
    orders = Order.objects.select_related('patient', 'provider').all()[:50]
    return render(request, 'careplan/order_list.html', {
        'orders': orders,
    })


def order_create(request):
    """
    Create a new care plan order.
    """
    if request.method == 'POST':
        form = OrderForm(request.POST)

        if form.is_valid():
            try:
                # Create the order
                order = form.create_order()

                # Check for order duplicate warning
                order_dup = check_order_duplicate(
                    order.patient.id,
                    order.medication_name
                )

                if order_dup.is_warning:
                    messages.warning(request, order_dup.message)

                messages.success(
                    request,
                    f"Order #{order.id} created successfully. Ready to generate care plan."
                )
                return redirect('order_detail', order_id=order.id)

            except Exception as e:
                logger.error(f"Error creating order: {str(e)}")
                messages.error(request, f"Error creating order: {str(e)}")
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = OrderForm()

    return render(request, 'careplan/order_form.html', {
        'form': form,
    })


def order_detail(request, order_id):
    """
    View order details and generated care plan.
    """
    order = get_object_or_404(
        Order.objects.select_related('patient', 'provider'),
        id=order_id
    )

    care_plan = None
    try:
        care_plan = order.care_plan
    except CarePlan.DoesNotExist:
        pass

    return render(request, 'careplan/order_detail.html', {
        'order': order,
        'care_plan': care_plan,
    })


@require_POST
def generate_care_plan_view(request, order_id):
    """
    Generate a care plan for an order using the LLM.
    """
    order = get_object_or_404(Order, id=order_id)

    # Check if care plan already exists
    try:
        existing_plan = order.care_plan
        messages.info(request, "Care plan already exists. Regenerating...")
        existing_plan.delete()
    except CarePlan.DoesNotExist:
        pass

    try:
        # Generate the care plan
        content, elapsed_ms, model_used = generate_care_plan(order)

        # Save the care plan
        care_plan = CarePlan.objects.create(
            order=order,
            content=content,
            model_used=model_used,
            generation_time_ms=elapsed_ms
        )

        # Update order status
        order.status = 'completed'
        order.save()

        messages.success(
            request,
            f"Care plan generated successfully in {elapsed_ms}ms!"
        )

    except Exception as e:
        logger.error(f"Error generating care plan for Order #{order_id}: {str(e)}")
        messages.error(request, f"Error generating care plan: {str(e)}")

    return redirect('order_detail', order_id=order_id)


def download_care_plan(request, order_id):
    """
    Download the care plan as a text file.
    """
    order = get_object_or_404(Order, id=order_id)

    try:
        care_plan = order.care_plan
    except CarePlan.DoesNotExist:
        messages.error(request, "No care plan exists for this order.")
        return redirect('order_detail', order_id=order_id)

    # Create the response
    filename = f"care_plan_{order.patient.mrn}_{order.id}.txt"
    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Write header info
    response.write(f"CARE PLAN\n")
    response.write(f"{'=' * 60}\n\n")
    response.write(f"Patient: {order.patient.full_name}\n")
    response.write(f"MRN: {order.patient.mrn}\n")
    response.write(f"Provider: {order.provider.name} (NPI: {order.provider.npi})\n")
    response.write(f"Primary Diagnosis: {order.primary_diagnosis_code}\n")
    response.write(f"Medication: {order.medication_name}\n")
    response.write(f"Generated: {care_plan.generated_at.strftime('%Y-%m-%d %H:%M')}\n")
    response.write(f"\n{'=' * 60}\n\n")

    # Write care plan content
    response.write(care_plan.content)

    return response


# =============================================================================
# HTMX API Endpoints
# =============================================================================

@require_POST
def check_provider_api(request):
    """
    HTMX endpoint to check for provider duplicates.
    Returns HTML partial for display.
    """
    name = request.POST.get('provider_name', '').strip()
    npi = request.POST.get('provider_npi', '').strip()

    if not name or not npi or len(npi) != 10:
        return HttpResponse('')

    # Check for existing provider
    existing = get_existing_provider_by_npi(npi)
    if existing:
        return render(request, 'partials/provider_found.html', {
            'provider': existing,
            'message': f"Provider found: {existing.name}"
        })

    # Check for duplicates
    result = check_provider_duplicate(name, npi)

    if result.is_blocking:
        return render(request, 'partials/duplicate_error.html', {
            'message': result.message,
            'items': result.similar_items
        })
    elif result.is_warning:
        return render(request, 'partials/duplicate_warning.html', {
            'message': result.message,
            'items': result.similar_items
        })

    return HttpResponse('')


@require_POST
def check_patient_api(request):
    """
    HTMX endpoint to check for patient duplicates.
    Returns HTML partial for display.
    """
    first_name = request.POST.get('patient_first_name', '').strip()
    last_name = request.POST.get('patient_last_name', '').strip()
    mrn = request.POST.get('patient_mrn', '').strip()
    dob_str = request.POST.get('patient_dob', '')

    if not mrn or len(mrn) != 6:
        return HttpResponse('')

    # Parse DOB if provided
    dob = None
    if dob_str:
        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    # Check for existing patient
    existing = get_existing_patient_by_mrn(mrn)
    if existing:
        return render(request, 'partials/patient_found.html', {
            'patient': existing,
            'message': f"Patient found: {existing.full_name}"
        })

    # Check for duplicates
    result = check_patient_duplicate(first_name, last_name, mrn, dob)

    if result.is_blocking:
        return render(request, 'partials/duplicate_error.html', {
            'message': result.message,
            'items': result.similar_items
        })
    elif result.is_warning:
        return render(request, 'partials/duplicate_warning.html', {
            'message': result.message,
            'items': result.similar_items
        })

    return HttpResponse('')


# =============================================================================
# Care Plan Editing Endpoints (HTMX)
# =============================================================================

@require_GET
def care_plan_edit_form(request, care_plan_id):
    """
    HTMX endpoint to render the care plan edit form.
    """
    care_plan = get_object_or_404(CarePlan, id=care_plan_id)

    return render(request, 'partials/care_plan_edit.html', {
        'care_plan': care_plan,
        'order': care_plan.order,
    })


@require_POST
def save_care_plan_edit(request, care_plan_id):
    """
    HTMX endpoint to save edited care plan content.
    Returns the updated care plan display partial.
    """
    care_plan = get_object_or_404(CarePlan, id=care_plan_id)

    content = request.POST.get('content', '').strip()

    if not content:
        return HttpResponse(
            '<div class="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">'
            'Care plan content cannot be empty.</div>',
            status=400
        )

    # Update care plan
    care_plan.content = content
    care_plan.is_edited = True
    care_plan.edited_at = timezone.now()
    care_plan.save()

    # Return the display partial (non-edit mode)
    return render(request, 'partials/care_plan_display.html', {
        'care_plan': care_plan,
        'order': care_plan.order,
    })


@require_GET
def care_plan_display(request, care_plan_id):
    """
    HTMX endpoint to render the care plan display (cancel edit mode).
    """
    care_plan = get_object_or_404(CarePlan, id=care_plan_id)

    return render(request, 'partials/care_plan_display.html', {
        'care_plan': care_plan,
        'order': care_plan.order,
    })


# =============================================================================
# Export Functionality
# =============================================================================

@require_GET
def export_orders_csv(request):
    """
    Export all orders with care plans to CSV.
    Used for pharma reporting.
    """
    response = HttpResponse(content_type='text/csv')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    response['Content-Disposition'] = f'attachment; filename="orders_export_{timestamp}.csv"'

    writer = csv.writer(response)

    # Header row
    writer.writerow([
        'Order ID',
        'Status',
        'Created Date',
        'Patient First Name',
        'Patient Last Name',
        'Patient MRN',
        'Patient DOB',
        'Provider Name',
        'Provider NPI',
        'Primary Diagnosis Code',
        'Primary Diagnosis Description',
        'Additional Diagnoses',
        'Medication Name',
        'Medication History',
        'Care Plan Generated',
        'Care Plan Model',
        'Generation Time (ms)',
    ])

    # Data rows
    orders = Order.objects.select_related('patient', 'provider').all()

    for order in orders:
        care_plan_generated = 'No'
        care_plan_model = ''
        generation_time = ''

        try:
            care_plan = order.care_plan
            care_plan_generated = 'Yes'
            care_plan_model = care_plan.model_used
            generation_time = care_plan.generation_time_ms
        except CarePlan.DoesNotExist:
            pass

        writer.writerow([
            order.id,
            order.status,
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.patient.first_name,
            order.patient.last_name,
            order.patient.mrn,
            order.patient.dob.strftime('%Y-%m-%d') if order.patient.dob else '',
            order.provider.name,
            order.provider.npi,
            order.primary_diagnosis_code,
            order.primary_diagnosis_description,
            ', '.join(order.additional_diagnoses) if order.additional_diagnoses else '',
            order.medication_name,
            ', '.join(order.medication_history) if order.medication_history else '',
            care_plan_generated,
            care_plan_model,
            generation_time,
        ])

    return response
