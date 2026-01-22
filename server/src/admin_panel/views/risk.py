# src/adminpanel/views/risk.py

import uuid
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from user.serializers import GlobalRiskSettingsSerializer, MarketRuleSerializer


# Mock in-memory data store
_global_risk_settings = {"patron_risk": 1000.0, "company_risk": 100000.0}
_market_rules_data = [
    {"id": str(uuid.uuid4()), "ticker": "MSFT", "patron_risk": 5000.0, "company_risk": 300000.0},
    {"id": str(uuid.uuid4()), "ticker": "GOOG", "patron_risk": 2000.0, "company_risk": 150000.0},
]


class GlobalRiskSettingsView(APIView):
    def get(self, request):
        try:
            serializer = GlobalRiskSettingsSerializer(_global_risk_settings)
            return Response(serializer.data)
        except Exception as e:
            print(f"Error fetching global risk settings: {e}")
            return Response(
                {"error": "Could not retrieve global risk settings."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request):
        serializer = GlobalRiskSettingsSerializer(data=request.data)
        if serializer.is_valid():
            try:
                _global_risk_settings.update(serializer.validated_data)
                return Response(
                    {"message": "Global risk settings updated successfully.", **_global_risk_settings},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                print(f"Error updating global risk settings: {e}")
                return Response(
                    {"error": "Could not update global risk settings."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MarketRuleListView(APIView):
    def get(self, request):
        try:
            serializer = MarketRuleSerializer(_market_rules_data, many=True)
            return Response(serializer.data)
        except Exception as e:
            print(f"Error fetching market rules: {e}")
            return Response(
                {"error": "Could not retrieve market rules."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        serializer = MarketRuleSerializer(data=request.data)
        if serializer.is_valid():
            try:
                new_rule = serializer.validated_data
                new_rule['id'] = str(uuid.uuid4())
                _market_rules_data.append(new_rule)
                return Response(
                    {"message": "Market rule created successfully.", **new_rule},
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                print(f"Error creating market rule: {e}")
                return Response(
                    {"error": "Could not create market rule."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MarketRuleDetailView(APIView):
    def get(self, request, rule_id):
        try:
            rule = next((r for r in _market_rules_data if r['id'] == rule_id), None)
            if rule:
                serializer = MarketRuleSerializer(rule)
                return Response(serializer.data)
            else:
                return Response(
                    {"error": "Market rule not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            print(f"Error fetching market rule {rule_id}: {e}")
            return Response(
                {"error": "Could not retrieve market rule."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, rule_id):
        serializer = MarketRuleSerializer(data=request.data)
        if serializer.is_valid():
            try:
                rule_found = False
                for i, rule in enumerate(_market_rules_data):
                    if rule['id'] == rule_id:
                        _market_rules_data[i].update(serializer.validated_data)
                        rule_found = True
                        return Response(
                            {"message": "Market rule updated successfully.", "id": rule_id, **_market_rules_data[i]},
                            status=status.HTTP_200_OK
                        )
                if not rule_found:
                    return Response(
                        {"error": "Market rule not found for update."},
                        status=status.HTTP_404_NOT_FOUND
                    )
            except Exception as e:
                print(f"Error updating market rule {rule_id}: {e}")
                return Response(
                    {"error": "Could not update market rule."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, rule_id):
        try:
            global _market_rules_data
            initial_len = len(_market_rules_data)
            _market_rules_data = [r for r in _market_rules_data if r['id'] != rule_id]
            if len(_market_rules_data) < initial_len:
                return Response(
                    {"message": "Market rule deleted successfully."},
                    status=status.HTTP_204_NO_CONTENT
                )
            else:
                return Response(
                    {"error": "Market rule not found for deletion."},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            print(f"Error deleting market rule {rule_id}: {e}")
            return Response(
                {"error": "Could not delete market rule."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
