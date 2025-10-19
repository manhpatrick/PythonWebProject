from django.contrib import admin
from .models import Coupon, Order, OrderItem
# Register your models here.
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'complete', 'cart_items', 'cart_total', 'coupon', 'discount', 'date_ordered')
    list_filter = ('complete', 'payment_method', 'date_ordered')
    search_fields = ('customer__username', 'customer_name', 'customer_phone', 'customer_email')

    def cart_items(self, obj):
        return obj.get_cart_items
    cart_items.short_description = 'Số SP'

    def cart_total(self, obj):
        return f"{obj.get_cart_total:,}đ"
    cart_total.short_description = 'Tổng tiền'
    
    def discount(self, obj):
        discount_amt = obj.get_discount_amount
        if discount_amt > 0:
            return f"-{discount_amt:,}đ"
        return "-"
    discount.short_description = 'Giảm giá'

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_amount', 'discount_percent', 'is_active', 'used_count', 'expires_at')
    list_filter = ('is_active',)
    search_fields = ('code',)
    filter_horizontal = ('used_by',)
    
    def used_count(self, obj):
        return obj.used_by.count()
    used_count.short_description = 'Đã dùng'

admin.site.register(OrderItem)