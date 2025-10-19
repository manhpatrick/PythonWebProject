from django.shortcuts import render, redirect
from django.contrib import messages
from order.models import Order, Coupon
from authentication.models import Address, Profile
from django.contrib.auth.decorators import login_required
from django.utils import timezone

# Create your views here.
@login_required(login_url='signin')
def purchase(request):
    if request.method == 'POST':
        # Xử lý đặt hàng
        order = Order.objects.filter(customer=request.user, complete=False).first()
        
        if order and order.get_cart_items > 0:
            # Lấy thông tin từ form
            full_name = request.POST.get('full_name')
            phone = request.POST.get('phone')
            email = request.POST.get('email')
            street = request.POST.get('street')
            ward = request.POST.get('ward')
            district = request.POST.get('district')
            city = request.POST.get('city')
            note = request.POST.get('note', '')
            payment_method = request.POST.get('payment_method', 'COD')
            
            # Cập nhật thông tin đơn hàng
            order.complete = True
            order.shipping_address = f"{street}, {ward}, {district}, {city}"
            order.customer_name = full_name
            order.customer_phone = phone
            order.customer_email = email
            order.note = note
            order.payment_method = payment_method
            
            # Đánh dấu coupon đã được sử dụng (nếu có)
            if order.coupon:
                order.coupon.mark_used_by(request.user)
            
            order.save()
            
            messages.success(request, 'Đặt hàng thành công! Chúng tôi sẽ liên hệ với bạn sớm nhất.')
            return redirect('profile')
        else:
            messages.error(request, 'Giỏ hàng của bạn đang trống!')
            return redirect('purchase')
    
    # GET request - hiển thị trang giỏ hàng
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
        
        # Lấy địa chỉ mặc định
        default_address = Address.objects.filter(user=request.user, is_default=True).first()
        
        # Lấy thông tin profile
        profile = Profile.objects.filter(user=request.user).first()
        
        # Lấy các coupon đang active và chưa hết hạn
        active_coupons = Coupon.objects.filter(is_active=True).filter(
            expires_at__gt=timezone.now()
        ) | Coupon.objects.filter(is_active=True, expires_at__isnull=True)
        
        # Thông tin user
        user_info = {
            'full_name': profile.full_name if profile else '',
            'phone': profile.phone if profile else '',
            'email': request.user.email,
        }
        
        # Thông tin địa chỉ
        address_info = {
            'street': default_address.street if default_address else '',
            'ward': default_address.ward if default_address else '',
            'district': default_address.district if default_address else '',
            'city': default_address.city if default_address else '',
        }
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}
        cartItems = 0
        user_info = {'full_name': '', 'phone': '', 'email': ''}
        address_info = {'street': '', 'ward': '', 'district': '', 'city': ''}
        active_coupons = []
    
    context = {
        'order': order,
        'items': items,
        'cartItems': cartItems,
        'user_info': user_info,
        'address_info': address_info,
        'shipping_fee': 30000,  # Phí vận chuyển cố định
        'active_coupons': active_coupons[:3],  # Chỉ hiển thị 3 mã
    }
    return render(request, "purchase.html", context)