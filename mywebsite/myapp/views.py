"""Views for the myapp application."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Tuple

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import ListView, View

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
    Profile,
    contactList,
)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _extract_data(request: HttpRequest) -> Dict[str, Any]:
    if request.method == "POST" and request.POST:
        return request.POST
    return request.GET


def _parse_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid integer value") from exc


def _parse_bool(value: Any, default: bool | None = None) -> bool | None:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "yes", "on", "y", "t"}


def _get_profile(user: User) -> Profile | None:
    try:
        return user.profile
    except Profile.DoesNotExist:
        return None


def _serialize_user(user: User) -> Dict[str, Any]:
    profile = _get_profile(user)
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "usertype": profile.usertype if profile else None,
        "point": profile.point if profile else None,
    }


# ---------------------------------------------------------------------------
# Basic pages
# ---------------------------------------------------------------------------

def home(request: HttpRequest) -> HttpResponse:
    programs = Program.objects.filter(active=True).prefetch_related("rates", "images")
    program_cards: List[Dict[str, Any]] = []

    for program in programs:
        rate_map = {
            (rate.participant_type, rate.age_group): rate.price
            for rate in program.rates.all()
        }
        starting_price = None
        if rate_map:
            starting_price = min(rate_map.values())

        program_cards.append(
            {
                "program": program,
                "starting_price": starting_price,
                "rider_adult": rate_map.get((ProgramRate.Participant.RIDER, ProgramRate.AgeGroup.ADULT)),
                "rider_child": rate_map.get((ProgramRate.Participant.RIDER, ProgramRate.AgeGroup.CHILD)),
                "passenger_adult": rate_map.get((ProgramRate.Participant.PASSENGER, ProgramRate.AgeGroup.ADULT)),
                "passenger_child": rate_map.get((ProgramRate.Participant.PASSENGER, ProgramRate.AgeGroup.CHILD)),
                "primary_image": program.primary_image(),
            }
        )

    context = {
        "program_cards": program_cards,
        "program_count": len(program_cards),
    }
    return render(request, "myapp/home.html", context)


def aboutUs(request: HttpRequest) -> HttpResponse:
    return render(request, "myapp/aboutus.html")


def contact(request: HttpRequest) -> HttpResponse:
    context: Dict[str, Any] = {}

    if request.method == "POST":
        data = request.POST.copy()
        topic = data.get("topic", "").strip()
        email = data.get("email", "").strip()
        detail = data.get("detail", "").strip()

        if not topic or not email or not detail:
            context["message"] = "Please fill in all contact informations"
        else:
            contactList.objects.create(topic=topic, email=email, detail=detail)
            context["message"] = "The message has been received"

    return render(request, "myapp/contact.html", context)


def _build_program_entries() -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    programs_qs = Program.objects.filter(active=True).prefetch_related("rates", "images")
    program_entries: List[Dict[str, Any]] = []
    program_lookup: Dict[int, Dict[str, Any]] = {}

    for program in programs_qs:
        rates_map = {
            (rate.participant_type, rate.age_group): rate.price
            for rate in program.rates.all()
        }
        rows: List[Dict[str, Any]] = []
        for participant in ProgramRate.Participant.values:
            participant_label = ProgramRate.Participant(participant).label
            for age_group in ProgramRate.AgeGroup.values:
                age_label = ProgramRate.AgeGroup(age_group).label
                field = f"{participant}_{age_group}_{program.id}"
                rows.append(
                    {
                        "participant": participant,
                        "participant_label": participant_label,
                        "age_group": age_group,
                        "age_label": age_label,
                        "field": field,
                        "price": rates_map.get((participant, age_group)),
                        "quantity": 0,
                    }
                )
        rider_rows = [row for row in rows if row["participant"] == ProgramRate.Participant.RIDER]
        passenger_rows = [row for row in rows if row["participant"] == ProgramRate.Participant.PASSENGER]
        entry = {
            "program": program,
            "rows": rows,
            "rider_rows": rider_rows,
            "passenger_rows": passenger_rows,
            "is_active": True,
            "primary_image": program.primary_image(),
        }
        program_entries.append(entry)
        program_lookup[program.id] = entry

    return program_entries, program_lookup


def _build_addon_entries() -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for addon in Addon.objects.filter(active=True).order_by("name"):
        entries.append(
            {
                "addon": addon,
                "field": f"addon_{addon.id}",
                "quantity": 0,
            }
        )
    return entries


def _process_booking_submission(
    request: HttpRequest,
    program_entries: List[Dict[str, Any]],
    program_lookup: Dict[int, Dict[str, Any]],
    addon_entries: List[Dict[str, Any]],
    *,
    use_program_selector: bool = False,
) -> Tuple[
    Booking | None,
    Dict[str, Any],
    List[str],
    Dict[str, int],
    List[int],
    Dict[str, int],
]:
    data = request.POST.copy()
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    ride_date_raw = data.get("ride_date", "").strip()
    ride_time = data.get("ride_time", "").strip()
    pickup_place = data.get("pickup_place", "").strip()
    notes = data.get("notes", "").strip()

    form_values: Dict[str, Any] = {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "ride_date": ride_date_raw,
        "ride_time": ride_time,
        "pickup_place": pickup_place,
        "notes": notes,
    }
    errors: List[str] = []
    quantity_values: Dict[str, int] = {}
    active_program_ids: List[int] = []

    if not full_name or not email or not phone or not ride_date_raw:
        errors.append("Full name, email, phone, and ride date are required.")

    ride_date = None
    if ride_date_raw:
        try:
            ride_date = datetime.strptime(ride_date_raw, "%Y-%m-%d").date()
        except ValueError:
            errors.append("Ride date must be in YYYY-MM-DD format.")

    if ride_time and ride_time not in dict(Booking.RideSlot.choices):
        errors.append("Please select a valid ride time slot.")

    items_payload: List[Dict[str, Any]] = []
    addon_quantities: Dict[str, int] = {}
    addon_payload: List[Dict[str, Any]] = []

    if use_program_selector:
        raw_program_ids = data.getlist("active_program")
        seen_ids: set[int] = set()
        for raw_id in raw_program_ids:
            try:
                program_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if program_id in program_lookup and program_id not in seen_ids:
                active_program_ids.append(program_id)
                seen_ids.add(program_id)
    else:
        active_program_ids = [entry["program"].id for entry in program_entries]

    entries_to_process = [
        program_lookup[program_id]
        for program_id in active_program_ids
        if program_id in program_lookup
    ]

    if use_program_selector and not active_program_ids:
        errors.append("Please select at least one program.")

    for entry in entries_to_process:
        program = entry["program"]
        for row in entry["rows"]:
            field = row["field"]
            participant = row["participant"]
            age_group = row["age_group"]
            raw_value = data.get(field, "").strip()
            if raw_value == "":
                quantity_values[field] = 0
                continue
            try:
                quantity = int(raw_value)
            except ValueError:
                errors.append(
                    f"Quantity for {program.code} ({participant} {age_group}) must be a number."
                )
                continue
            if quantity < 0:
                errors.append(
                    f"Quantity for {program.code} ({participant} {age_group}) cannot be negative."
                )
                continue
            quantity_values[field] = quantity
            if quantity > 0:
                items_payload.append(
                    {
                        "program": program,
                        "participant": participant,
                        "age_group": age_group,
                        "quantity": quantity,
                    }
                )

    if not items_payload and not errors:
        errors.append("Please select at least one rider or passenger.")

    for entry in addon_entries:
        field = entry["field"]
        addon = entry["addon"]
        raw_value = data.get(field, "").strip()
        if raw_value == "":
            addon_quantities[field] = 0
            continue
        try:
            quantity = int(raw_value)
        except ValueError:
            errors.append(f"Quantity for {addon.name} must be a number.")
            continue
        if quantity < 0:
            errors.append(f"Quantity for {addon.name} cannot be negative.")
            continue
        addon_quantities[field] = quantity
        if quantity > 0:
            addon_payload.append({"addon": addon, "quantity": quantity})

    if not errors and ride_date is not None:
        booking = Booking.objects.create(
            full_name=full_name,
            email=email,
            phone=phone,
            ride_date=ride_date,
            ride_time=ride_time,
            pickup_place=pickup_place,
            notes=notes,
        )
        for item in items_payload:
            BookingItem.objects.create(
                booking=booking,
                program=item["program"],
                participant_type=item["participant"],
                age_group=item["age_group"],
                quantity=item["quantity"],
                unit_price=Decimal("0"),
                line_total=Decimal("0"),
            )
        for addon in addon_payload:
            BookingAddon.objects.create(
                booking=booking,
                addon=addon["addon"],
                quantity=addon["quantity"],
                unit_price=Decimal("0"),
                line_total=Decimal("0"),
            )
        booking.refresh_from_db()
        return (
            booking,
            form_values,
            errors,
            quantity_values,
            active_program_ids,
            addon_quantities,
        )

    return None, form_values, errors, quantity_values, active_program_ids, addon_quantities


def booking(request: HttpRequest) -> HttpResponse:
    program_entries, program_lookup = _build_program_entries()
    addon_entries = _build_addon_entries()
    form_values: Dict[str, Any] = {}
    quantity_values: Dict[str, int] = {}
    errors: List[str] = []
    active_program_ids: List[int] = []
    addon_quantities: Dict[str, int] = {}

    if request.method == "POST":
        (
            booking_obj,
            form_values,
            errors,
            quantity_values,
            active_program_ids,
            addon_quantities,
        ) = _process_booking_submission(
            request,
            program_entries,
            program_lookup,
            addon_entries,
            use_program_selector=True,
        )
        if booking_obj is not None:
            return redirect("booking-success", booking_id=booking_obj.pk)

    for field in [
        "full_name",
        "email",
        "phone",
        "ride_date",
        "ride_time",
        "pickup_place",
        "notes",
    ]:
        form_values.setdefault(field, "")

    for entry in program_entries:
        for row in entry["rows"]:
            quantity = quantity_values.setdefault(row["field"], 0)
            row["quantity"] = quantity
        entry["is_active"] = entry["program"].id in active_program_ids

    for entry in addon_entries:
        entry["quantity"] = addon_quantities.get(entry["field"], 0)

    context = {
        "program_entries": program_entries,
        "addon_entries": addon_entries,
        "ride_slots": Booking.RideSlot.choices,
        "form_values": form_values,
        "errors": errors,
        "admin_booking_mode": False,
        "active_program_ids": active_program_ids,
    }

    return render(request, "myapp/booking.html", context)


@login_required(login_url="/login")
def admin_booking_create(request: HttpRequest) -> HttpResponse:
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Forbidden", status=403)

    program_entries, program_lookup = _build_program_entries()
    addon_entries = _build_addon_entries()
    form_values: Dict[str, Any] = {}
    quantity_values: Dict[str, int] = {}
    errors: List[str] = []
    success_booking: Booking | None = None
    active_program_ids: List[int] = []
    addon_quantities: Dict[str, int] = {}

    if request.method == "POST":
        (
            booking_obj,
            form_values,
            errors,
            quantity_values,
            active_program_ids,
            addon_quantities,
        ) = _process_booking_submission(
            request,
            program_entries,
            program_lookup,
            addon_entries,
            use_program_selector=True,
        )
        if booking_obj is not None:
            success_booking = booking_obj
            form_values = {}
            quantity_values = {}
            active_program_ids = []
            addon_quantities = {}

    for field in [
        "full_name",
        "email",
        "phone",
        "ride_date",
        "ride_time",
        "pickup_place",
        "notes",
    ]:
        form_values.setdefault(field, "")

    if not form_values["ride_date"]:
        form_values["ride_date"] = timezone.localdate().isoformat()
    if not form_values["pickup_place"]:
        form_values["pickup_place"] = "None"

    for entry in program_entries:
        for row in entry["rows"]:
            quantity = quantity_values.setdefault(row["field"], 0)
            row["quantity"] = quantity
        entry["is_active"] = entry["program"].id in active_program_ids

    for entry in addon_entries:
        entry["quantity"] = addon_quantities.get(entry["field"], 0)

    context = {
        "program_entries": program_entries,
        "addon_entries": addon_entries,
        "ride_slots": Booking.RideSlot.choices,
        "form_values": form_values,
        "errors": errors,
        "success_booking": success_booking,
        "admin_booking_mode": True,
        "active_program_ids": active_program_ids,
    }

    return render(request, "myapp/booking.html", context)


def userLogin(request: HttpRequest) -> HttpResponse:
    context: Dict[str, Any] = {}

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next")
            return redirect(next_url or "home")
        context["message"] = "Username or password is incorrect."

    return render(request, "myapp/login.html", context)


@login_required(login_url="/login")
def showContact(request: HttpRequest) -> HttpResponse:
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Forbidden", status=403)

    contacts = contactList.objects.all()
    return render(request, "myapp/showcontact.html", {"contact": contacts})


@login_required(login_url="/login")
def showBookings(request: HttpRequest) -> HttpResponse:
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Forbidden", status=403)

    bookings_qs = (
        Booking.objects.prefetch_related("items__program", "addons__addon")
        .order_by("-created_at")
    )

    program_value = request.GET.get("program", "").strip()
    date_value = request.GET.get("ride_date", "").strip()

    if program_value:
        try:
            program_id = int(program_value)
        except (TypeError, ValueError):
            program_value = ""
        else:
            bookings_qs = bookings_qs.filter(items__program_id=program_id).distinct()

    if date_value:
        try:
            ride_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        except ValueError:
            date_value = ""
        else:
            bookings_qs = bookings_qs.filter(ride_date=ride_date)

    total_results = bookings_qs.count()
    aggregates = bookings_qs.aggregate(
        total_revenue=Sum("total_amount"),
        booking_count=Count("id"),
    )
    total_revenue = aggregates["total_revenue"] or Decimal("0")
    booking_count = aggregates["booking_count"] or 0
    average_revenue = total_revenue / booking_count if booking_count else Decimal("0")
    upcoming_count = bookings_qs.filter(ride_date__gte=timezone.localdate()).count()

    paginator = Paginator(bookings_qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    preserved_params = request.GET.copy()
    if "page" in preserved_params:
        preserved_params.pop("page")
    filter_query = preserved_params.urlencode()

    context = {
        "bookings": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "total_results": total_results,
        "total_revenue": total_revenue,
        "average_revenue": average_revenue,
        "upcoming_count": upcoming_count,
        "programs": Program.objects.filter(active=True).order_by("name"),
        "selected_program": program_value,
        "selected_date": date_value,
        "filter_query": filter_query,
        "page_range": paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1),
    }

    return render(request, "myapp/booking_list.html", context)


def booking_success(request: HttpRequest, booking_id: int) -> HttpResponse:
    booking = get_object_or_404(
        Booking.objects.prefetch_related("items__program", "addons__addon"), pk=booking_id
    )
    return render(request, "myapp/booking_success.html", {"booking": booking})


def userRegist(request: HttpRequest) -> HttpResponse:
    context: Dict[str, Any] = {}

    if request.method == "POST":
        data = request.POST.copy()
        firstname = data.get("firstname", "").strip()
        lastname = data.get("lastname", "").strip()
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password")
        repassword = data.get("repassword")

        if not username:
            context["message"] = "Username is required."
        elif User.objects.filter(username=username).exists():
            context["message"] = "Username duplicate"
        elif password != repassword:
            context["message"] = "Password or re-password is incorrect."
        else:
            new_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=firstname,
                last_name=lastname,
            )
            Profile.objects.get_or_create(user=new_user)
            context["message"] = "Register complete."

    return render(request, "myapp/register.html", context)


@login_required(login_url="/login")
def userProfile(request: HttpRequest) -> HttpResponse:
    profile = get_object_or_404(Profile, user=request.user)
    return render(request, "myapp/profile.html", {"profile": profile})


@login_required(login_url="/login")
def editProfile(request: HttpRequest) -> HttpResponse:
    profile = get_object_or_404(Profile, user=request.user)
    context: Dict[str, Any] = {"profile": profile}

    if request.method == "POST":
        data = request.POST.copy()
        firstname = data.get("firstname", "").strip()
        lastname = data.get("lastname", "").strip()
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password")

        user = request.user

        if username and username != user.username and User.objects.filter(username=username).exists():
            context["message"] = "Username already taken."
        else:
            user.first_name = firstname
            user.last_name = lastname
            if username:
                user.username = username
            user.email = email

            if password:
                user.set_password(password)

            user.save()

            if password:
                refreshed = authenticate(username=user.username, password=password)
                if refreshed is not None:
                    login(request, refreshed)

            context["message"] = "Profile updated successfully."
            context["profile"] = get_object_or_404(Profile, user=user)

    return render(request, "myapp/editprofile.html", context)


@login_required(login_url="/login")
def actionPage(request: HttpRequest, cid: int) -> HttpResponse:
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Forbidden", status=403)

    contact = get_object_or_404(contactList, id=cid)
    context: Dict[str, Any] = {"contact": contact}

    try:
        action = Action.objects.get(contactList=contact)
        context["action"] = action
        # Provide legacy attribute for templates expecting actionDetail
        if not hasattr(action, "actionDetail"):
            action.actionDetail = action.actionsDetail  # type: ignore[attr-defined]
    except Action.DoesNotExist:
        action = None

    if request.method == "POST":
        data = request.POST.copy()
        action_detail = data.get("actiondetail", "").strip()

        if "save" in data:
            action_obj, _ = Action.objects.get_or_create(contactList=contact)
            action_obj.actionsDetail = action_detail
            action_obj.save()
            context["action"] = action_obj
            if not hasattr(action_obj, "actionDetail"):
                action_obj.actionDetail = action_obj.actionsDetail  # type: ignore[attr-defined]
        elif "delete" in data:
            contact.delete()
            return redirect("showcontact-page")
        elif "complete" in data:
            contact.complete = True
            contact.save()
            return redirect("showcontact-page")

    return render(request, "myapp/action.html", context)


@login_required(login_url="/login")
def addProgram(request: HttpRequest) -> HttpResponse:
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Forbidden", status=403)

    rate_fields = [
        {
            "field": f"rate_{ProgramRate.Participant.RIDER}_{ProgramRate.AgeGroup.ADULT}",
            "label": "Rider – Adult",
            "participant": ProgramRate.Participant.RIDER,
            "age": ProgramRate.AgeGroup.ADULT,
        },
        {
            "field": f"rate_{ProgramRate.Participant.RIDER}_{ProgramRate.AgeGroup.CHILD}",
            "label": "Rider – Child",
            "participant": ProgramRate.Participant.RIDER,
            "age": ProgramRate.AgeGroup.CHILD,
        },
        {
            "field": f"rate_{ProgramRate.Participant.PASSENGER}_{ProgramRate.AgeGroup.ADULT}",
            "label": "Passenger – Adult",
            "participant": ProgramRate.Participant.PASSENGER,
            "age": ProgramRate.AgeGroup.ADULT,
        },
        {
            "field": f"rate_{ProgramRate.Participant.PASSENGER}_{ProgramRate.AgeGroup.CHILD}",
            "label": "Passenger – Child",
            "participant": ProgramRate.Participant.PASSENGER,
            "age": ProgramRate.AgeGroup.CHILD,
        },
    ]

    form_values: Dict[str, Any] = {
        "code": "",
        "name": "",
        "duration_minutes": "60",
        "description": "",
        "active": True,
    }
    rate_values: Dict[str, str] = {field["field"]: "" for field in rate_fields}
    for field in rate_fields:
        field["value"] = ""
    errors: List[str] = []
    success = False

    if request.method == "POST":
        data = request.POST.copy()
        code = data.get("code", "").strip()
        name = data.get("name", "").strip()
        duration_raw = data.get("duration_minutes", "60").strip()
        description = data.get("description", "").strip()
        active = _parse_bool(data.get("active"), default=True)

        form_values.update(
            {
                "code": code,
                "name": name,
                "duration_minutes": duration_raw,
                "description": description,
                "active": active,
            }
        )

        if not code:
            errors.append("Program code is required.")
        elif Program.objects.filter(code=code).exists():
            errors.append("Program code must be unique.")

        if not name:
            errors.append("Program name is required.")

        try:
            duration_minutes = int(duration_raw)
            if duration_minutes <= 0:
                raise ValueError
        except (TypeError, ValueError):
            errors.append("Duration must be a positive whole number (minutes).")
            duration_minutes = 60

        parsed_rates: List[Dict[str, Any]] = []
        for field in rate_fields:
            value = data.get(field["field"], "").strip()
            rate_values[field["field"]] = value
            field["value"] = value
            if value == "":
                continue
            try:
                price = Decimal(value)
                if price < 0:
                    raise ValueError
            except (ArithmeticError, ValueError):
                errors.append(f"Price for {field['label']} must be a non-negative number.")
                continue
            parsed_rates.append(
                {
                    "participant": field["participant"],
                    "age": field["age"],
                    "price": price,
                }
            )

        image_files = request.FILES.getlist("images")
        if not image_files:
            errors.append("Please upload at least one program image.")

        if not errors:
            program = Program.objects.create(
                code=code,
                name=name,
                duration_minutes=duration_minutes,
                description=description,
                active=bool(active),
            )

            for rate in parsed_rates:
                ProgramRate.objects.update_or_create(
                    program=program,
                    participant_type=rate["participant"],
                    age_group=rate["age"],
                    defaults={"price": rate["price"]},
                )

            for index, image in enumerate(image_files):
                ProgramImage.objects.create(
                    program=program,
                    image=image,
                    alt_text=description[:140] or name,
                    display_order=index,
                )

            success = True
            form_values.update({
                "code": "",
                "name": "",
                "duration_minutes": "60",
                "description": "",
                "active": True,
            })
            rate_values = {field["field"]: "" for field in rate_fields}
            for field in rate_fields:
                field["value"] = ""

    context = {
        "form_values": form_values,
        "rate_fields": rate_fields,
        "errors": errors,
        "success": success,
    }

    return render(request, "myapp/addprogram.html", context)


def handler404(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(request, "myapp/404errorPage.html")


@login_required(login_url="/login")
def user_management(request: HttpRequest) -> HttpResponse:
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Forbidden", status=403)

    users = User.objects.select_related("profile").order_by("username")
    initial_users = []
    for user in users:
        profile = getattr(user, "profile", None)
        initial_users.append(
            {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "usertype": profile.usertype if profile else "",
                "point": profile.point if profile else 0,
            }
        )

    initial_users_json = json.dumps(initial_users).replace("</", "<\\/")

    context = {
        "initial_users_json": initial_users_json,
        "current_user_id": request.user.id,
    }
    return render(request, "myapp/user_management.html", context)


def product_detail(request: HttpRequest, pk: int) -> HttpResponse:
    product = get_object_or_404(Product, pk=pk)
    return render(request, "myapp/product_detail.html", {"product": product})


# ---------------------------------------------------------------------------
# AJAX views for user CRUD
# ---------------------------------------------------------------------------

class ProductListView(ListView):
    model = Product
    template_name = "myapp/product_list.html"
    context_object_name = "product_list"
    paginate_by = 9

    def get_queryset(self):  # type: ignore[override]
        queryset = super().get_queryset().order_by("title")
        term = self.request.GET.get("search")
        if term:
            queryset = queryset.filter(Q(title__icontains=term) | Q(description__icontains=term))
        return queryset


class UserDetailAjax(View):
    http_method_names = ["get"]

    def get(self, request: HttpRequest) -> JsonResponse:  # type: ignore[override]
        if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({"error": "Forbidden"}, status=403)

        user_id = request.GET.get("id")
        if not user_id:
            return JsonResponse({"error": "Missing user id"}, status=400)

        user = get_object_or_404(User, pk=user_id)
        return JsonResponse({"user": _serialize_user(user)})


class CreateUserAjax(View):
    http_method_names = ["get", "post"]

    def _handle(self, request: HttpRequest) -> JsonResponse:
        if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({"error": "Forbidden"}, status=403)

        data = _extract_data(request)

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return JsonResponse({"error": "Username and password are required"}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username already exists"}, status=400)

        user = User(
            username=username,
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            email=data.get("email", ""),
        )
        user.set_password(password)

        is_active = _parse_bool(data.get("is_active"), default=True)
        if is_active is not None:
            user.is_active = is_active

        is_staff = _parse_bool(data.get("is_staff"), default=user.is_staff)
        if is_staff is not None:
            user.is_staff = is_staff

        user.save()

        profile = _get_profile(user) or Profile(user=user)
        if data.get("usertype"):
            profile.usertype = data.get("usertype")
        if "point" in data:
            try:
                profile.point = _parse_int(data.get("point"), default=profile.point)
            except ValueError as exc:
                return JsonResponse({"error": str(exc)}, status=400)
        profile.save()

        return JsonResponse({"user": _serialize_user(user)}, status=201)

    def get(self, request: HttpRequest) -> JsonResponse:  # type: ignore[override]
        return self._handle(request)

    def post(self, request: HttpRequest) -> JsonResponse:  # type: ignore[override]
        return self._handle(request)


class UpdateUserAjax(View):
    http_method_names = ["get", "post"]

    def _handle(self, request: HttpRequest) -> JsonResponse:
        if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({"error": "Forbidden"}, status=403)

        data = _extract_data(request)
        user_id = data.get("id")
        if not user_id:
            return JsonResponse({"error": "Missing user id"}, status=400)

        user = get_object_or_404(User, pk=user_id)

        if "username" in data and data.get("username") != user.username:
            new_username = data.get("username")
            if not new_username:
                return JsonResponse({"error": "Username cannot be blank"}, status=400)
            if User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
                return JsonResponse({"error": "Username already exists"}, status=400)
            user.username = new_username

        if "first_name" in data:
            user.first_name = data.get("first_name", "")
        if "last_name" in data:
            user.last_name = data.get("last_name", "")
        if "email" in data:
            user.email = data.get("email", "")

        if data.get("password"):
            user.set_password(data.get("password"))

        if "is_active" in data:
            is_active = _parse_bool(data.get("is_active"), default=user.is_active)
            if is_active is not None:
                user.is_active = is_active

        if "is_staff" in data:
            is_staff = _parse_bool(data.get("is_staff"), default=user.is_staff)
            if is_staff is not None:
                user.is_staff = is_staff

        user.save()

        profile = _get_profile(user) or Profile(user=user)
        if "usertype" in data:
            value = data.get("usertype")
            if value:
                profile.usertype = value
        if "point" in data:
            try:
                profile.point = _parse_int(data.get("point"), default=profile.point)
            except ValueError as exc:
                return JsonResponse({"error": str(exc)}, status=400)
        profile.save()

        return JsonResponse({"user": _serialize_user(user)})

    def get(self, request: HttpRequest) -> JsonResponse:  # type: ignore[override]
        return self._handle(request)

    def post(self, request: HttpRequest) -> JsonResponse:  # type: ignore[override]
        return self._handle(request)


class DeleteUserAjax(View):
    http_method_names = ["get", "post", "delete"]

    def _handle(self, request: HttpRequest) -> JsonResponse:
        if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({"error": "Forbidden"}, status=403)

        data = _extract_data(request)
        user_id = data.get("id")
        if not user_id:
            return JsonResponse({"error": "Missing user id"}, status=400)

        user = get_object_or_404(User, pk=user_id)

        if user.is_superuser:
            return JsonResponse({"error": "Cannot delete a superuser"}, status=403)

        if request.user.is_authenticated and request.user.pk == user.pk:
            return JsonResponse({"error": "Users cannot delete themselves"}, status=403)

        user.delete()
        return JsonResponse({"deleted": True})

    def get(self, request: HttpRequest) -> JsonResponse:  # type: ignore[override]
        return self._handle(request)

    def post(self, request: HttpRequest) -> JsonResponse:  # type: ignore[override]
        return self._handle(request)

    def delete(self, request: HttpRequest) -> JsonResponse:  # type: ignore[override]
        return self._handle(request)
