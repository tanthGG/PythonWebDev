from django.shortcuts import render

from django.http import HttpResponse

def home(request):
    return render(request, 'myapp/home.html')

def aboutUs(request):
    return render(request, 'myapp/aboutus.html')
