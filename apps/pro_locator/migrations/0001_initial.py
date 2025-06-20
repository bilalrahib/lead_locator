# Generated by Django 4.2.21 on 2025-06-10 16:01

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("locator", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientProfile",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "client_name",
                    models.CharField(help_text="Client business name", max_length=255),
                ),
                (
                    "client_contact_name",
                    models.CharField(
                        blank=True, help_text="Primary contact name", max_length=255
                    ),
                ),
                (
                    "client_email",
                    models.EmailField(
                        blank=True, help_text="Client email address", max_length=254
                    ),
                ),
                (
                    "client_phone",
                    models.CharField(
                        blank=True, help_text="Client phone number", max_length=20
                    ),
                ),
                (
                    "client_zip_code",
                    models.CharField(
                        help_text="Client's primary ZIP code", max_length=10
                    ),
                ),
                (
                    "client_city",
                    models.CharField(
                        blank=True, help_text="Client's city", max_length=100
                    ),
                ),
                (
                    "client_state",
                    models.CharField(
                        blank=True, help_text="Client's state", max_length=50
                    ),
                ),
                (
                    "default_machine_type",
                    models.CharField(
                        choices=[
                            ("snack", "Snack Machine"),
                            ("drink", "Drink Machine"),
                            ("claw", "Claw Machine"),
                            ("combo", "Combo Machine"),
                            ("hot_food", "Hot Food Kiosk"),
                            ("ice_cream", "Ice Cream Machine"),
                            ("coffee", "Coffee Machine"),
                        ],
                        help_text="Default machine type for this client",
                        max_length=30,
                    ),
                ),
                (
                    "client_notes",
                    models.TextField(
                        blank=True, help_text="Additional notes about the client"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True, help_text="Whether this client is active"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        help_text="Elite/Professional user who owns this client",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_profiles",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Client Profile",
                "verbose_name_plural": "Client Profiles",
                "ordering": ["client_name"],
            },
        ),
        migrations.CreateModel(
            name="WhiteLabelSettings",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "company_name",
                    models.CharField(
                        help_text="Custom company name for branding", max_length=255
                    ),
                ),
                (
                    "company_logo",
                    models.ImageField(
                        blank=True,
                        help_text="Company logo for exports and client portal",
                        null=True,
                        upload_to="whitelabel/logos/",
                        validators=[
                            django.core.validators.FileExtensionValidator(
                                allowed_extensions=["png", "jpg", "jpeg", "svg"]
                            )
                        ],
                    ),
                ),
                (
                    "primary_color",
                    models.CharField(
                        default="#fb6d00",
                        help_text="Primary brand color (hex format)",
                        max_length=7,
                    ),
                ),
                (
                    "secondary_color",
                    models.CharField(
                        default="#ffffff",
                        help_text="Secondary brand color (hex format)",
                        max_length=7,
                    ),
                ),
                (
                    "company_website",
                    models.URLField(blank=True, help_text="Company website URL"),
                ),
                (
                    "company_phone",
                    models.CharField(
                        blank=True, help_text="Company phone number", max_length=20
                    ),
                ),
                (
                    "company_email",
                    models.EmailField(
                        blank=True, help_text="Company contact email", max_length=254
                    ),
                ),
                (
                    "custom_domain",
                    models.CharField(
                        blank=True,
                        help_text="Custom domain for client portal (e.g., clients.yourcompany.com)",
                        max_length=255,
                    ),
                ),
                (
                    "remove_vending_hive_branding",
                    models.BooleanField(
                        default=False,
                        help_text="Remove Vending Hive branding from client-facing materials",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True, help_text="Whether white-labeling is active"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="whitelabel_settings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "White Label Settings",
                "verbose_name_plural": "White Label Settings",
            },
        ),
        migrations.CreateModel(
            name="ClientSavedSearch",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "search_name",
                    models.CharField(
                        help_text="Custom name for this search", max_length=255
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True, help_text="Notes about this search for the client"
                    ),
                ),
                (
                    "is_shared_with_client",
                    models.BooleanField(
                        default=False,
                        help_text="Whether this search has been shared with the client",
                    ),
                ),
                (
                    "shared_at",
                    models.DateTimeField(
                        blank=True, help_text="When this search was shared", null=True
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "client_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="saved_searches",
                        to="pro_locator.clientprofile",
                    ),
                ),
                (
                    "search_history",
                    models.ForeignKey(
                        help_text="Reference to the original search",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_searches",
                        to="locator.searchhistory",
                    ),
                ),
            ],
            options={
                "verbose_name": "Client Saved Search",
                "verbose_name_plural": "Client Saved Searches",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ClientLocationData",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True, help_text="Client-specific notes for this location"
                    ),
                ),
                (
                    "priority",
                    models.IntegerField(
                        default=0,
                        help_text="Priority ranking for this client (higher = more priority)",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "New Lead"),
                            ("contacted", "Contacted"),
                            ("interested", "Interested"),
                            ("not_interested", "Not Interested"),
                            ("placed", "Machine Placed"),
                            ("rejected", "Rejected"),
                        ],
                        default="new",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "client_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_locations",
                        to="pro_locator.clientprofile",
                    ),
                ),
                (
                    "location_data",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_assignments",
                        to="locator.locationdata",
                    ),
                ),
                (
                    "saved_search",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assigned_locations",
                        to="pro_locator.clientsavedsearch",
                    ),
                ),
            ],
            options={
                "verbose_name": "Client Location Data",
                "verbose_name_plural": "Client Location Data",
                "ordering": ["-priority", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="clientsavedsearch",
            index=models.Index(
                fields=["client_profile", "created_at"],
                name="pro_locator_client__2ad17d_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="clientsavedsearch",
            index=models.Index(
                fields=["is_shared_with_client"], name="pro_locator_is_shar_3f5f7c_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="clientprofile",
            index=models.Index(
                fields=["user", "is_active"], name="pro_locator_user_id_910370_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="clientprofile",
            index=models.Index(
                fields=["client_zip_code"], name="pro_locator_client__a56afa_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="clientprofile",
            index=models.Index(
                fields=["created_at"], name="pro_locator_created_182dcc_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="clientlocationdata",
            index=models.Index(
                fields=["client_profile", "status"],
                name="pro_locator_client__326a0a_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="clientlocationdata",
            index=models.Index(
                fields=["status", "created_at"], name="pro_locator_status_f120d6_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="clientlocationdata",
            index=models.Index(
                fields=["priority"], name="pro_locator_priorit_2c229a_idx"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="clientlocationdata",
            unique_together={("client_profile", "location_data", "saved_search")},
        ),
    ]
