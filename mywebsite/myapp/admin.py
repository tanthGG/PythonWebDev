from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import (
    Action,
    Addon,
    Booking,
    BookingAddon,
    BookingItem,
    Product,
    Program,
    ProgramImage,
    ProgramRate,
    contactList,
    Profile,
)


class ProgramRateInline(admin.TabularInline):
    model = ProgramRate
    extra = 0


class ProgramImageInline(admin.TabularInline):
    model = ProgramImage
    extra = 1


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "duration_minutes", "active")
    list_filter = ("active",)
    search_fields = ("code", "name")
    readonly_fields = ("primary_image_preview",)
    inlines = [ProgramRateInline, ProgramImageInline]

    def primary_image_preview(self, obj):
        image = obj.primary_image()
        if not image:
            return "—"
        return mark_safe(f'<img src="{image.image.url}" alt="{image.alt_text or obj.name}" style="max-width: 220px; border-radius: 12px;" />')
    primary_image_preview.short_description = "Primary image"


class BookingItemInline(admin.TabularInline):
    model = BookingItem
    extra = 0


class BookingAddonInline(admin.TabularInline):
    model = BookingAddon
    extra = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("full_name", "ride_date", "ride_time", "total_amount", "created_at")
    list_filter = ("ride_date", "ride_time")
    search_fields = ("full_name", "email", "phone")
    readonly_fields = ("total_amount", "created_at")
    inlines = [BookingItemInline, BookingAddonInline]


admin.site.register(Product)
admin.site.register(contactList)
admin.site.register(Profile)
admin.site.register(Action)
admin.site.register(Addon)
