from rest_framework import generics, permissions
from .models import CompetitionMember
from .serializers import CompetitionMemberSerializer

class CompetitionMemberListAPIView(generics.ListAPIView):
    """
    API endpoint to list all competition memberships for the authenticated user.
    """
    serializer_class = CompetitionMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return CompetitionMember.objects.filter(user=user)
