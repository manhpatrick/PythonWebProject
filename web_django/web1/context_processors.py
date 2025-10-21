from urllib.parse import urlencode

def next_url_processor(request):
    """
    Context processor để tạo next URL với đầy đủ query parameters
    """
    # Lấy full path bao gồm cả query string
    full_path = request.get_full_path()
    
    # Nếu đang ở trang signin/signup/reset, lấy next từ GET params
    if request.path in ['/authentication/signin/', '/authentication/signup/', '/authentication/reset-password/']:
        next_param = request.GET.get('next', '')
        if next_param:
            full_path = next_param
    
    return {
        'current_full_path': full_path,
    }

def user_display_name(request):
    """
    Context processor để lấy tên hiển thị của user
    """
    display_name = "Khách"
    
    if request.user.is_authenticated:
        user = request.user
        
        # Thứ tự ưu tiên: full_name > username từ email > username
        try:
            if hasattr(user, 'profile') and user.profile.full_name:
                display_name = user.profile.full_name
            elif user.email:
                display_name = user.email.split('@')[0]
            elif user.username:
                display_name = user.username
            else:
                display_name = "Người dùng"
        except:
            display_name = user.username if user.username else "Người dùng"
    
    return {
        'user_display_name': display_name,
    }
