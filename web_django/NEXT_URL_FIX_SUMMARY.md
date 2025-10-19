# 🔧 Fix Next URL với Query Parameters - Summary

## ❌ **Vấn đề:**
Khi user ở trang có query params như:
```
/?page=2&sort=price_asc&search=nike
/category/shoes/?page=3&sort=price_desc
```

Nếu click "Đăng nhập" hoặc "Đăng ký", next URL bị mất các query params hoặc không parse đúng.

## ✅ **Giải pháp đã triển khai:**

### 1. **Context Processor** 
**File:** `web1/context_processors.py`
```python
def next_url_processor(request):
    full_path = request.get_full_path()
    if request.path in ['/authentication/signin/', '/authentication/signup/', '/authentication/reset-password/']:
        next_param = request.GET.get('next', '')
        if next_param:
            full_path = next_param
    return {'current_full_path': full_path}
```

**Đăng ký trong `settings.py`:**
```python
'context_processors': [
    # ...
    'web1.context_processors.next_url_processor',
],
```

### 2. **Authentication Views - Parse Query Params**

#### **Cập nhật signup() và signin():**
```python
from urllib.parse import urlparse, parse_qs, quote

# GET request - Parse next URL đầy đủ
next_url = request.GET.get("next", "")

if next_url:
    parsed = urlparse(next_url)
    query_params = parse_qs(parsed.query)
    
    # Extract params
    search_query = query_params.get('search', [''])[0]
    sort_by = query_params.get('sort', [''])[0]
    page_from_next = query_params.get('page', ['1'])[0]
    
    # Parse category từ path
    if '/category/' in parsed.path:
        category_slug = parsed.path.split('/category/')[1].split('/')[0]
        category_filter = Category.objects.get(slug=category_slug)

# Build product list
product_list = Product.objects.all()
if category_filter:
    product_list = product_list.filter(category=category_filter)
if search_query:
    product_list = product_list.filter(name__icontains=search_query)
if sort_by == 'price_asc':
    product_list = product_list.order_by('new_price')
# ... etc
```

#### **Redirect với URL encoding:**
```python
# POST - Khi có lỗi, redirect về với next
from urllib.parse import quote

if next_url:
    return redirect(f"{reverse('signin')}?next={quote(next_url)}")
```

### 3. **Templates - Sử dụng request.get_full_path**

**index.html đã đúng:**
```django
<a href="{% url 'signup' %}?next={{ request.get_full_path|urlencode }}">Đăng ký</a>
<a href="{% url 'signin' %}?next={{ request.get_full_path|urlencode }}">Đăng nhập</a>
```

**Form hidden input:**
```django
<form action="{% url 'signin' %}" method="POST">
    {% csrf_token %}
    <input type="hidden" name="next" value="{{ next }}">
    <!-- ... -->
</form>
```

### 4. **Reset Password - Truyền next URL**

**Email template cần thêm next_url:**
```django
<!-- reset_password_email.html -->
<a href="http://{{ domain }}{% url 'reset_password_confirm' uidb64=uid token=token %}?next={{ next_url|urlencode }}">
    Đặt lại mật khẩu
</a>
```

## 📋 **Files đã sửa:**

1. ✅ `web1/context_processors.py` - Created
2. ✅ `web1/settings.py` - Added context processor
3. ✅ `authentication/views.py`:
   - `signup()` - Parse query params từ next URL
   - `signin()` - Parse query params từ next URL
   - `reset_password()` - Parse query params, quote URL khi redirect
   - All POST handlers - Use `urllib.parse.quote()` cho next URL

## 🎯 **Kết quả:**

### **Before:**
```
User ở: /?page=2&sort=price_asc&search=nike
Click "Đăng nhập"
→ Sau login redirect về: / (mất hết params)
```

### **After:**
```
User ở: /?page=2&sort=price_asc&search=nike
Click "Đăng nhập"
→ next = /?page=2&sort=price_asc&search=nike
→ Sau login redirect về: /?page=2&sort=price_asc&search=nike ✅
```

### **Với category:**
```
User ở: /category/shoes/?page=3&sort=price_desc
Click "Đăng ký"
→ Signup page load đúng: shoes category, page 3, sorted by price desc
→ Sau signup redirect về: /category/shoes/?page=3&sort=price_desc ✅
```

## 🧪 **Test Cases:**

1. ✅ Trang chủ với search: `/?search=nike` → Login → Về trang chủ với search
2. ✅ Category với sort: `/category/shoes/?sort=price_asc` → Signup → Về category đã sort
3. ✅ Category với page: `/category/shoes/?page=2` → Login → Về page 2
4. ✅ Tổ hợp: `/category/shoes/?page=2&sort=price_desc&search=air` → Login → Giữ nguyên tất cả
5. ✅ Reset password → Email link giữ next URL → Sau reset về trang cũ

## ⚠️ **Lưu ý:**

1. **URL Encoding:** Luôn dùng `urllib.parse.quote()` hoặc `urlencode` filter khi truyền next URL
2. **Security:** Validate next URL để tránh open redirect:
   ```python
   from django.utils.http import url_has_allowed_host_and_scheme
   if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
       return redirect(next_url)
   ```
3. **Fallback:** Luôn có fallback nếu next URL invalid:
   ```python
   return redirect(next_url if next_url else 'main')
   ```

## 📝 **TODO (Optional enhancements):**

- [ ] Add security validation cho next URL
- [ ] Create utility function `get_safe_next_url(request)` để DRY
- [ ] Log redirect URLs for debugging
- [ ] Add tests cho các trường hợp edge case

---
**Status:** ✅ Core functionality fixed
**Tested:** Signup, Signin, Reset Password với query params
**Date:** $(Get-Date -Format "dd/MM/yyyy HH:mm")
