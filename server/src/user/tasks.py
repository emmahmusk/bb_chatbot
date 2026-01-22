# In yourapp/tasks.py (or utils.py)

from django.contrib.auth import get_user_model
from .models import Profile
User = get_user_model()

def recalculate_user_crs_exposure(user_id):
    try:
        user = User.objects.get(id=user_id)
        # Calls the Profile method that recalculates and saves the score
        user.profile.update_crs_risk()
    except (User.DoesNotExist, Profile.DoesNotExist, AttributeError):
        pass