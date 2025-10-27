"""Views for the myapp application."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, View

from .models import Action, Product, Profile, contactList


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
    all_products = Product.objects.all()
    paginator = Paginator(all_products, 3)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    rows: List[List[Product]] = []
    current_row: List[Product] = []
    for index, product in enumerate(page_obj):
        if index % 3 == 0 and current_row:
            rows.append(current_row)
            current_row = []
        current_row.append(product)
    if current_row:
        rows.append(current_row)

    context = {
        "allproduct": page_obj,
        "allrow": rows,
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
    contacts = contactList.objects.all()
    return render(request, "myapp/showcontact.html", {"contact": contacts})


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


def addProduct(request: HttpRequest) -> HttpResponse:
    context: Dict[str, Any] = {}

    if request.method == "POST":
        data = request.POST.copy()
        title = data.get("title")
        description = data.get("description")
        price = data.get("price")
        quantity = data.get("quantity")
        instock = data.get("instock")

        product = Product(
            title=title,
            description=description,
            price=float(price) if price else None,
            quantity=int(quantity) if quantity else 0,
            instock=_parse_bool(instock, default=False) or False,
        )

        if "picture" in request.FILES:
            picture = request.FILES["picture"]
            storage = FileSystemStorage(location="media/product")
            filename = storage.save(picture.name.replace(" ", "_"), picture)
            product.picture = f"product/{filename}"

        if "specfile" in request.FILES:
            specfile = request.FILES["specfile"]
            storage = FileSystemStorage(location="media/specfile")
            filename = storage.save(specfile.name.replace(" ", "_"), specfile)
            product.specfile = f"specfile/{filename}"

        product.save()
        context["success"] = True

    return render(request, "myapp/addproduct.html", context)


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
        user_id = request.GET.get("id")
        if not user_id:
            return JsonResponse({"error": "Missing user id"}, status=400)

        user = get_object_or_404(User, pk=user_id)
        return JsonResponse({"user": _serialize_user(user)})


class CreateUserAjax(View):
    http_method_names = ["get", "post"]

    def _handle(self, request: HttpRequest) -> JsonResponse:
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
