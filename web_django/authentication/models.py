from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    GENDER_CHOICES = [
        ('Nam', 'Nam'),
        ('Nữ', 'Nữ'),
        ('Khác', 'Khác'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=200, blank=True, verbose_name="Họ và tên")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Số điện thoại")
    birthday = models.DateField(null=True, blank=True, verbose_name="Ngày sinh")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Nam', verbose_name="Giới tính")
    def __str__(self):
        return f"Profile của {self.user.username}"
    
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    street = models.CharField(max_length=255, verbose_name="Số nhà, tên đường")
    ward = models.CharField(max_length=100, verbose_name="Phường/Xã")
    district = models.CharField(max_length=100, verbose_name="Quận/Huyện")
    city = models.CharField(max_length=100, verbose_name="Tỉnh/Thành phố")
    is_default = models.BooleanField(default=False, verbose_name="Địa chỉ mặc định")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name = "Địa chỉ"
        verbose_name_plural = "Địa chỉ"
    
    def __str__(self):
        return f"{self.get_full_address()}"
    
    def get_full_address(self):
        return f"{self.street}, {self.ward}, {self.district}, {self.city}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None  # kiểm tra xem có phải record mới không
        if self.is_default:
            # Nếu đặt địa chỉ này làm mặc định, bỏ mặc định của địa chỉ khác cùng user
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        elif is_new and not Address.objects.filter(user=self.user).exists():
            # Nếu là địa chỉ đầu tiên của user → tự động set làm mặc định
            self.is_default = True
        super().save(*args, **kwargs)