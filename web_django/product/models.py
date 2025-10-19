from django.db import models
from django.forms import ValidationError
from django.contrib.auth.models import User
# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=200,null=True)
    slug = models.SlugField(max_length=200,unique=True)
    def __str__(self):
        return self.name
    
class Product(models.Model):
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
