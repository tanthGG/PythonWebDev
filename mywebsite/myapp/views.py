from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import *
from django.contrib.auth import authenticate,login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from django.core.files.storage import FileSystemStorage

from django.http import HttpResponse

def home(request):
    allproduct = Product.objects.all()
    context = {'pd': allproduct}
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


