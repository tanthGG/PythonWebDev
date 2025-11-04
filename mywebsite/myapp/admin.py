from django.contrib import admin
from django.utils.safestring import mark_safe
from django.db.models import Count, Max, Q

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
    Staff,
    StaffFeedback,
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
    fieldsets = (
        (
            "Program",
            {
                "fields": (
                    "code",
                    "name",
                    "duration_minutes",
                    "description",
                    "active",
                    "primary_image_preview",
                )
            },
        ),
        (
            "Details",
            {
                "fields": (
                    "itinerary",
                    "schedule_details",
                    "tour_includes",
                    "tour_excludes",
                    "tour_notes",
                    "pricing_notes",
                )
            },
        ),
    )

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


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "likes_received", "dislikes_received", "active", "latest_feedback_recorded")
    list_filter = ("active",)
    search_fields = ("name", "nickname", "role")
    readonly_fields = ("likes_received", "dislikes_received", "latest_feedback_recorded")
    ordering = ("display_order", "name")
    fieldsets = (
        (
            "Profile",
            {
                "fields": (
                    "name",
                    "nickname",
                    "role",
                    "years_experience",
                    "bio",
                    "likes",
                    "dislikes",
                    "comment",
                    "avatar",
                    "active",
                    "display_order",
                )
            },
        ),
        (
            "Feedback summary",
            {
                "fields": (
                    "likes_received",
                    "dislikes_received",
                    "latest_feedback_recorded",
                )
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            likes_count=Count("feedback", filter=Q(feedback__sentiment=StaffFeedback.Sentiment.LIKE)),
            dislikes_count=Count("feedback", filter=Q(feedback__sentiment=StaffFeedback.Sentiment.DISLIKE)),
            feedback_latest=Max("feedback__updated_at"),
        )

    def likes_received(self, obj):
        return obj.likes_total()
    likes_received.short_description = "Likes"
    likes_received.admin_order_field = "likes_count"

    def dislikes_received(self, obj):
        return obj.dislikes_total()
    dislikes_received.short_description = "Dislikes"
    dislikes_received.admin_order_field = "dislikes_count"

    def latest_feedback_recorded(self, obj):
        return obj.latest_feedback_time()
    latest_feedback_recorded.short_description = "Latest feedback"
    latest_feedback_recorded.admin_order_field = "feedback_latest"


@admin.register(StaffFeedback)
class StaffFeedbackAdmin(admin.ModelAdmin):
    list_display = ("staff", "user", "sentiment", "comment_preview", "created_at")
    list_filter = ("sentiment", "created_at")
    search_fields = ["staff__name", "user__username", "comment"]
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "staff",
                    "user",
                    "sentiment",
                    "comment",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    def comment_preview(self, obj):
        if not obj.comment:
            return "—"
        text = obj.comment.strip()
        return text if len(text) <= 60 else f"{text[:57]}..."
    comment_preview.short_description = "Comment"
