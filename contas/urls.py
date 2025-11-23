from django.urls import path
from . import views

urlpatterns = [
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('clientes/', views.clientes_view, name='clientes'),
    path('relatorios/', views.relatorios, name='relatorios'),
    path('estoque/', views.estoque_view, name='estoque'),
    path('estoque/entrada/', views.entrada_estoque_geral_view, name='entrada_estoque'),
    path('estoque/novo/', views.novo_produto_view, name='novo_produto'),
    
]
