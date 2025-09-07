from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import *
from django.contrib.auth import authenticate,login
from django.contrib.auth.models import User

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
            return redirect('home')
        context['message'] = "Username or password is incorrect."
    return render(request, 'myapp/login.html', context)

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


        
