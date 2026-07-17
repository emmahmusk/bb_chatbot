from rest_framework import serializers


class HistoryMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(max_length=8000)


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=8000)
    history = HistoryMessageSerializer(many=True, required=False, default=list)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=25)


class SyncRequestSerializer(serializers.Serializer):
    symbols = serializers.ListField(
        child=serializers.CharField(max_length=16), required=False, allow_empty=False
    )
    prune = serializers.BooleanField(required=False, default=False)
