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
        size = request.POST.get('size', 'M')  # Lấy size từ request
        
        if not product_id:
            return JsonResponse({'success': False, 'error': 'Thiếu product_id'})

        product = Product.objects.get(id=product_id)
        order, _ = Order.objects.get_or_create(customer=request.user, complete=False)
        
        # Kiểm tra xem đã có OrderItem với cùng product và size chưa
        order_item, created = OrderItem.objects.get_or_create(
            order=order, 
            product=product,
            size=size
        )

        if created:
            order_item.quantity = quantity
        else:
            order_item.quantity += quantity

        order_item.save()

        return JsonResponse({
            'success': True,
            'cartItems': order.get_cart_items,
            'cartTotal': order.get_cart_total,
            'message': f'Đã thêm {product.name} (Size {size}) vào giỏ hàng!',
        })

    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Sản phẩm không tồn tại'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Lỗi: {str(e)}'})

@csrf_exempt
def updateItem(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Vui lòng đăng nhập'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        item_id = data.get('itemId')
        action = data.get('action')

        if not item_id or not action:
            return JsonResponse({'success': False, 'error': 'Thiếu thông tin'})

        # Lấy OrderItem theo ID và đảm bảo thuộc về user hiện tại
        orderItem = OrderItem.objects.get(id=item_id, order__customer=request.user, order__complete=False)

        if action == 'add':
            orderItem.quantity += 1
            orderItem.save()
        elif action == 'remove':
            orderItem.quantity -= 1
            if orderItem.quantity <= 0:
                orderItem.delete()
                return JsonResponse({
                    'success': True,
                    'deleted': True,
                    'cartItems': orderItem.order.get_cart_items,
                    'cartTotal': orderItem.order.get_cart_total,
                    'message': 'Đã xóa sản phẩm khỏi giỏ hàng'
                })
            else:
                orderItem.save()
        elif action == 'delete':
            order = orderItem.order
            orderItem.delete()
            return JsonResponse({
                'success': True,
                'deleted': True,
                'cartItems': order.get_cart_items,
                'cartTotal': order.get_cart_total,
                'message': 'Đã xóa sản phẩm khỏi giỏ hàng'
            })
        else:
            return JsonResponse({'success': False, 'error': 'Action không hợp lệ'})

        return JsonResponse({
            'success': True,
            'quantity': orderItem.quantity,
            'cartItems': orderItem.order.get_cart_items,
            'cartTotal': orderItem.order.get_cart_total,
            'message': 'Đã cập nhật giỏ hàng'
        })

    except OrderItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Sản phẩm không tồn tại trong giỏ hàng'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Lỗi: {str(e)}'})

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
