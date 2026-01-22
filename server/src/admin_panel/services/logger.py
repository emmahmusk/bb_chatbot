from admin_panel.models import AdminActionLog


def log_admin_action(admin, action_type, before, after):
    AdminActionLog.objects.create(
        admin=admin,
        action_type=action_type,
        before_value=str(before),
        after_value=str(after),
    )
