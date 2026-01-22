# Register your models here.
# from django.contrib import admin
# from .models import OptionContract


# @admin.register(OptionContract)
# class OptionContractAdmin(admin.ModelAdmin):
#     list_display = ("ticker", "contract_type", "strike_price", "ask_price", "bid_price", "is_active", "updated_at")
#     list_filter = ("contract_type", "exercise_style", "is_active")
#     search_fields = ("ticker", "underlying_ticker")


# class Admin(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     role = models.CharField(choices=[('admin', 'Admin'), ('superadmin', 'Super Admin')], max_length=20)

# class AdminLog(models.Model):
#     admin = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True)
#     timestamp = models.DateTimeField(auto_now_add=True)
#     change_type = models.CharField(max_length=100)
#     before = models.JSONField()
#     after = models.JSONField()
