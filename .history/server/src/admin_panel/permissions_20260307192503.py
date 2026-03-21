from rest_framework.permissions import BasePermission



class IsAdminUserFlag(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        profile = getattr(request.user, "profile", None)
        return bool(getattr(profile, "is_admin", False))


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        profile = getattr(request.user, "profile", None)
        if getattr(profile, "is_admin", False):
            return True
        admin_obj = getattr(request.user, "admin", None)
        return getattr(admin_obj, "role", None) in ["admin", "superadmin"]


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            hasattr(request.user, "admin") and request.user.admin.role == "superadmin"
        )
