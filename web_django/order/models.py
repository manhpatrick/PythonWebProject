from django.db import models
from django.forms import ValidationError
from django.contrib.auth.models import User
from product.models import Product
from django.core.validators import MinValueValidator, MaxValueValidator
# Create your models here.
class Order(models.Model):
    PAYMENT_CHOICES = [
        ('COD', 'Thanh toán khi nhận hàng'),
        ('BANK', 'Chuyển khoản ngân hàng'),
        ('EWALLET', 'Ví điện tử'),
    ]
    
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_ordered = models.DateTimeField(auto_now_add=True)
    complete = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Thông tin khách hàng
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)
    
    # Thông tin giao hàng
    shipping_address = models.TextField(blank=True)
    note = models.TextField(blank=True, verbose_name="Ghi chú")
    
    # Phương thức thanh toán
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='COD')
    
    # Coupon
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')

    def __str__(self):
        return str(self.id)

    @property
    def get_cart_total(self):
        orderitems = self.orderitem_set.all()
        total = sum([item.get_total for item in orderitems])
        return total
    
    @property
    def get_discount_amount(self):
        """Tính số tiền giảm giá từ coupon"""
        if not self.coupon or not self.coupon.is_active:
            return 0
        
        # Check if coupon expired
        if self.coupon.expires_at:
            from django.utils import timezone
            if timezone.now() > self.coupon.expires_at:
                return 0
        
        cart_total = self.get_cart_total
        
        if self.coupon.discount_amount:
            return min(self.coupon.discount_amount, cart_total)
        elif self.coupon.discount_percent:
            return int(cart_total * self.coupon.discount_percent / 100)
        
        return 0
    
    @property
    def get_final_total(self):
        """Tổng tiền sau khi áp dụng coupon (chưa cộng phí ship)"""
        return self.get_cart_total - self.get_discount_amount

    @property
    def get_cart_items(self):
        orderitems = self.orderitem_set.all()
        total = sum([item.quantity for item in orderitems])
        return total

class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.IntegerField(default=0, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)  # ← Quan trọng!

    @property
    def get_total(self):
        if self.product.new_price:
            return self.product.new_price * self.quantity
        else:
            return self.product.old_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_amount = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Giảm theo số tiền (VNĐ)"
    )
    discount_percent = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Giảm theo phần trăm (%)"
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ManyToManyField(User, blank=True, related_name='used_coupons', help_text="Users đã sử dụng mã này")

    def clean(self):
        super().clean()
        # Chỉ được chọn 1 trong 2 loại giảm giá
        if self.discount_amount and self.discount_percent:
            raise ValidationError("Chỉ được chọn một loại giảm giá: hoặc theo tiền, hoặc theo phần trăm.")
        if not self.discount_amount and not self.discount_percent:
            raise ValidationError("Phải có ít nhất một loại giảm giá (tiền hoặc phần trăm).")
    
    def is_used_by(self, user):
        """Kiểm tra xem user đã dùng mã này chưa"""
        return self.used_by.filter(id=user.id).exists()
    
    def mark_used_by(self, user):
        """Đánh dấu user đã dùng mã này"""
        if not self.is_used_by(user):
            self.used_by.add(user)

    def __str__(self):
        return f"{self.code}"
