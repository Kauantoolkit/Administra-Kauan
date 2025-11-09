from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('clientes/', views.clientes_view, name='clientes'),
]