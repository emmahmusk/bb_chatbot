from django.contrib import admin

from .models import CRSRiskAuditLog


@admin.register(CRSRiskAuditLog)
class CRSRiskAuditLogAdmin(admin.ModelAdmin):
    list_display = ("user", "changed_by", "previous_score", "new_score", "timestamp")
    search_fields = ("user__email", "changed_by__email")
    list_filter = ("new_level", "timestamp")


admin.site.site_title = "BullBear Admin"
admin.site.site_header = "BullBear Admin"
admin.site.index_title = "BullBear Admin"


# @admin.register(Profile)
# class ProfileAdmin(admin.ModelAdmin):
#     list_display = ("user__email", "user__first_name", "user__last_name")
