# em contas/urls.py (O ARQUIVO NOVO)
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Quando alguém visitar /cadastro/, chame a função cadastro_view
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]