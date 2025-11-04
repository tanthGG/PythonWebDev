from django.urls import path
from . import views

from .views import *


urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.aboutUs, name='about-page'),   # name must match template
    path('contact/', views.contact, name='contact-page'),
    path('booking/', views.booking, name='booking-page'),
    path('booking/walk-in/', views.admin_booking_create, name='admin-booking-create'),
    path('booking/success/<int:booking_id>/', views.booking_success, name='booking-success'),
    path('showcontact/', showContact, name='showcontact-page'),
    path('bookings/manage/', views.showBookings, name='booking-list-page'),
    path('staff/insights/', views.staff_insights, name='staff-insights'),
    path('register/', userRegist, name="register-page"),
    path('profile/', userProfile, name="profile-page"),
    path('editprofile/', editProfile, name="editprofile-page"),
    path('action/<int:cid>', actionPage, name="action-page"),
    path('programs/create/', addProgram, name="addprogram-page"),
    path('programs/<slug:code>/', views.program_detail, name="program-detail"),
    path('users/manage/', views.user_management, name='user-management-page'),
    path('products/<int:pk>/', views.product_detail, name='product-detail'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('staff/<int:staff_id>/feedback/', views.staff_feedback, name='staff-feedback'),

    path("ajax/user/detail/", views.UserDetailAjax.as_view(), name="ajax_user_detail"),
    path("ajax/user/create/", views.CreateUserAjax.as_view(), name="ajax_user_create"),
    path("ajax/user/update/", views.UpdateUserAjax.as_view(), name="ajax_user_update"),
    path("ajax/user/delete/", views.DeleteUserAjax.as_view(), name="ajax_user_delete"),
]
