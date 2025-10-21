from django.db import models
from django.forms import ValidationError
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=200,null=True)
    slug = models.SlugField(max_length=200,unique=True)
    def __str__(self):
        return self.name
    
class Product(models.Model):
    SIZE_CHOICES = [
        ('S', 'Size S'),
        ('M', 'Size M'),
        ('L', 'Size L'),
        ('XL', 'Size XL'),
    ]
    
    category = models.ManyToManyField(Category,related_name='product')
    name = models.CharField(max_length=200,null=True)
    old_price = models.IntegerField()
    new_price = models.IntegerField(null=True, blank=True)
    discount_percent = models.FloatField(default=0, blank=True)
    sold_number = models.IntegerField(default=0)
    rating = models.FloatField(default=0)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    country=models.CharField(max_length=200,null=True)
    brand=models.CharField(max_length=200,null=True)
    detail = models.TextField(null=True,blank=True)
    available_sizes = models.CharField(max_length=50, default='S,M,L,XL', help_text='Các size có sẵn, ngăn cách bởi dấu phẩy')
    exclude = ('discount_percent',)
    def __str__(self):
        return self.name
    @property
    def imageURL(self):
        try:
            url = self.image.url
        except:
            url = ''
        return url
    
    def clean(self):
        if self.new_price is not None and self.old_price is not None:
            if self.new_price >= self.old_price:
                raise ValidationError("Giá mới phải nhỏ hơn giá cũ!")
            
    def save(self, *args, **kwargs):
        if self.old_price and self.new_price and self.new_price < self.old_price:
            self.discount_percent = round((1 - self.new_price / self.old_price) * 100, 1)
        else:
            self.discount_percent = 0
        super().save(*args, **kwargs)
    
    def get_total_stock(self):
        """Tổng số lượng tồn kho của tất cả các size"""
        return sum([inv.stock_quantity for inv in self.inventory.all()])
    
    def get_available_stock(self, size):
        """Số lượng còn có thể bán cho size cụ thể"""
        try:
            inventory = self.inventory.get(size=size)
            return inventory.available_quantity
        except:
            return 0


class ProductInventory(models.Model):
    """
    QUẢN LÝ TỒN KHO THEO SIZE
    - Mỗi sản phẩm có nhiều size, mỗi size có số lượng tồn riêng
    - stock_quantity: Tổng số lượng trong kho
    - reserved_quantity: Số lượng đang trong giỏ hàng (chưa thanh toán)
    - sold_quantity: Số lượng đã bán (đã thanh toán)
    """
    SIZE_CHOICES = [
        ('S', 'Size S'),
        ('M', 'Size M'),
        ('L', 'Size L'),
        ('XL', 'Size XL'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory')
    size = models.CharField(max_length=5, choices=SIZE_CHOICES)
    stock_quantity = models.IntegerField(default=0, help_text='Tổng số lượng trong kho')
    reserved_quantity = models.IntegerField(default=0, help_text='Số lượng đang giữ trong giỏ hàng')
    sold_quantity = models.IntegerField(default=0, help_text='Số lượng đã bán')
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('product', 'size')
        verbose_name = 'Tồn kho'
        verbose_name_plural = 'Tồn kho'
        ordering = ['product', 'size']
    
    def __str__(self):
        return f"{self.product.name} - Size {self.size}: {self.available_quantity}/{self.stock_quantity}"
    
    @property
    def available_quantity(self):
        """Số lượng thực tế có thể bán = Tồn kho - Đang giữ - Đã bán"""
        return max(0, self.stock_quantity - self.reserved_quantity - self.sold_quantity)
    
    def clean(self):
        """Validation: Đảm bảo số lượng hợp lệ"""
        if self.stock_quantity < 0:
            raise DjangoValidationError({'stock_quantity': 'Số lượng tồn kho không được âm'})
        if self.reserved_quantity < 0:
            raise DjangoValidationError({'reserved_quantity': 'Số lượng giữ không được âm'})
        if self.sold_quantity < 0:
            raise DjangoValidationError({'sold_quantity': 'Số lượng bán không được âm'})
        if self.reserved_quantity + self.sold_quantity > self.stock_quantity:
            raise DjangoValidationError('Tổng số lượng giữ và bán vượt quá tồn kho!')
    
    def reserve(self, quantity):
        """Giữ hàng khi khách thêm vào giỏ"""
        if quantity > self.available_quantity:
            raise ValueError(f'Chỉ còn {self.available_quantity} sản phẩm size {self.size}')
        self.reserved_quantity += quantity
        self.save()
    
    def release(self, quantity):
        """Trả lại hàng khi khách xóa khỏi giỏ"""
        self.reserved_quantity = max(0, self.reserved_quantity - quantity)
        self.save()
    
    def complete_sale(self, quantity):
        """Hoàn tất bán hàng - chuyển từ reserved sang sold"""
        if quantity > self.reserved_quantity:
            raise ValueError('Số lượng bán vượt quá số lượng đã giữ')
        self.reserved_quantity -= quantity
        self.sold_quantity += quantity
        self.save()
