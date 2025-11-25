from django.db import models
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Sum

# Create your models here.

class Product(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, \
                                null=True, blank=True)
    quantity = models.IntegerField(default=0, null=True, blank=True)
    instock = models.BooleanField(default=True)

    #file
    picture = models.ImageField(upload_to='product/', blank=True, null=True)  
    specfile = models.FileField(upload_to='specfile/', blank=True, null=True) 
    def __str__(self):
        return self.title

# myapp/models.py
class contactList(models.Model):
    topic = models.CharField(max_length=200)
    email = models.CharField(max_length=100)
    detail = models.TextField(null=True, blank=True)
    complete = models.BooleanField(default=False)

    def __str__(self):
        return self.topic

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    usertype = models.CharField(max_length=100, default='member')
    point = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username

class Action(models.Model):
    contactList = models.ForeignKey(contactList, on_delete=models.CASCADE)
    actionsDetail = models.TextField()

    def __str__(self):
        return self.contactList.topic

class Program(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    duration_minutes = models.PositiveIntegerField(default=60)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    itinerary = models.TextField(blank=True)
    schedule_details = models.TextField(blank=True)
    pricing_notes = models.TextField(blank=True)
    tour_includes = models.TextField(blank=True)
    tour_excludes = models.TextField(blank=True)
    tour_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_rate(self, participant: "ProgramRate.Participant", age_group: "ProgramRate.AgeGroup") -> Decimal:
        try:
            rate = self.rates.get(participant_type=participant, age_group=age_group)
        except ProgramRate.DoesNotExist as exc:
            raise ValidationError(
                f"No rate configured for program {self.code} ({participant}, {age_group})"
            ) from exc
        return rate.price

    def primary_image(self):
        return self.images.order_by("display_order", "id").first()


class ProgramRate(models.Model):
    class Participant(models.TextChoices):
        RIDER = "rider", "Rider"
        PASSENGER = "passenger", "Passenger"

    class AgeGroup(models.TextChoices):
        ADULT = "adult", "Adult"
        CHILD = "child", "Child"

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="rates")
    participant_type = models.CharField(max_length=20, choices=Participant.choices)
    age_group = models.CharField(max_length=20, choices=AgeGroup.choices)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        unique_together = ("program", "participant_type", "age_group")
        ordering = ["program__code", "participant_type", "age_group"]

    def __str__(self) -> str:
        return f"{self.program.code} - {self.participant_type} ({self.age_group})"


class ProgramImage(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="programs/")
    alt_text = models.CharField(max_length=150, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self) -> str:
        return f"{self.program.code} image #{self.pk}"


class Staff(models.Model):
    name = models.CharField(max_length=100)
    nickname = models.CharField(max_length=60, blank=True)
    role = models.CharField(max_length=120, blank=True)
    years_experience = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)
    likes = models.TextField(blank=True)
    dislikes = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="staff/", blank=True)
    active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self) -> str:
        return self.name

    def likes_total(self) -> int:
        if hasattr(self, "likes_count") and self.likes_count is not None:
            return int(self.likes_count)
        return self.feedback.filter(sentiment=StaffFeedback.Sentiment.LIKE).count()

    def dislikes_total(self) -> int:
        if hasattr(self, "dislikes_count") and self.dislikes_count is not None:
            return int(self.dislikes_count)
        return self.feedback.filter(sentiment=StaffFeedback.Sentiment.DISLIKE).count()

    def latest_feedback_time(self):
        if hasattr(self, "feedback_latest") and self.feedback_latest is not None:
            return self.feedback_latest
        latest = self.feedback.order_by("-updated_at").values_list("updated_at", flat=True).first()
        return latest


class StaffFeedback(models.Model):
    class Sentiment(models.TextChoices):
        LIKE = "like", "Like"
        DISLIKE = "dislike", "Dislike"
        NONE = "none", "No vote"

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="feedback")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="staff_feedback")
    sentiment = models.CharField(max_length=10, choices=Sentiment.choices, default=Sentiment.NONE)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("staff", "user")
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.user} → {self.staff} ({self.sentiment})"


class Addon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Booking(models.Model):
    class RideSlot(models.TextChoices):
        MORNING = "morning", "Morning"
        NOON = "noon", "Noon"
        AFTERNOON = "afternoon", "Afternoon"

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    ride_date = models.DateField()
    ride_time = models.CharField(max_length=10, choices=RideSlot.choices, blank=True)
    pickup_place = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["-created_at"]

    def update_total(self) -> None:
        items_total = self.items.aggregate(total=Sum("line_total"))["total"] or Decimal("0")
        addons_total = self.addons.aggregate(total=Sum("line_total"))["total"] or Decimal("0")
        total = items_total + addons_total
        Booking.objects.filter(pk=self.pk).update(total_amount=total)
        self.total_amount = total

    def __str__(self):
        return f"{self.full_name} – {self.ride_date}"


class BookingItem(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="items")
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="booking_items")
    participant_type = models.CharField(max_length=20, choices=ProgramRate.Participant.choices)
    age_group = models.CharField(max_length=20, choices=ProgramRate.AgeGroup.choices)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["booking_id", "id"]

    def save(self, *args, **kwargs):
        self.unit_price = self.program.get_rate(self.participant_type, self.age_group)
        self.line_total = self.unit_price * Decimal(self.quantity)
        super().save(*args, **kwargs)
        self.booking.update_total()

    def delete(self, *args, **kwargs):
        booking = self.booking
        super().delete(*args, **kwargs)
        booking.update_total()

    def __str__(self) -> str:
        return f"{self.program.code} x {self.quantity} ({self.get_participant_type_display()} {self.get_age_group_display()})"


class BookingAddon(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="addons")
    addon = models.ForeignKey(Addon, on_delete=models.PROTECT, related_name="booking_addons")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["booking_id", "id"]

    def save(self, *args, **kwargs):
        self.unit_price = self.addon.price
        self.line_total = self.unit_price * Decimal(self.quantity)
        super().save(*args, **kwargs)
        self.booking.update_total()

    def delete(self, *args, **kwargs):
        booking = self.booking
        super().delete(*args, **kwargs)
        booking.update_total()

    def __str__(self) -> str:
        return f"{self.addon.code} x {self.quantity}"


class Bike(models.Model):
    number = models.PositiveIntegerField(unique=True)
    nickname = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["number"]

    def __str__(self) -> str:
        label = f"ATV #{self.number}"
        if self.nickname:
            return f"{label} – {self.nickname}"
        return label


class BikeAssignment(models.Model):
    bike = models.ForeignKey(Bike, on_delete=models.CASCADE, related_name="assignments")
    date = models.DateField()
    note = models.CharField(max_length=200, blank=True)
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bike_assignments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("bike", "date")
        ordering = ["-date", "bike__number"]

    def __str__(self) -> str:
        return f"{self.bike} → {self.date.isoformat()}"
