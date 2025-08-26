from django.urls import path

from .views import *

urlpatterns = [ 
    # localhost: 8000
    path('', home),
    #localhost: 8000/about
    path('about/', aboutUs, name="about-page"),
]