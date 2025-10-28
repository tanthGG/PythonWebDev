from django.contrib import admin

from .models import Action, Booking, BookingItem, Product, Program, ProgramRate, contactList, Profile


class ProgramRateInline(admin.TabularInline):
    model = ProgramRate
    extra = 0


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "duration_minutes", "active")
    list_filter = ("active",)
    search_fields = ("code", "name")
    inlines = [ProgramRateInline]


class BookingItemInline(admin.TabularInline):
    model = BookingItem
    extra = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("full_name", "ride_date", "ride_time", "total_amount", "created_at")
    list_filter = ("ride_date", "ride_time")
    search_fields = ("full_name", "email", "phone")
    readonly_fields = ("total_amount", "created_at")
    inlines = [BookingItemInline]


admin.site.register(Product)
admin.site.register(contactList)
admin.site.register(Profile)
admin.site.register(Action)
