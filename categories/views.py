from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from . import models, serializers

# ══════════════════════════════════════════
# INVOICE BANK DETAILS
# ══════════════════════════════════════════

@api_view(['POST'])
def create_bank_detail(request):
    serializer = serializers.InvoiceBankDetailsSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_bank_details(request):
    qs = models.InvoiceBankDetails.objects.all().order_by('-id')
    serializer = serializers.InvoiceBankDetailsSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_bank_detail(request, id):
    obj = get_object_or_404(models.InvoiceBankDetails, id=id)
    serializer = serializers.InvoiceBankDetailsSerializer(obj)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
def edit_bank_detail(request, id):
    obj = get_object_or_404(models.InvoiceBankDetails, id=id)
    partial = request.method == 'PATCH'
    serializer = serializers.InvoiceBankDetailsSerializer(obj, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_bank_detail(request, id):
    obj = get_object_or_404(models.InvoiceBankDetails, id=id)
    obj.delete()
    return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ══════════════════════════════════════════
# INVOICE COMPANY ADDRESS
# ══════════════════════════════════════════

@api_view(['POST'])
def create_company_address(request):
    serializer = serializers.InvoiceCompanyAddressSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_company_addresses(request):
    qs = models.InvoiceCompanyAddress.objects.all().order_by('-id')
    serializer = serializers.InvoiceCompanyAddressSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_company_address(request, id):
    obj = get_object_or_404(models.InvoiceCompanyAddress, id=id)
    serializer = serializers.InvoiceCompanyAddressSerializer(obj)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
def edit_company_address(request, id):
    obj = get_object_or_404(models.InvoiceCompanyAddress, id=id)
    partial = request.method == 'PATCH'
    serializer = serializers.InvoiceCompanyAddressSerializer(obj, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_company_address(request, id):
    obj = get_object_or_404(models.InvoiceCompanyAddress, id=id)
    obj.delete()
    return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ══════════════════════════════════════════
# INVOICE AUTHORIZED PERSON
# ══════════════════════════════════════════

@api_view(['POST'])
def create_authorized_person(request):
    serializer = serializers.InvoiceAuthorizedPersonSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_authorized_persons(request):
    qs = models.InvoiceAuthorizedPerson.objects.all().order_by('-id')
    serializer = serializers.InvoiceAuthorizedPersonSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
def get_authorized_person(request, id):
    obj = get_object_or_404(models.InvoiceAuthorizedPerson, id=id)
    serializer = serializers.InvoiceAuthorizedPersonSerializer(obj, context={'request': request})
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
def edit_authorized_person(request, id):
    obj = get_object_or_404(models.InvoiceAuthorizedPerson, id=id)
    partial = request.method == 'PATCH'
    serializer = serializers.InvoiceAuthorizedPersonSerializer(obj, data=request.data, partial=partial, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_authorized_person(request, id):
    obj = get_object_or_404(models.InvoiceAuthorizedPerson, id=id)
    obj.delete()
    return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ══════════════════════════════════════════
# ADS FORMATS
# ══════════════════════════════════════════

@api_view(['POST'])
def create_ads_format(request):
    serializer = serializers.AdsFormatsSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_ads_formats(request):
    qs = models.AdsFormats.objects.all().order_by('-id')
    serializer = serializers.AdsFormatsSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_ads_format(request, id):
    obj = get_object_or_404(models.AdsFormats, id=id)
    serializer = serializers.AdsFormatsSerializer(obj)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
def edit_ads_format(request, id):
    obj = get_object_or_404(models.AdsFormats, id=id)
    partial = request.method == 'PATCH'
    serializer = serializers.AdsFormatsSerializer(obj, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_ads_format(request, id):
    obj = get_object_or_404(models.AdsFormats, id=id)
    obj.delete()
    return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ══════════════════════════════════════════
# METRICS
# ══════════════════════════════════════════

@api_view(['POST'])
def create_metric(request):
    serializer = serializers.MetricsSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_metrics(request):
    qs = models.Metrics.objects.all().order_by('-id')
    serializer = serializers.MetricsSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_metric(request, id):
    obj = get_object_or_404(models.Metrics, id=id)
    serializer = serializers.MetricsSerializer(obj)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
def edit_metric(request, id):
    obj = get_object_or_404(models.Metrics, id=id)
    partial = request.method == 'PATCH'
    serializer = serializers.MetricsSerializer(obj, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_metric(request, id):
    obj = get_object_or_404(models.Metrics, id=id)
    obj.delete()
    return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ══════════════════════════════════════════
# MODE OF PAYMENT
# ══════════════════════════════════════════

@api_view(['POST'])
def create_mode_of_payment(request):
    serializer = serializers.ModeOfPaymentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_modes_of_payment(request):
    qs = models.ModeOfPayment.objects.all().order_by('-id')
    serializer = serializers.ModeOfPaymentSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_mode_of_payment(request, id):
    obj = get_object_or_404(models.ModeOfPayment, id=id)
    serializer = serializers.ModeOfPaymentSerializer(obj)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
def edit_mode_of_payment(request, id):
    obj = get_object_or_404(models.ModeOfPayment, id=id)
    partial = request.method == 'PATCH'
    serializer = serializers.ModeOfPaymentSerializer(obj, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_mode_of_payment(request, id):
    obj = get_object_or_404(models.ModeOfPayment, id=id)
    obj.delete()
    return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ══════════════════════════════════════════
# PAYMENT TERMS
# ══════════════════════════════════════════

@api_view(['POST'])
def create_payment_term(request):
    serializer = serializers.PaymentTermsSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_payment_terms(request):
    qs = models.PaymentTerms.objects.all().order_by('-id')
    serializer = serializers.PaymentTermsSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_payment_term(request, id):
    obj = get_object_or_404(models.PaymentTerms, id=id)
    serializer = serializers.PaymentTermsSerializer(obj)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
def edit_payment_term(request, id):
    obj = get_object_or_404(models.PaymentTerms, id=id)
    partial = request.method == 'PATCH'
    serializer = serializers.PaymentTermsSerializer(obj, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_payment_term(request, id):
    obj = get_object_or_404(models.PaymentTerms, id=id)
    obj.delete()
    return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ══════════════════════════════════════════
# ETHNICITY
# ══════════════════════════════════════════

@api_view(['POST'])
def create_ethnicity(request):
    serializer = serializers.EthnicitySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_ethnicities(request):
    qs = models.Ethnicity.objects.all().order_by('-id')
    serializer = serializers.EthnicitySerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_ethnicity(request, id):
    obj = get_object_or_404(models.Ethnicity, id=id)
    serializer = serializers.EthnicitySerializer(obj)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
def edit_ethnicity(request, id):
    obj = get_object_or_404(models.Ethnicity, id=id)
    partial = request.method == 'PATCH'
    serializer = serializers.EthnicitySerializer(obj, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_ethnicity(request, id):
    obj = get_object_or_404(models.Ethnicity, id=id)
    obj.delete()
    return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

# ══════════════════════════════════════════
# DEPARTMENTS
# ══════════════════════════════════════════

@api_view(['POST'])
def create_department(request):
    serializer = serializers.DepartmentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_departments(request):
    qs = models.Department.objects.prefetch_related('roles').all().order_by('title')
    serializer = serializers.DepartmentSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_department(request, id):
    obj = get_object_or_404(models.Department, id=id)
    serializer = serializers.DepartmentSerializer(obj)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
def edit_department(request, id):
    obj = get_object_or_404(models.Department, id=id)
    partial = request.method == 'PATCH'
    serializer = serializers.DepartmentSerializer(obj, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_department(request, id):
    obj = get_object_or_404(models.Department, id=id)
    obj.delete()  # cascades and deletes its roles too, per on_delete=models.CASCADE
    return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# ══════════════════════════════════════════
# ROLES
# ══════════════════════════════════════════

@api_view(['POST'])
def create_role(request):
    serializer = serializers.RoleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_roles(request):
    qs = models.Role.objects.select_related('department').all().order_by('department__title', 'title')
    serializer = serializers.RoleSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_roles_by_department(request, department_id):
    """Roles for one specific department — e.g. populating a Role dropdown after a Department is picked."""
    qs = models.Role.objects.filter(department_id=department_id, is_active=True).order_by('title')
    serializer = serializers.RoleSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_role(request, id):
    obj = get_object_or_404(models.Role, id=id)
    serializer = serializers.RoleSerializer(obj)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
def edit_role(request, id):
    obj = get_object_or_404(models.Role, id=id)
    partial = request.method == 'PATCH'
    serializer = serializers.RoleSerializer(obj, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_role(request, id):
    obj = get_object_or_404(models.Role, id=id)
    obj.delete()
    return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
def create_user_credential(request):
    serializer = serializers.UserCredentialSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(serializers.UserCredentialSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_user_credentials(request):
    qs = models.UserCredential.objects.select_related('department', 'role').all().order_by('username')
    serializer = serializers.UserCredentialSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_user_credential(request, id):
    obj = get_object_or_404(models.UserCredential, id=id)
    serializer = serializers.UserCredentialSerializer(obj)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
def edit_user_credential(request, id):
    obj = get_object_or_404(models.UserCredential, id=id)
    partial = request.method == 'PATCH'
    serializer = serializers.UserCredentialSerializer(obj, data=request.data, partial=partial)
    if serializer.is_valid():
        user = serializer.save()
        return Response(serializers.UserCredentialSerializer(user).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_user_credential(request, id):
    obj = get_object_or_404(models.UserCredential, id=id)
    obj.delete()
    return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

#----------------------------------------------------------------
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from categories.models import UserCredential

# department title -> dashboard key. Add more here as you go.
DEPARTMENT_DASHBOARD_MAP = {
    "account manager": "account_manager",
    "creative ops": "creative_ops",
    "campaign ops": "campaign_ops",
    "finance": "finance",
}

@csrf_exempt
@require_POST
def login_view(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request body."}, status=400)

    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""

    if not email or not password:
        return JsonResponse({"error": "Email and password are required."}, status=400)

    try:
        user = UserCredential.objects.get(email__iexact=email)
    except UserCredential.DoesNotExist:
        return JsonResponse({"error": "Invalid email or password."}, status=401)

    if not user.is_active:
        return JsonResponse({"error": "This account has been deactivated."}, status=403)

    if not user.check_password(password):
        return JsonResponse({"error": "Invalid email or password."}, status=401)

    department_title = user.department.title
    dashboard_key = DEPARTMENT_DASHBOARD_MAP.get(department_title.strip().lower())

    return JsonResponse({
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "department": department_title,
            "department_id": user.department_id,
            "role": user.role.title,
            "role_id": user.role_id,
            "dashboard": dashboard_key,  # e.g. "account_manager" or "creative_ops"
        }
    })
#----------------------------------------------------------------