# serializers.py
from rest_framework import serializers

from betengine.models import Stock
from .models import OptionData


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = [
            "symbol",
            "company_name",
            "last_price",
            "updated_at",
            "created_at",
            "url",
        ]
        read_only_fields = ["last_price", "updated_at", "created_at"]

class OptionDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionData
        fields = "__all__"
