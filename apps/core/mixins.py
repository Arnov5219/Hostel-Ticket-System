from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(AccessMixin):
    """Verify that the current user has one of the allowed roles."""

    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if self.allowed_roles and request.user.role not in self.allowed_roles:
            if not request.user.is_superuser:
                raise PermissionDenied("You do not have permission to access this resource.")

        return super().dispatch(request, *args, **kwargs)


class HtmxMixin:
    """Helper mixin to easily handle HTMX vs standard HTTP requests."""

    def is_htmx(self):
        return self.request.headers.get("HX-Request") == "true"
