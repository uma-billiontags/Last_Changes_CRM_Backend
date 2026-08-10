from rest_framework import serializers
from .models import *


# ==============================
# CAMPAIGN SERIALIZERS
# ==============================

class CreativeSerializer(serializers.ModelSerializer):
    main_asset_url = serializers.SerializerMethodField()
    #backup_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Creative
        fields = [
            'id',
            'line_item',
            'creative_name',

            'main_asset',
            'main_asset_url',

            #'backup_image',
            #'backup_image_url',

            'dimensions',
            'aspect_ratio',
            'file_size',

            'click_through_url',
            'appended_html_tag',
            'integration_code',
            'notes',
            'uploaded_at',
            
            'creative_id',
        ]

        read_only_fields = [
            'uploaded_at',
            'main_asset_url',
        ]

    def get_main_asset_url(self, obj):
        request = self.context.get('request')

        if obj.main_asset and request:
            return request.build_absolute_uri(obj.main_asset.url)

        return None

  

# ==============================
# THIRD PARTY CREATIVE
# ==============================

class ThirdPartyCreativeSerializer(serializers.ModelSerializer):

    input_file_url = serializers.SerializerMethodField()
    backup_image_url = serializers.SerializerMethodField()

    class Meta:
        model = ThirdPartyCreative

        fields = [
            'id',
            'line_item',
            'input_file',
            'input_file_url',
            'backup_image',
            'backup_image_url',
            'uploaded_at',
            
            'creative_id',
        ]

        read_only_fields = [
            'uploaded_at',
            'input_file_url',
            'backup_image_url',
        ]

    def get_input_file_url(self, obj):

        request = self.context.get('request')

        if obj.input_file and request:
            return request.build_absolute_uri(obj.input_file.url)

        return None

    def get_backup_image_url(self, obj):

        request = self.context.get('request')

        if obj.backup_image and request:
            return request.build_absolute_uri(obj.backup_image.url)

        return None


# ==============================
# LINE ITEM
# ==============================

class LineItemSerializer(serializers.ModelSerializer):
    creatives = CreativeSerializer(
        many=True,
        read_only=True,
        source='creatives_detail'  
    )

    third_party_creatives = ThirdPartyCreativeSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = LineItem
        fields = '__all__'


# ==============================
# CAMPAIGN
# ==============================

class CampaignSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)

    line_items = LineItemSerializer(many=True,read_only=True)

    client = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Campaign
        fields = '__all__'
        read_only_fields = ['created_at'] 