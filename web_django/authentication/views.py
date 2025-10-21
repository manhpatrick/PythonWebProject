from tokenize import generate_tokens
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
from django.core.mail import EmailMessage,send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.paginator import Paginator
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from product.models import Category, Product
from product.views import render_stars_home
from .tokens import generate_token
from .models import Address, Profile
from order.models import Order, OrderItem

def is_strong_password(password):
    if len(password) < 8:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    return has_upper and has_lower and has_digit and has_special
def valid_email(email):
    import re
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def signup(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        next_url = request.POST.get("next", "")
        
        # Validate password match
        if password1 != password2:
            messages.error(request, "Mật khẩu không khớp.")
            if next_url:
                from urllib.parse import urlencode
                return redirect(f"{reverse('signup')}?next={next_url}")
            return redirect("signup")
        
        # Check email exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email đã được đăng ký.")
            if next_url:
                from urllib.parse import quote
                return redirect(f"{reverse('signup')}?next={quote(next_url)}")
            return redirect("signup")
        
        # Validate password strength
        if not is_strong_password(password1):
            messages.error(request, "Mật khẩu phải có ít nhất 8 ký tự, chứa chữ hoa, số và ký tự đặc biệt.")
            if next_url:
                from urllib.parse import quote
                return redirect(f"{reverse('signup')}?next={quote(next_url)}")
            return redirect("signup")
        
        # Validate email format
        if not valid_email(email):
            messages.error(request, "Email không hợp lệ.")
            if next_url:
                from urllib.parse import quote
                return redirect(f"{reverse('signup')}?next={quote(next_url)}")
            return redirect("signup")
        
        # Create user
        myuser = User.objects.create_user(username=email, email=email, password=password1)
        myuser.is_active = False
        myuser.save()
        
        messages.success(request, "Tài khoản của bạn đã được tạo thành công. Một mã xác thực (OTP) đã được gửi tới địa chỉ email của bạn. Vui lòng kiểm tra hộp thư và nhập mã để hoàn tất.")
        
        # Welcome email
        subject = "Chào mừng bạn đến với trang web Sport Clothes của chúng tôi"
        message = "Xin chào, cảm ơn bạn đã đăng ký! Vui lòng xác thực email để hoàn tất."
        from_email = settings.EMAIL_HOST_USER
        to_list = [myuser.email]
        send_mail(subject, message, from_email, to_list, fail_silently=True)
        
        # OTP Code Email
        current_site = get_current_site(request)
        email_subject = "Confirm your email"
        message2 = render_to_string('email_confirmation.html', {
            'name': myuser.email.split('@')[0],
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(myuser.pk)),
            'token': generate_token.make_token(myuser),
        })
        email = EmailMessage(
            email_subject,
            message2,
            settings.EMAIL_HOST_USER,
            [myuser.email],
        )
        email.content_subtype = "html"
        email.fail_silently = True
        email.send()
        
        # Redirect về signin với next parameter
        if next_url:
            from urllib.parse import quote
            return redirect(f"{reverse('signin')}?next={quote(next_url)}")
        return redirect("signin")
    
    # GET request
    next_url = request.GET.get("next", "")
    
    # Parse query params từ next_url
    from urllib.parse import urlparse, parse_qs
    category_filter = None
    search_query = ""
    sort_by = ""
    page_from_next = "1"
    
    if next_url:
        parsed = urlparse(next_url)
        query_params = parse_qs(parsed.query)
        
        # Lấy các params (note: search page uses 'searched' parameter)
        search_query = query_params.get('searched', [''])[0]  # Changed from 'search' to 'searched'
        sort_by = query_params.get('sort', [''])[0]
        page_from_next = query_params.get('page', ['1'])[0]
        
        # Parse category từ path
        if '/category/' in parsed.path:
            try:
                category_slug = parsed.path.split('/category/')[1].split('/')[0]
                category_filter = Category.objects.get(slug=category_slug)
            except:
                pass
    
    # Build product list với filters
    product_list = Product.objects.all()
    
    if category_filter:
        product_list = product_list.filter(category=category_filter)
    
    if search_query:
        product_list = product_list.filter(name__icontains=search_query)
    
    # Apply sorting - same logic as product/views.py
    if sort_by == "popular":
        product_list = product_list.order_by('-rating')
    elif sort_by == "newest":
        product_list = product_list.order_by('-id')
    elif sort_by == "best_selling":
        product_list = product_list.order_by('-sold_number')
    elif sort_by == "price_asc":
        product_list = product_list.order_by('new_price')
    elif sort_by == "price_desc":
        product_list = product_list.order_by('-new_price')
    else:
        product_list = product_list.order_by('-id')  # Default to newest
    
    # Phân trang
    paginator = Paginator(product_list, 5)
    page_obj = paginator.get_page(page_from_next)

    categories = Category.objects.all()

    # Gắn sao
    for p in page_obj:
        p.stars_html = render_stars_home(p.rating)
    
    return render(request, "Authentication/signup.html", {
        "page_obj": page_obj,
        "categories": categories,
        "products": page_obj,
        "next": next_url,
        "search_query": search_query,
        "searched": search_query,  # For template compatibility with search page
        "sort_by": sort_by,
        "current_sort": sort_by,  # For UI highlighting
        "current_category": category_filter,  # For category highlighting
        "category": category_filter,  # For template compatibility with index.html
    })

# Đăng nhập
def signin(request):
    if request.method == "POST":
        email = request.POST.get("Email")
        password = request.POST.get("password")
        next_url = request.POST.get("next")
        
        user = authenticate(username=email, password=password)
        if user is not None:
            login(request, user)
            request.session["accountname"] = email.split('@')[0]
            
            if next_url and next_url != '':
                return redirect(next_url)
            return redirect("main")
        else:
            messages.error(request, "Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.")
            if next_url:
                from urllib.parse import quote
                return redirect(f"{reverse('signin')}?next={quote(next_url)}")
            return redirect("signin")
    
    # GET request
    next_url = request.GET.get("next", "")
    
    # Parse query params từ next_url
    from urllib.parse import urlparse, parse_qs
    category_filter = None
    search_query = ""
    sort_by = ""
    page_from_next = "1"
    
    if next_url:
        parsed = urlparse(next_url)
        query_params = parse_qs(parsed.query)
        
        # Lấy các params (note: search page uses 'searched' parameter)
        search_query = query_params.get('searched', [''])[0]  # Changed from 'search' to 'searched'
        sort_by = query_params.get('sort', [''])[0]
        page_from_next = query_params.get('page', ['1'])[0]
        
        # Parse category từ path
        if '/category/' in parsed.path:
            try:
                category_slug = parsed.path.split('/category/')[1].split('/')[0]
                category_filter = Category.objects.get(slug=category_slug)
            except:
                pass
    
    # Build product list với filters
    product_list = Product.objects.all()
    
    if category_filter:
        product_list = product_list.filter(category=category_filter)
    
    if search_query:
        product_list = product_list.filter(name__icontains=search_query)
    
    # Apply sorting - same logic as product/views.py
    if sort_by == "popular":
        product_list = product_list.order_by('-rating')
    elif sort_by == "newest":
        product_list = product_list.order_by('-id')
    elif sort_by == "best_selling":
        product_list = product_list.order_by('-sold_number')
    elif sort_by == "price_asc":
        product_list = product_list.order_by('new_price')
    elif sort_by == "price_desc":
        product_list = product_list.order_by('-new_price')
    else:
        product_list = product_list.order_by('-id')  # Default to newest
    
    # Phân trang
    paginator = Paginator(product_list, 5)
    page_obj = paginator.get_page(page_from_next)

    categories = Category.objects.all()

    # Gắn sao
    for p in page_obj:
        p.stars_html = render_stars_home(p.rating)
    
    return render(request, "Authentication/signin.html", {
        "page_obj": page_obj,
        "categories": categories,
        "products": page_obj,
        "next": next_url,
        "search_query": search_query,
        "searched": search_query,  # For template compatibility with search page
        "sort_by": sort_by,
        "current_sort": sort_by,  # For UI highlighting
        "current_category": category_filter,  # For category highlighting
        "category": category_filter,  # For template compatibility with index.html
    })

#Đăng xuất
def signout(request):
    logout(request)
    return redirect("main")

# Xác thực email
def activate(request, uidb64, token):
    try:
        uid=force_str(urlsafe_base64_decode(uidb64))
        myuser=User.objects.get(pk=uid)
    except (TypeError,ValueError,OverflowError,User.DoesNotExist):
        myuser=None
    if myuser is not None and generate_token.check_token(myuser,token):
        myuser.is_active=True
        myuser.save()
        login(request,myuser)
        request.session['accountname'] = myuser.email.split('@')[0]
        return redirect("main")
    else:
        return render(request,'activation_failed.html')
    
# Đặt lại mật khẩu
def reset_password(request):
    next_url = request.GET.get("next", "")
    current_page = request.GET.get("page", "1")

    # --- POST: Gửi email đặt lại mật khẩu ---
    if request.method == "POST":
        email = request.POST.get("Email")
        try:
            myuser = User.objects.get(email=email)
            if not myuser.is_active:
                messages.error(request, "Tài khoản chưa kích hoạt, không thể đặt lại mật khẩu.")
                return redirect(f"reset_password?next={next_url}&page={current_page}")

            # Gửi email đặt lại mật khẩu
            current_site = get_current_site(request)
            mail_subject = "Yêu cầu đặt lại mật khẩu - Sport Clothes"
            message = render_to_string(
                'Authentication/Forget_password/reset_password_email.html',
                {
                    'name': myuser.email.split('@')[0],
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(myuser.pk)),
                    'token': generate_token.make_token(myuser),
                }
            )

            email_obj = EmailMessage(
                mail_subject,
                message,
                settings.EMAIL_HOST_USER,
                [myuser.email],
            )
            email_obj.content_subtype = "html"
            email_obj.fail_silently = True
            email_obj.send()

            messages.success(request, "Đã gửi email đặt lại mật khẩu.")
        except User.DoesNotExist:
            messages.error(request, "Email không tồn tại trong hệ thống.")
            return redirect(f"reset_password?next={next_url}&page={current_page}")

    # --- GET: Hiển thị sản phẩm + danh mục ---
    # Parse query params từ next_url
    from urllib.parse import urlparse, parse_qs
    category_filter = None
    search_query = ""
    sort_by = ""
    page_from_next = "1"
    
    if next_url:
        parsed = urlparse(next_url)
        query_params = parse_qs(parsed.query)
        
        # Lấy các params (note: search page uses 'searched' parameter)
        search_query = query_params.get('searched', [''])[0]  # Changed from 'search' to 'searched'
        sort_by = query_params.get('sort', [''])[0]
        page_from_next = query_params.get('page', ['1'])[0]
        
        # Parse category từ path
        if '/category/' in parsed.path:
            try:
                category_slug = parsed.path.split('/category/')[1].split('/')[0]
                category_filter = Category.objects.get(slug=category_slug)
            except:
                pass
    
    # Build product list với filters
    product_list = Product.objects.all()
    
    if category_filter:
        product_list = product_list.filter(category=category_filter)
    
    if search_query:
        product_list = product_list.filter(name__icontains=search_query)
    
    # Apply sorting - same logic as product/views.py
    if sort_by == "popular":
        product_list = product_list.order_by('-rating')
    elif sort_by == "newest":
        product_list = product_list.order_by('-id')
    elif sort_by == "best_selling":
        product_list = product_list.order_by('-sold_number')
    elif sort_by == "price_asc":
        product_list = product_list.order_by('new_price')
    elif sort_by == "price_desc":
        product_list = product_list.order_by('-new_price')
    else:
        product_list = product_list.order_by('-id')  # Default to newest

    # Sắp xếp và phân trang
    paginator = Paginator(product_list, 5)
    page_obj = paginator.get_page(page_from_next)

    # Lấy danh mục
    categories = Category.objects.all()

    # Gắn sao hiển thị cho từng sản phẩm
    for p in page_obj:
        p.stars_html = render_stars_home(p.rating)

    # Render template
    return render(request, "Authentication/Forget_password/reset_password.html", {
        "page_obj": page_obj,
        "categories": categories,
        "products": page_obj,
        "next": next_url,
        "search_query": search_query,
        "searched": search_query,  # For template compatibility with search page
        "sort_by": sort_by,
        "current_sort": sort_by,  # For UI highlighting
        "current_category": category_filter,  # For category highlighting
        "category": category_filter,  # For template compatibility with index.html
    })

# Xác nhận đặt lại mật khẩu
def reset_password_confirm(request, uidb64, token):
    next_url = request.GET.get('next', '/')
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        myuser = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        myuser = None
    
    if myuser is not None and generate_token.check_token(myuser, token):
        if request.method == "POST":
            password1 = request.POST.get("password1")
            password2 = request.POST.get("password2")
            next_url = request.POST.get("next_url", "/")
            
            if password1 and password1 == password2 and is_strong_password(password1):
                myuser.set_password(password1)
                myuser.save()
                messages.success(request, "Mật khẩu đã được thay đổi thành công.")
                if next_url and next_url != '':
                    return redirect(next_url)
                return redirect('main')
            else:
                messages.error(request, "Mật khẩu không hợp lệ hoặc không khớp. Vui lòng thử lại.")
        
        # Parse query params từ next_url
        from urllib.parse import urlparse, parse_qs
        category_filter = None
        search_query = ""
        sort_by = ""
        page_from_next = "1"
        
        if next_url:
            parsed = urlparse(next_url)
            query_params = parse_qs(parsed.query)
            
            # Lấy các params (note: search page uses 'searched' parameter)
            search_query = query_params.get('searched', [''])[0]  # Changed from 'search' to 'searched'
            sort_by = query_params.get('sort', [''])[0]
            page_from_next = query_params.get('page', ['1'])[0]
            
            # Parse category từ path
            if '/category/' in parsed.path:
                try:
                    category_slug = parsed.path.split('/category/')[1].split('/')[0]
                    category_filter = Category.objects.get(slug=category_slug)
                except:
                    pass
        
        # Build product list với filters
        product_list = Product.objects.all()
        
        if category_filter:
            product_list = product_list.filter(category=category_filter)
        
        if search_query:
            product_list = product_list.filter(name__icontains=search_query)
        
        # Apply sorting - same logic as product/views.py
        if sort_by == "popular":
            product_list = product_list.order_by('-rating')
        elif sort_by == "newest":
            product_list = product_list.order_by('-id')
        elif sort_by == "best_selling":
            product_list = product_list.order_by('-sold_number')
        elif sort_by == "price_asc":
            product_list = product_list.order_by('new_price')
        elif sort_by == "price_desc":
            product_list = product_list.order_by('-new_price')
        else:
            product_list = product_list.order_by('-id')  # Default to newest
            
        categories = Category.objects.all()             
        paginator = Paginator(product_list, 5)
        page_obj = paginator.get_page(page_from_next)
        
        return render(request, "Authentication/Forget_password/reset_password_confirm.html", {
            "page_obj": page_obj,
            "categories": categories, # type: ignore
            "products": page_obj,
            "next": next_url,
            "next_url": next_url,  # For form hidden field
            "search_query": search_query,
            "searched": search_query,  # For template compatibility with search page
            "sort_by": sort_by,
            "current_sort": sort_by,  # For UI highlighting
            "current_category": category_filter,  # For category highlighting
            "category": category_filter,  # For template compatibility with index.html
            "uidb64": uidb64,
            "token": token,
        })
    else:
        return render(request, "activation_failed.html")

#Sửa Profile
def update_profile(request):
    if request.method == "POST":
        user = request.user
        profile, created = Profile.objects.get_or_create(user=user)
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        birthday = request.POST.get("birthday")
        gender = request.POST.get("gender")
        profile.full_name=full_name
        profile.phone = phone
        profile.gender = gender
        profile.birthday = birthday if birthday else None
        profile.save()
    messages.success(request, "Cập nhật thông tin thành công 🎉")
    return redirect("/authentication/profile")
    return render(request, "profile.html")
#login_required
# ============= ADDRESS MANAGEMENT =============

@login_required
def address_list(request):
    """Danh sách địa chỉ - Redirect về profile#address"""
    return redirect('/authentication/profile#address')

@login_required
def address_add(request):
    """Thêm địa chỉ mới - Redirect về profile#address"""
    return redirect('/authentication/profile#address')

@login_required
def address_edit(request, address_id):
    """Sửa địa chỉ"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        address.street = request.POST.get('street')
        address.ward = request.POST.get('ward')
        address.district = request.POST.get('district')
        address.city = request.POST.get('city')
        
        # Xử lý is_default
        is_default = request.POST.get('is_default') == 'on'
        if is_default and not address.is_default:
            # Nếu set làm mặc định, bỏ mặc định của địa chỉ khác
            Address.objects.filter(user=request.user).update(is_default=False)
        address.is_default = is_default
        
        address.save()
        messages.success(request, "✏️ Đã cập nhật địa chỉ!")
        return redirect('/authentication/profile/#address')
    
    return redirect('/authentication/profile/#address')

@login_required
def address_delete(request, address_id):
    """Xóa địa chỉ"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    # Nếu xóa địa chỉ mặc định, set địa chỉ khác làm mặc định
    if address.is_default:
        other_address = Address.objects.filter(user=request.user).exclude(id=address_id).first()
        if other_address:
            other_address.is_default = True
            other_address.save()
    
    address.delete()
    messages.success(request, "🗑️ Đã xóa địa chỉ!")
    return redirect('/authentication/profile#address')

@login_required
def address_set_default(request, address_id):
    """Đặt địa chỉ mặc định"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    # Bỏ mặc định tất cả địa chỉ khác
    Address.objects.filter(user=request.user).update(is_default=False)
    
    # Set địa chỉ này làm mặc định
    address.is_default = True
    address.save()
    
    messages.success(request, "✅ Đã đặt làm địa chỉ mặc định!")
    return redirect('/authentication/profile#address')
#Trang hỗ trợ           
def guide(request):
    return render(request, "Authentication/guide.html")
def policy(request):
    return render(request, "Authentication/Forget_password/policy.html")

@login_required(login_url='signin')
def profile(request):
    # Xử lý form thêm địa chỉ
    if request.method == 'POST' and request.POST.get('action') == 'add_address':
        # Debug: In ra thông tin POST data
        print("=" * 50)
        print("DEBUG: Đang thêm địa chỉ mới")
        print(f"User: {request.user.username}")
        print(f"Street: {request.POST.get('street')}")
        print(f"Ward: {request.POST.get('ward')}")
        print(f"District: {request.POST.get('district')}")
        print(f"City: {request.POST.get('city')}")
        
        # Tạo địa chỉ mới (KHÔNG CẦN full_name và phone nữa)
        new_address = Address.objects.create(
            user=request.user,
            street=request.POST.get('street'),
            ward=request.POST.get('ward'),
            district=request.POST.get('district'),
            city=request.POST.get('city'),
            is_default=request.POST.get('is_default') == 'on'
        )
        
        print(f"✓ Địa chỉ đã được tạo với ID: {new_address.id}")
        print("=" * 50)
        
        messages.success(request, 'Đã thêm địa chỉ thành công!')
        return redirect('/authentication/profile/#address')
    
    # Giỏ hàng chưa thanh toán
    current_order, created = Order.objects.get_or_create(
        customer=request.user, 
        complete=False
    )
    current_items = current_order.orderitem_set.all()
    
    # Lịch sử đơn hàng đã hoàn tất
    completed_orders = Order.objects.filter(
        customer=request.user, 
        complete=True
    ).order_by('-date_ordered')
    
    # Lấy tất cả địa chỉ của user
    addresses = Address.objects.filter(user=request.user)
    
    print(f"DEBUG: User {request.user.username} có {addresses.count()} địa chỉ")
    
    context = {
        'current_order': current_order,
        'current_items': current_items,
        'completed_orders': completed_orders,
        'addresses': addresses,
        # Thêm các biến cần thiết cho template
        'order': current_order,
        'items': current_items,
        'cart_count': current_order.get_cart_items,
        'cart_total': current_order.get_cart_total,
    }
    return render(request, "profile.html", context)

@login_required
def google_oauth_callback(request):
    """
    Trang callback sau khi đăng nhập Google thành công
    Sẽ gửi message về parent window và tự đóng popup
    """
    return render(request, 'Authentication/google_callback.html', {
        'user': request.user
    })
