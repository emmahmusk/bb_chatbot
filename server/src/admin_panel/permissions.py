from rest_framework.permissions import BasePermission



class IsAdminUserFlag(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user.profile, "is_admin", False)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, "admin") and request.user.admin.role in [
            "admin",
            "superadmin",
        ]


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            hasattr(request.user, "admin") and request.user.admin.role == "superadmin"
        )
