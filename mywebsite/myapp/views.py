from django.shortcuts import render
from django.http import HttpResponse
from .models import *

from django.http import HttpResponse

def home(request):
    allproduct = Product.objects.all()
    context = {'pd': allproduct}
    return render(request, 'myapp/home.html', context)

def aboutUs(request):
    return render(request, 'myapp/aboutus.html')
