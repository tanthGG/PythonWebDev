from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import *
from django.contrib.auth import authenticate,login

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