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


class CapabilityRequiredMixin(AccessMixin):
    """Verify that current user has the required capability."""

    required_capability = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if self.required_capability:
            from apps.core.permissions import has_capability
            if not has_capability(request.user, self.required_capability):
                raise PermissionDenied(f"Missing required capability: {self.required_capability}")

        return super().dispatch(request, *args, **kwargs)


class HostelerOnlyMixin(AccessMixin):
    """Guarantees only authenticated hostelers can access endpoint (Community)."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        from apps.core.permissions import Capability, has_capability
        if not has_capability(request.user, Capability.COMMUNITY_ACCESS):
            raise PermissionDenied("Community is reserved for residents only.")

        return super().dispatch(request, *args, **kwargs)


class HtmxMixin:
    """Helper mixin to easily handle HTMX vs standard HTTP requests."""

    def is_htmx(self):
        return self.request.headers.get("HX-Request") == "true"
