# Generated migration for admin_panel

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminDashboardStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stat_date', models.DateField(unique=True)),
                ('total_users', models.IntegerField(default=0)),
                ('new_users_today', models.IntegerField(default=0)),
                ('active_subscriptions', models.IntegerField(default=0)),
                ('revenue_today', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('searches_today', models.IntegerField(default=0)),
                ('support_tickets_open', models.IntegerField(default=0)),
                ('cache_data', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Dashboard Stats',
                'verbose_name_plural': 'Dashboard Stats',
                'ordering': ['-stat_date'],
            },
        ),
        migrations.CreateModel(
            name='SystemSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text='Setting key', max_length=100, unique=True)),
                ('value', models.TextField(help_text='Setting value')),
                ('setting_type', models.CharField(choices=[('string', 'String'), ('integer', 'Integer'), ('float', 'Float'), ('boolean', 'Boolean'), ('json', 'JSON')], default='string', max_length=20)),
                ('description', models.TextField(help_text='Setting description')),
                ('category', models.CharField(default='general', help_text='Setting category for grouping', max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('is_editable', models.BooleanField(default=True, help_text='Whether this setting can be edited via admin panel')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_settings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'System Setting',
                'verbose_name_plural': 'System Settings',
                'ordering': ['category', 'key'],
            },
        ),
        migrations.CreateModel(
            name='ContentTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Template name', max_length=200)),
                ('template_type', models.CharField(choices=[('email', 'Email Template'), ('social_post', 'Social Media Post'), ('banner', 'Banner/Image'), ('tutorial', 'Tutorial Link'), ('landing_page', 'Landing Page'), ('video', 'Video Content')], max_length=20)),
                ('title', models.CharField(help_text='Template title/subject', max_length=300)),
                ('content', models.TextField(help_text='Template content/body')),
                ('preview_url', models.URLField(blank=True, help_text='Preview or demo URL')),
                ('thumbnail', models.ImageField(blank=True, help_text='Template thumbnail', null=True, upload_to='admin_panel/templates/')),
                ('description', models.TextField(blank=True, help_text='Template description')),
                ('tags', models.CharField(blank=True, help_text='Comma-separated tags', max_length=500)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived')], default='draft', max_length=20)),
                ('is_featured', models.BooleanField(default=False)),
                ('usage_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_templates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Content Template',
                'verbose_name_plural': 'Content Templates',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AdminLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action_type', models.CharField(choices=[('user_activate', 'User Activated'), ('user_deactivate', 'User Deactivated'), ('subscription_change', 'Subscription Changed'), ('credit_grant', 'Credits Granted'), ('affiliate_approve', 'Affiliate Approved'), ('affiliate_reject', 'Affiliate Rejected'), ('content_create', 'Content Created'), ('content_update', 'Content Updated'), ('content_delete', 'Content Deleted'), ('system_setting', 'System Setting Changed'), ('bulk_operation', 'Bulk Operation')], max_length=30)),
                ('description', models.TextField(help_text='Detailed description of the action')),
                ('before_state', models.JSONField(blank=True, default=dict, help_text='State before the action')),
                ('after_state', models.JSONField(blank=True, default=dict, help_text='State after the action')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('admin_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='admin_actions', to=settings.AUTH_USER_MODEL)),
                ('target_user', models.ForeignKey(blank=True, help_text='User affected by the action', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admin_actions_received', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Admin Log',
                'verbose_name_plural': 'Admin Logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='systemsettings',
            index=models.Index(fields=['category', 'is_active'], name='admin_panel_systemse_categor_9f7e64_idx'),
        ),
        migrations.AddIndex(
            model_name='systemsettings',
            index=models.Index(fields=['key'], name='admin_panel_systemse_key_9a8b4c_idx'),
        ),
        migrations.AddIndex(
            model_name='contenttemplate',
            index=models.Index(fields=['template_type', 'status'], name='admin_panel_content_templat_47b8a9_idx'),
        ),
        migrations.AddIndex(
            model_name='contenttemplate',
            index=models.Index(fields=['status', 'is_featured'], name='admin_panel_content_status_d4c8e1_idx'),
        ),
        migrations.AddIndex(
            model_name='contenttemplate',
            index=models.Index(fields=['created_at'], name='admin_panel_content_created_c9f7e3_idx'),
        ),
        migrations.AddIndex(
            model_name='adminlog',
            index=models.Index(fields=['admin_user', 'created_at'], name='admin_panel_adminlo_admin_u_8b4c9f_idx'),
        ),
        migrations.AddIndex(
            model_name='adminlog',
            index=models.Index(fields=['action_type', 'created_at'], name='admin_panel_adminlo_action__d7e8c2_idx'),
        ),
        migrations.AddIndex(
            model_name='adminlog',
            index=models.Index(fields=['target_user', 'created_at'], name='admin_panel_adminlo_target__f9a3e6_idx'),
        ),
    ]