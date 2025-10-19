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
