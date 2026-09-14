from django.contrib import admin

from .models import ItemVenda, Venda


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 0
    autocomplete_fields = ('produto',)


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome_cliente', 'data_venda', 'status',
                    'forma_pagamento', 'total', 'estoque_baixado')
    list_filter = ('status', 'forma_pagamento', 'data_venda')
    search_fields = ('id', 'cliente__nome')
    readonly_fields = ('subtotal', 'total', 'estoque_baixado')
    inlines = [ItemVendaInline]
    date_hierarchy = 'data_venda'
