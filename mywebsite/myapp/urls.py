from django.urls import path
from . import views

from .views import *


urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.aboutUs, name='about-page'),   # name must match template
    path('contact/', views.contact, name='contact-page'),
    path('showcontact/', showContact, name='showcontact-page'),
    path('register/', userRegist, name="register-page"),
    path('profile/', userProfile, name="profile-page"),
    path('editprofile/', editProfile, name="editprofile-page"),
    path('action/<int:cid>', actionPage, name="action-page"),
    path('addproduct/', addProduct, name="addproduct-page"),
]