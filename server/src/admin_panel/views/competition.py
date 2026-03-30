"""
admin_panel/views/competition.py

Admin-facing CRUD endpoints for the Competition model.

Endpoints (all require IsAdmin permission):
  GET    /admin/competitions/              – list all competitions (paginated)
  GET    /admin/competitions/<id>/        – retrieve single competition
  PATCH  /admin/competitions/<id>/update/ – partially update a competition
  DELETE /admin/competitions/<id>/delete/ – delete a competition
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from betengine.models import Competition
from betengine.serializers import CompetitionSerializer
from admin_panel.permissions import IsAdmin


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
from rest_framework.pagination import PageNumberPagination

class CompetitionAdminPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# ---------------------------------------------------------------------------
# List all competitions
# ---------------------------------------------------------------------------
class AdminCompetitionListView(generics.ListAPIView):
    """
    GET /admin/competitions/
    Returns a paginated list of all competitions, newest first.
    Supports optional ?status=<status> and ?search=<name> query params.
    """
    permission_classes = [IsAdmin]
    serializer_class = CompetitionSerializer
    pagination_class = CompetitionAdminPagination

    def get_queryset(self):
        qs = Competition.objects.all().order_by("-created_at")

        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)

        return qs


# ---------------------------------------------------------------------------
# Retrieve a single competition
# ---------------------------------------------------------------------------
class AdminCompetitionDetailView(generics.RetrieveAPIView):
    """
    GET /admin/competitions/<id>/
    Returns full details of a single competition.
    """
    permission_classes = [IsAdmin]
    serializer_class = CompetitionSerializer
    queryset = Competition.objects.all()
    lookup_field = "pk"


# ---------------------------------------------------------------------------
# Update a single competition
# ---------------------------------------------------------------------------
class AdminCompetitionUpdateView(generics.UpdateAPIView):
    """
    PATCH /admin/competitions/<id>/update/
    Partially update any writable field on a competition.
    Admin can change name, description, status, prizes, dates, etc.
    """
    permission_classes = [IsAdmin]
    serializer_class = CompetitionSerializer
    queryset = Competition.objects.all()
    lookup_field = "pk"
    http_method_names = ["patch"]  # partial updates only via PATCH

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True  # enforce partial update
        return super().update(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Delete a single competition
# ---------------------------------------------------------------------------
class AdminCompetitionDeleteView(APIView):
    """
    DELETE /admin/competitions/<id>/delete/
    Permanently delete a competition and all related members/bets.
    Returns 204 No Content on success.
    """
    permission_classes = [IsAdmin]

    def delete(self, request, pk, *args, **kwargs):
        competition = get_object_or_404(Competition, pk=pk)
        competition_name = competition.name
        competition.delete()
        return Response(
            {"detail": f"Competition '{competition_name}' (id={pk}) has been deleted."},
            status=status.HTTP_204_NO_CONTENT,
        )
