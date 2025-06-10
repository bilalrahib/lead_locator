from rest_framework import permissions
from django.contrib.auth.models import Permission


class IsAdminUser(permissions.BasePermission):
    """
    Permission to only allow admin users to access admin panel.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff
        )


class IsSuperUser(permissions.BasePermission):
    """
    Permission to only allow superusers for sensitive operations.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser
        )


class HasAdminPanelPermission(permissions.BasePermission):
    """
    Custom permission for admin panel operations.
    """
    
    permission_map = {
        'GET': 'view',
        'OPTIONS': 'view',
        'HEAD': 'view',
        'POST': 'add',
        'PUT': 'change',
        'PATCH': 'change',
        'DELETE': 'delete',
    }

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        if request.user.is_superuser:
            return True
        
        if not request.user.is_staff:
            return False
        
        # Check specific permissions based on view and action
        app_label = getattr(view, 'permission_app_label', 'admin_panel')
        model_name = getattr(view, 'permission_model_name', 'adminpanel')
        action = self.permission_map.get(request.method, 'view')
        
        permission_code = f"{app_label}.{action}_{model_name}"
        return request.user.has_perm(permission_code)


class CanManageUsers(permissions.BasePermission):
    """
    Permission for user management operations.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff and
            (request.user.is_superuser or 
             request.user.has_perm('accounts.change_customuser'))
        )


class CanManageSubscriptions(permissions.BasePermission):
    """
    Permission for subscription management operations.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff and
            (request.user.is_superuser or 
             request.user.has_perm('project_core.change_subscriptionplan'))
        )


class CanViewAnalytics(permissions.BasePermission):
    """
    Permission for viewing analytics and reports.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff and
            (request.user.is_superuser or 
             request.user.has_perm('admin_panel.view_analytics'))
        )


class CanManageContent(permissions.BasePermission):
    """
    Permission for content management operations.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff and
            (request.user.is_superuser or 
             request.user.has_perm('admin_panel.change_contenttemplate'))
        )