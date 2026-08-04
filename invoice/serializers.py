from rest_framework import serializers
from .models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    client_id = serializers.CharField(source='client.client_id', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = ['invoice_id', 'generated_at']