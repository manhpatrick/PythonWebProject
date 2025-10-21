from django.apps import AppConfig


class ProductConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'product'
    
    def ready(self):
        """Đăng ký signals khi app khởi động"""
        import product.signals  # Import signals để kích hoạt
