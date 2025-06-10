from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models import Q
from typing import Dict, List, Optional
import logging

from ..models import ContentTemplate, SystemSettings, AdminLog

User = get_user_model()
logger = logging.getLogger(__name__)


class ContentManagementService:
    """Service for content management operations."""

    @staticmethod
    def get_templates(template_type: str = None, status: str = None, 
                     search: str = None, page: int = 1, page_size: int = 20) -> Dict:
        """
        Get content templates with filtering and pagination.
        
        Args:
            template_type: Filter by template type
            status: Filter by status
            search: Search in name/title/description
            page: Page number
            page_size: Results per page
            
        Returns:
            Dict with templates and pagination info
        """
        queryset = ContentTemplate.objects.select_related('created_by')
        
        # Apply filters
        if template_type:
            queryset = queryset.filter(template_type=template_type)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
        
        # Count total
        total_count = queryset.count()
        
        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        templates = queryset.order_by('-created_at')[start:end]
        
        return {
            'templates': templates,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        }

    @staticmethod
    @transaction.atomic
    def create_template(template_data: Dict, admin_user: User) -> Dict:
        """
        Create a new content template.
        
        Args:
            template_data: Template data
            admin_user: Admin creating the template
            
        Returns:
            Dict with creation results
        """
        try:
            template_data['created_by'] = admin_user
            template = ContentTemplate.objects.create(**template_data)
            
            # Log action
            AdminLog.objects.create(
                admin_user=admin_user,
                action_type='content_create',
                description=f"Created template: {template.name}",
                after_state={
                    'template_id': str(template.id),
                    'name': template.name,
                    'type': template.template_type
                }
            )
            
            logger.info(f"Template {template.name} created by {admin_user.email}")
            
            return {
                'success': True,
                'template_id': str(template.id),
                'message': f"Successfully created template {template.name}"
            }
            
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    @transaction.atomic
    def update_template(template_id: str, template_data: Dict, admin_user: User) -> Dict:
        """
        Update a content template.
        
        Args:
            template_id: Template ID
            template_data: Updated template data
            admin_user: Admin updating the template
            
        Returns:
            Dict with update results
        """
        try:
            template = ContentTemplate.objects.get(id=template_id)
            
            # Store old state for logging
            old_state = {
                'name': template.name,
                'type': template.template_type,
                'status': template.status
            }
            
            # Update template
            for field, value in template_data.items():
                setattr(template, field, value)
            template.save()
            
            # Log action
            AdminLog.objects.create(
                admin_user=admin_user,
                action_type='content_update',
                description=f"Updated template: {template.name}",
                before_state=old_state,
                after_state={
                    'name': template.name,
                    'type': template.template_type,
                    'status': template.status
                }
            )
            
            logger.info(f"Template {template.name} updated by {admin_user.email}")
            
            return {
                'success': True,
                'message': f"Successfully updated template {template.name}"
            }
            
        except ContentTemplate.DoesNotExist:
            return {'success': False, 'error': 'Template not found'}
        except Exception as e:
            logger.error(f"Error updating template: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    @transaction.atomic
    def delete_template(template_id: str, admin_user: User) -> Dict:
        """
        Delete a content template.
        
        Args:
            template_id: Template ID
            admin_user: Admin deleting the template
            
        Returns:
            Dict with deletion results
        """
        try:
            template = ContentTemplate.objects.get(id=template_id)
            template_name = template.name
            
            # Store state for logging
            old_state = {
                'name': template.name,
                'type': template.template_type,
                'status': template.status
            }
            
            template.delete()
            
            # Log action
            AdminLog.objects.create(
                admin_user=admin_user,
                action_type='content_delete',
                description=f"Deleted template: {template_name}",
                before_state=old_state
            )
            
            logger.info(f"Template {template_name} deleted by {admin_user.email}")
            
            return {
                'success': True,
                'message': f"Successfully deleted template {template_name}"
            }
            
        except ContentTemplate.DoesNotExist:
            return {'success': False, 'error': 'Template not found'}
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_template_statistics() -> Dict:
        """
        Get content template statistics.
        
        Returns:
            Dict with template statistics
        """
        total_templates = ContentTemplate.objects.count()
        
        # Count by type
        type_distribution = {}
        for choice in ContentTemplate.TEMPLATE_TYPES:
            type_key = choice[0]
            count = ContentTemplate.objects.filter(template_type=type_key).count()
            type_distribution[type_key] = count
        
        # Count by status
        status_distribution = {}
        for choice in ContentTemplate.CONTENT_STATUS:
            status_key = choice[0]
            count = ContentTemplate.objects.filter(status=status_key).count()
            status_distribution[status_key] = count
        
        # Most used templates
        popular_templates = ContentTemplate.objects.filter(
            usage_count__gt=0
        ).order_by('-usage_count')[:5]
        
        return {
            'total_templates': total_templates,
            'type_distribution': type_distribution,
            'status_distribution': status_distribution,
            'popular_templates': [
                {
                    'id': str(t.id),
                    'name': t.name,
                    'type': t.template_type,
                    'usage_count': t.usage_count
                }
                for t in popular_templates
            ]
        }

    @staticmethod
    def get_system_settings(category: str = None) -> List[SystemSettings]:
        """
        Get system settings.
        
        Args:
            category: Filter by category
            
        Returns:
            List of system settings
        """
        queryset = SystemSettings.objects.filter(is_active=True)
        
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset.order_by('category', 'key')

    @staticmethod
    @transaction.atomic
    def update_system_setting(setting_id: int, value: str, admin_user: User) -> Dict:
        """
        Update a system setting.
        
        Args:
            setting_id: Setting ID
            value: New value
            admin_user: Admin updating the setting
            
        Returns:
            Dict with update results
        """
        try:
            setting = SystemSettings.objects.get(id=setting_id, is_editable=True)
            
            old_value = setting.value
            setting.value = value
            setting.updated_by = admin_user
            setting.save()
            
            # Log action
            AdminLog.objects.create(
                admin_user=admin_user,
                action_type='system_setting',
                description=f"Updated setting {setting.key}",
                before_state={'value': old_value},
                after_state={'value': value}
            )
            
            logger.info(f"Setting {setting.key} updated by {admin_user.email}")
            
            return {
                'success': True,
                'message': f"Successfully updated setting {setting.key}"
            }
            
        except SystemSettings.DoesNotExist:
            return {'success': False, 'error': 'Setting not found or not editable'}
        except Exception as e:
            logger.error(f"Error updating setting: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_setting_categories() -> List[str]:
        """
        Get unique setting categories.
        
        Returns:
            List of category names
        """
        return list(
            SystemSettings.objects.values_list('category', flat=True).distinct()
        )