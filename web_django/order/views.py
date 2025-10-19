from time import timezone
from django.shortcuts import render
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from order.models import Order, OrderItem
from .models import Coupon, Product
import json
# Create your views here.
@csrf_exempt
def add_to_cart(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Vui lòng đăng nhập để thêm sản phẩm'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        if not product_id:
            return JsonResponse({'success': False, 'error': 'Thiếu product_id'})

        product = Product.objects.get(id=product_id)
        order, _ = Order.objects.get_or_create(customer=request.user, complete=False)
        order_item, created = OrderItem.objects.get_or_create(order=order, product=product)

        if created:
            order_item.quantity = quantity
        else:
            order_item.quantity += quantity

        order_item.save()

        return JsonResponse({
            'success': True,
            'cartItems': order.get_cart_items,
            'cartTotal': order.get_cart_total,
            'message': f'Đã thêm {product.name} vào giỏ hàng!',
        })

    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Sản phẩm không tồn tại'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Lỗi: {str(e)}'})

def updateItem(request):
    data = json.loads(request.body)
    productId = data['productId']
    action = data['action']

    customer = request.user
    product = Product.objects.get(id=productId)
    order, _ = Order.objects.get_or_create(customer=customer, complete=False)
    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

    if action == 'add':
        orderItem.quantity += 1
    elif action == 'remove':
        orderItem.quantity -= 1
    elif action == 'delete':
        orderItem.delete()
        return JsonResponse({'message': 'Item deleted'}, safe=False)

    orderItem.save()
    if orderItem.quantity <= 0:
        orderItem.delete()

    return JsonResponse('Item was updated', safe=False)

@login_required
def apply_coupon(request):
    """API để validate và áp dụng coupon"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip().upper()
        
        if not code:
            return JsonResponse({'success': False, 'error': 'Vui lòng nhập mã giảm giá'})
        
        # Lấy order hiện tại
        order = Order.objects.filter(customer=request.user, complete=False).first()
        
        if not order or order.get_cart_items == 0:
            return JsonResponse({'success': False, 'error': 'Giỏ hàng của bạn đang trống'})
        
        # Tìm coupon
        try:
            coupon = Coupon.objects.get(code=code, is_active=True)
        except Coupon.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Mã giảm giá không hợp lệ'})
        
        # Kiểm tra xem user đã dùng mã này chưa (chỉ check các order đã hoàn thành)
        if coupon.is_used_by(request.user):
            return JsonResponse({'success': False, 'error': 'Bạn đã sử dụng mã này rồi!'})
        
        # Kiểm tra ngày hết hạn
        if coupon.expires_at:
            from django.utils import timezone
            if timezone.now() > coupon.expires_at:
                return JsonResponse({'success': False, 'error': 'Mã giảm giá đã hết hạn'})
        
        # Áp dụng coupon vào order
        order.coupon = coupon
        order.save()
        
        # Tính discount
        cart_total = order.get_cart_total
        discount_amount = order.get_discount_amount
        final_total = order.get_final_total
        
        return JsonResponse({
            'success': True,
            'code': coupon.code,
            'discount_amount': discount_amount,
            'discount_percent': coupon.discount_percent if coupon.discount_percent else 0,
            'cart_total': cart_total,
            'final_total': final_total,
            'message': f'Đã áp dụng mã {code}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Dữ liệu không hợp lệ'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Lỗi: {str(e)}'})

@login_required
def remove_coupon(request):
    """API để xóa coupon khỏi order"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        order = Order.objects.filter(customer=request.user, complete=False).first()
        
        if order:
            order.coupon = None
            order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Đã xóa mã giảm giá'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Lỗi: {str(e)}'})

def couponApply(request):
    data = json.loads(request.body)
    code = data['code']

    try:
        coupon = Coupon.objects.get(code=code, is_active=True)
        # Kiểm tra ngày hết hạn
        if coupon.expires_at and coupon.expires_at < timezone.now():
            return JsonResponse({'success': False, 'error': 'Mã giảm giá đã hết hạn'})

        return JsonResponse({
            'success': True,
            'discount_amount': coupon.discount_amount,
            'discount_percent': coupon.discount_percent,
        })
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mã giảm giá không hợp lệ'})
