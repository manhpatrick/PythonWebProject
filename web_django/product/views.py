from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from order.models import Order, OrderItem
from authentication.models import Address
from .models import Product, Category
import json
# Create your views here.
def main(request):
    sort_by = request.GET.get('sort', 'newest')  # Đổi default thành 'newest' thay vì ''
    
    # Lấy products và apply sort TRƯỚC KHI phân trang
    products = Product.objects.all()
    
    if sort_by == "popular":
        products = products.order_by('-rating')  # Bỏ dấu ngoặc kép ở -'rating'
    elif sort_by == "newest":
        products = products.order_by('-id')  # Thêm dấu - để id giảm dần (mới nhất)
    elif sort_by == "best_selling":
        products = products.order_by('-sold_number')  # Bỏ dấu ngoặc kép
    elif sort_by == "price_asc":  # Sửa lỗi đánh máy 'acs' -> 'asc'
        products = products.order_by('new_price')
    elif sort_by == "price_desc":  # Sửa 'des' -> 'desc'
        products = products.order_by('-new_price')  # Bỏ dấu ngoặc kép
    else:
        products = products.order_by('-id')  # Default sort
    
    paginator = Paginator(products, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    if request.user.is_authenticated:
        order, _ = Order.objects.get_or_create(customer=request.user, complete=False)
        items = order.orderitem_set.all()
    else:
        items = []
    
    # Render stars cho products trong page hiện tại
    for p in page_obj:
        p.stars_html = render_stars_home(p.rating)
    
    categories = Category.objects.all()
    
    return render(request, 'index.html', {
        "page_obj": page_obj,
        "categories": categories,
        'current_sort': sort_by,
        "items": items,

    })

def get_product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    data = {
        'id': product.id,
        'name': product.name,
        'old_price': product.old_price,
        'new_price': product.new_price,
        'discount_percent': product.discount_percent,
        'sold_number': product.sold_number,
        'rating': product.rating,
        'image': product.imageURL,
        'country': product.country,
        'brand': product.brand,
        'detail': product.detail,
        'available_sizes': product.available_sizes
    }
    return JsonResponse(data)
def render_stars_home(rating):
    full_stars = int(rating)
    has_half_star = rating - full_stars >= 0.5
    stars_html = ""
    for i in range(1, 6):
        if i <= full_stars:
            stars_html += '<i class="fa-solid fa-star"></i>'
        elif i == full_stars + 1 and has_half_star:
            stars_html += '<i class="fa-solid fa-star-half-stroke"></i>'
        else:
            stars_html += '<i class="fa-regular fa-star"></i>'
    return stars_html
def cart_item(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'partials/cart_item.html', {'product': product})

def category(request, slug):
    category = get_object_or_404(Category, slug=slug)
    
    # Lấy sort parameter
    sort_by = request.GET.get('sort', 'newest')
    
    # Lọc sản phẩm theo danh mục
    products = Product.objects.filter(category=category)

    # Áp dụng sort trước khi phân trang
    if sort_by == "popular":
        products = products.order_by('-rating')
    elif sort_by == "newest":
        products = products.order_by('-id')
    elif sort_by == "best_selling":
        products = products.order_by('-sold_number')
    elif sort_by == "price_asc":
        products = products.order_by('new_price')
    elif sort_by == "price_desc":
        products = products.order_by('-new_price')
    else:
        products = products.order_by('-id')  # default sort

    # Phân trang
    paginator = Paginator(products, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    if request.user.is_authenticated:
        order, _ = Order.objects.get_or_create(customer=request.user, complete=False)
        items = order.orderitem_set.all()
    else:
        items = []

    # Render stars cho sản phẩm trong page hiện tại
    for p in page_obj:
        p.stars_html = render_stars_home(p.rating)

    categories = Category.objects.all()

    return render(request, 'index.html', {
        'category': category,
        'categories': categories,
        'page_obj': page_obj,
        'current_sort': sort_by,
        "items":items,
    })

def search(request):
    searched = request.GET.get("searched", "")
    sort_by = request.GET.get('sort', 'newest')
    keys = Product.objects.none()
    no_results = False

    if searched:
        keys = Product.objects.filter(name__icontains=searched)
        
        # Apply sorting to search results
        if sort_by == "popular":
            keys = keys.order_by('-rating')
        elif sort_by == "newest":
            keys = keys.order_by('-id')
        elif sort_by == "best_selling":
            keys = keys.order_by('-sold_number')
        elif sort_by == "price_asc":
            keys = keys.order_by('new_price')
        elif sort_by == "price_desc":
            keys = keys.order_by('-new_price')
        else:
            keys = keys.order_by('-id')
        
        if not keys.exists():
            no_results = True
    
    # Pagination for search results
    paginator = Paginator(keys, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Gắn sao cho products
    for p in page_obj:
        p.stars_html = render_stars_home(p.rating)
    
    if request.user.is_authenticated:
        order, _ = Order.objects.get_or_create(customer=request.user, complete=False)
        items = order.orderitem_set.all()
    else:
        items = []

    categories = Category.objects.all()
    context = {
        "searched": searched,
        "page_obj": page_obj,
        "categories": categories,
        "no_results": no_results,
        "items": items,
        "current_sort": sort_by,
    }
    return render(request, "index.html", context)

@login_required(login_url='signin')
def profile(request):
    try:
        # Giỏ hàng hiện tại (chưa hoàn tất)
        current_order, _ = Order.objects.get_or_create(customer=request.user, complete=False)
        cart_items = current_order.orderitem_set.all()
        
        # Lịch sử đơn hàng đã hoàn tất
        completed_orders = Order.objects.filter(customer=request.user, complete=True).order_by('-date_ordered')
        
        # Địa chỉ của user
        addresses = Address.objects.filter(user=request.user)
        
        context = {
            'user': request.user,
            'order': current_order,
            'items': cart_items,
            'cart_total': current_order.get_cart_total,
            'cart_count': current_order.get_cart_items,
            'completed_orders': completed_orders,
            'addresses': addresses,
            # Thêm alias cho consistency với authentication view
            'current_order': current_order,
            'current_items': cart_items,
        }
        return render(request, 'profile.html', context)
    except Exception as e:
        print(f"Error in profile view: {e}")
        context = {
            'user': request.user,
            'items': [],
            'order': {'get_cart_total': 0, 'get_cart_items': 0},
            'cart_total': 0,
            'cart_count': 0,
            'completed_orders': [],
            'addresses': [],
            'current_order': None,
            'current_items': [],
        }
        return render(request, 'profile.html', context)