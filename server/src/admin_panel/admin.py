from django.contrib.auth.models import User
from django.db import models


# Register your models here.
class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(
        choices=[("admin", "Admin"), ("superadmin", "Super Admin")], max_length=20
    )


# class AdminLog(models.Model):
#     admin = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True)
#     timestamp = models.DateTimeField(auto_now_add=True)
#     change_type = models.CharField(max_length=100)
#     before = models.JSONField()
#     after = models.JSONField()
