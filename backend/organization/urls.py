"""Hospital setup API routes (Spec 003, M2; plan.md API table)."""

from rest_framework.routers import DefaultRouter

from .views import (
    DepartmentViewSet,
    ServiceCategoryViewSet,
    ServiceViewSet,
    StaffViewSet,
    VisitTypeViewSet,
)

router = DefaultRouter()
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"staff", StaffViewSet, basename="staff")
router.register(r"services", ServiceViewSet, basename="service")
router.register(
    r"service-categories", ServiceCategoryViewSet, basename="service-category"
)
router.register(r"visit-types", VisitTypeViewSet, basename="visit-type")

urlpatterns = router.urls
