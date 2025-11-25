
from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_clientes, name='lista_clientes'),
    path('novo/', views.novo_cliente, name='novo_cliente'),
    path('<int:pk>/', views.ver_cliente, name='ver_cliente'),
    path('<int:pk>/editar/', views.editar_cliente, name='editar_cliente'),
    path('<int:pk>/excluir/', views.excluir_cliente, name='excluir_cliente'),
    path('exportar/', views.exportar_clientes_csv, name='exportar_clientes'),
]