"""Health-check endpoint (public; no auth, no patient data)."""

from django.http import JsonResponse


def health_check(request):
    """Liveness probe used by CI, docker-compose and the frontend."""
    return JsonResponse({"status": "ok"})
