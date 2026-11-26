from django.conf import settings
from django.http import JsonResponse
from django.views.generic import TemplateView


class LandingPageView(TemplateView):
    template_name = "risk_site/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contact_email"] = settings.CONTACT_EMAIL
        return context


def health_check(request):
    return JsonResponse({"status": "ok", "service": "bullbear-risk-website"})
