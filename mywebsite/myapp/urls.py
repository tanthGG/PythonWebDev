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
    path('users/manage/', views.user_management, name='user-management-page'),
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("ajax/user/detail/", views.UserDetailAjax.as_view(), name="ajax_user_detail"),
    path("ajax/user/create/", views.CreateUserAjax.as_view(), name="ajax_user_create"),
    path("ajax/user/update/", views.UpdateUserAjax.as_view(), name="ajax_user_update"),
    path("ajax/user/delete/", views.DeleteUserAjax.as_view(), name="ajax_user_delete"),
]
