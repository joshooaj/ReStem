from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Job, CreditPackage, Purchase, SiteSettings


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for custom User model."""
    list_display = ('email', 'username', 'credits', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'username')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Credits', {'fields': ('credits',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('email', 'credits')}),
    )


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """Admin configuration for Job model."""
    list_display = ('id', 'user', 'original_filename', 'model', 'status', 'created_at', 'completed_at')
    list_filter = ('status', 'model', 'created_at')
    search_fields = ('original_filename', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(CreditPackage)
class CreditPackageAdmin(admin.ModelAdmin):
    """Admin configuration for CreditPackage model."""
    list_display = ('name', 'credits', 'price_dollars', 'is_active')
    list_filter = ('is_active',)
    ordering = ('credits',)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    """Admin configuration for Purchase model."""
    list_display = ('id', 'user', 'package', 'amount_cents', 'is_completed', 'created_at')
    list_filter = ('is_completed', 'created_at')
    search_fields = ('user__email', 'square_payment_id')
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Admin configuration for site-wide settings (singleton)."""
    list_display = ('__str__', 'default_credits')
    
    def has_add_permission(self, request):
        """Prevent creating additional instances - only one should exist."""
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting the settings instance."""
        return False
