from django.contrib import admin
from .models import Product, Category, ProductInventory


class ProductInventoryInline(admin.TabularInline):
    """Hiển thị tồn kho ngay trong trang sản phẩm"""
    model = ProductInventory
    extra = 1
    fields = ('size', 'stock_quantity', 'reserved_quantity', 'sold_quantity', 'available_quantity')
    readonly_fields = ('available_quantity',)
    
    def available_quantity(self, obj):
        return obj.available_quantity if obj.pk else 0
    available_quantity.short_description = 'Có thể bán'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    exclude = ('discount_percent',)
    inlines = [ProductInventoryInline]
    list_display = ('name', 'old_price', 'new_price', 'get_total_stock', 'sold_number')
    
    def get_total_stock(self, obj):
        return obj.get_total_stock()
    get_total_stock.short_description = 'Tồn kho'


@admin.register(ProductInventory)
class ProductInventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'stock_quantity', 'reserved_quantity', 'sold_quantity', 'available_quantity', 'last_updated')
    list_filter = ('size', 'product')
    search_fields = ('product__name',)
    readonly_fields = ('available_quantity', 'last_updated')


admin.site.register(Category)

