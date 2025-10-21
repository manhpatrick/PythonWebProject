from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from allauth.account.models import EmailAddress
from django.urls import reverse

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    
    def get_login_redirect_url(self, request):
        """
        Redirect về trang callback sau khi OAuth thành công
        """
        return reverse('google_oauth_callback')
    
    
    def pre_social_login(self, request, sociallogin):
        """
        Tự động kết nối tài khoản Google với tài khoản email đã tồn tại
        """
        # Nếu user đã đăng nhập rồi, bỏ qua
        if sociallogin.is_existing:
            return
        
        # Lấy email từ social account
        email = sociallogin.account.extra_data.get('email', '').lower()
        
        if not email:
            return
        
        try:
            # Tìm user đã tồn tại với email này
            existing_user = User.objects.get(email=email)
            
            # Kết nối social account với user đã tồn tại
            sociallogin.connect(request, existing_user)
            
            # Đảm bảo email được verify
            EmailAddress.objects.get_or_create(
                user=existing_user,
                email=email,
                defaults={'verified': True, 'primary': True}
            )
            
        except User.DoesNotExist:
            # User chưa tồn tại, để flow bình thường
            pass
    
    def populate_user(self, request, sociallogin, data):
        """
        Tự động điền thông tin user và xử lý username trùng
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Lấy email từ data hoặc từ sociallogin
        email = data.get('email') or sociallogin.account.extra_data.get('email', '')
        
        # BẮT BUỘC phải có email
        if not email:
            raise ValidationError("Email is required for social login")
        
        user.email = email
        
        # Tự động tạo username từ email nếu chưa có
        if not user.username or user.username.strip() == '':
            base_username = email.split('@')[0]
            user.username = base_username
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """
        Lưu user và tự động xử lý username trùng
        """
        user = super().save_user(request, sociallogin, form)
        
        # Đảm bảo user có email và username hợp lệ
        if not user.email or user.email.strip() == '':
            # Lấy email từ sociallogin
            email = sociallogin.account.extra_data.get('email', '')
            if email:
                user.email = email
                if not user.username or user.username.strip() == '':
                    user.username = email.split('@')[0]
        
        # Nếu username bị trùng, tự động thêm số vào
        if User.objects.filter(username=user.username).exclude(pk=user.pk).exists():
            base_username = user.username
            counter = 1
            while User.objects.filter(username=f"{base_username}{counter}").exists():
                counter += 1
            user.username = f"{base_username}{counter}"
        
        # Lưu lại nếu có thay đổi
        user.save()
        
        return user
