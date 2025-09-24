import json

from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import *
from django.contrib.auth import authenticate,login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator

from django.shortcuts import render
from django.views.generic import View, ListView
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Product

from django.http import HttpResponse

def home(request):
    allproduct = Product.objects.all()
    product_per_page = 3
    paginator = Paginator(allproduct, product_per_page)
    page = request.GET.get('page')
    allproduct = paginator.get_page(page)

    context = {'allproduct': allproduct}

    # 1 row 3 cols
    allrow = []
    row = []
    for i, p in enumerate(allproduct):
        if i % 3 == 0:
            if i != 0:
                allrow.append(row)
                row = []
            row.append(p)
        else:
            row.append(p)
    allrow.append(row)

    context['allrow'] = allrow

    return render(request, 'myapp/home.html', context)


def aboutUs(request):
    return render(request, 'myapp/aboutus.html')

def contact(request):

    context = {} # message to notify

    if request.method == 'POST':
        data = request.POST.copy()
        topic = data.get('topic')
        email = data.get('email')
        detail = data.get('detail')

        if (topic == '' or email == '' or detail == ''):
            context['message'] = 'Please fill in all contact informations'
            return render(request, 'myapp/contact.html', context)
        newRecord = contactList() #create object
        newRecord.topic = topic
        newRecord.email = email
        newRecord.detail = detail
        newRecord.save() # save data

        context['message'] = 'The message has been received'

    return render(request, 'myapp/contact.html', context)

def userLogin(request):
    context = {}
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Check if ?next= exists in the URL
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('home')  # fallback
        context['message'] = "Username or password is incorrect."
    return render(request, 'myapp/login.html', context)

@login_required(login_url='/login')
def showContact(request):
    allcontact = contactList.objects.all()
    # allcontact = contactList.objects.all().order_by('-id')  # reverse list (latest first)
    context = {'contact': allcontact}
    return render(request, 'myapp/showcontact.html', context)

def userRegist(request):
    context = {}

    if request.method == 'POST':
        data = request.POST.copy()
        firstname = data.get('firstname')
        lastname = data.get('lastname')
        username = data.get('username')
        email = data.get("email")
        password = data.get('password')
        repassword = data.get('repassword')

        try:
            # Check if username already exists
            User.objects.get(username=username)
            context['message'] = "Username duplicate"
        except:
            # Create new user
            newuser = User()
            newuser.username = username
            newuser.first_name = firstname
            newuser.last_name = lastname
            newuser.email = email

            if password == repassword:
                newuser.set_password(password)  # hash password
                newuser.save()

                # If you have a Profile model, create a profile for the new user
                try:
                    newprofile = Profile()
                    newprofile.user = User.objects.get(username=username)
                    newprofile.save()
                except:
                    pass  # skip if Profile model is not defined

                context['message'] = "Register complete."
            else:
                context['message'] = "Password or re-password is incorrect."

    return render(request, 'myapp/register.html', context)

def userProfile(request):
    context = {}
    userprofile = Profile.objects.get(user=request.user)
    context['profile'] = userprofile
    return render(request, 'myapp/profile.html', context)

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

def editProfile(request):
    context = {}

    if request.method == 'POST':
        data = request.POST.copy()
        firstname = data.get('firstname')
        lastname = data.get('lastname')
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        # Get the currently logged-in user
        current_user = User.objects.get(id=request.user.id)
        current_user.first_name = firstname
        current_user.last_name = lastname
        current_user.username = username
        current_user.email = email

        # Update password (hashed)
        current_user.set_password(password)
        current_user.save()

        try:
            # Re-authenticate after password change
            user = authenticate(username=current_user.username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home-page')
        except:
            context['message'] = "Edit profile fail"

    return render(request, 'myapp/editprofile.html', context)

def actionPage(request, cid):
    context = {}
    contact = contactList.objects.get(id=cid)
    context['contact'] = contact
    return render(request, 'myapp/action.html', context) 
        
from django.shortcuts import render, redirect
from .models import contactList, Action

def actionPage(request, cid):
    # cid = contactList ID
    context = {}
    contact = contactList.objects.get(id=cid)
    context['contact'] = contact

    try:
        action = Action.objects.get(contactList=contact)
        context['action'] = action
    except:
        pass

    if request.method == 'POST':
        data = request.POST.copy()
        actiondetail = data.get('actiondetail')

        # --- SAVE ---
        if 'save' in data:
            try:
                check = Action.objects.get(contactList=contact)
                check.actionDetail = actiondetail
                check.save()
                context['action'] = check
            except:
                new = Action()
                new.contactList = contact
                new.actionDetail = actiondetail
                new.save()
                context['action'] = new

        # --- DELETE ---
        elif 'delete' in data:
            try:
                contact.delete()
                return redirect('showcontact-page')
            except:
                pass

        # --- COMPLETE ---
        elif 'complete' in data:
            contact.complete = True
            contact.save()
            return redirect('showcontact-page')

    return render(request, 'myapp/action.html', context)

def addProduct(request):
    if request.method == 'POST':
        data = request.POST.copy()
        title = data.get('title')
        description = data.get('description')
        price = data.get('price')
        quantity = data.get('quantity')
        instock = data.get('instock')

        new = Product()
        new.title = title
        new.description = description
        new.price = float(price)
        new.quantity = int(quantity)

        if instock == 'instock':
            new.instock = True
        else:
            new.instock = False

        if 'picture' in request.FILES:
            file_image = request.FILES['picture']
            file_image_name = file_image.name.replace(' ', '_')  # delete space in file name
            # File system: from django.core.files.storage import FileSystemStorage
            fs = FileSystemStorage(location='media/product')
            filename = fs.save(file_image_name, file_image)
            upload_file_url = fs.url(filename)
            print('Picture url :', upload_file_url)
            new.picture = 'product' + upload_file_url[6:]

        if 'specfile' in request.FILES:
            file_specfile = request.FILES['specfile']
            file_specfile_name = file_specfile.name.replace(' ', '_')  # delete space in file name
            # FileSystemStorage: from django.core.files.storage import FileSystemStorage
            fs = FileSystemStorage(location='media/specfile')
            filename = fs.save(file_specfile_name, file_specfile)
            upload_file_url = fs.url(filename)
            print('Specfile url :', upload_file_url)
            new.specfile = 'specfile' + upload_file_url[6:]

        new.save()

    return render(request, 'myapp/addproduct.html')

def handler404(request, exception):
    return render(request, 'myapp/404errorPage.html')


@login_required(login_url='/login')
def user_management(request):
    users = User.objects.select_related('profile').order_by('username')

    initial_users = []
    for user in users:
        profile = getattr(user, 'profile', None)
        initial_users.append({
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'usertype': profile.usertype if profile else '',
            'point': profile.point if profile else 0,
        })

    initial_users_json = json.dumps(initial_users).replace('</', '<\\/')

    context = {
        'initial_users_json': initial_users_json,
        'current_user_id': request.user.id,
    }

    return render(request, 'myapp/user_management.html', context)

def _extract_data(request):
    if request.method == "POST" and request.POST:
        return request.POST
    return request.GET


def _parse_int(value, default=0):
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("Invalid quantity")


def _parse_bool(value, default=None):
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "yes", "on", "y", "t"}


def _get_profile(user):
    try:
        return user.profile
    except Profile.DoesNotExist:
        return None


def _serialize_user(user):
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


class ProductListView(ListView):
    model = Product
    template_name = "myapp/product_list.html"
    context_object_name = "product_list"
    paginate_by = 9

    def get_queryset(self):
        queryset = super().get_queryset().order_by("title")
        term = self.request.GET.get("search")
        if term:
            queryset = queryset.filter(
                Q(title__icontains=term) | Q(description__icontains=term)
            )
        return queryset


class UserDetailAjax(View):
    http_method_names = ["get"]

    def get(self, request):
        user_id = request.GET.get("id")
        if not user_id:
            return JsonResponse({"error": "Missing user id"}, status=400)

        user = get_object_or_404(User, pk=user_id)
        return JsonResponse({"user": _serialize_user(user)})


class CreateUserAjax(View):
    http_method_names = ["get", "post"]

    def _handle(self, request):
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
        if "usertype" in data and data.get("usertype"):
            profile.usertype = data.get("usertype")
        if "point" in data:
            try:
                profile.point = _parse_int(data.get("point"), default=profile.point)
            except ValueError as exc:
                return JsonResponse({"error": str(exc)}, status=400)
        profile.save()

        return JsonResponse({"user": _serialize_user(user)}, status=201)

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)


class UpdateUserAjax(View):
    http_method_names = ["get", "post"]

    def _handle(self, request):
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

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)


class DeleteUserAjax(View):
    http_method_names = ["get", "post", "delete"]

    def _handle(self, request):
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

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    def delete(self, request):
        return self._handle(request)
