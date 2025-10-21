from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import google.generativeai as genai
import json
import os
from product.models import Product, Category
from django.db.models import Q

# Cấu hình Gemini API
GEMINI_API_KEY = "AIzaSyBwk2b5ol5u6kN16-dpTPWapRK8QS-2Knk"  # API key mới

try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Tạo model - Gemini 2.5 Pro 
    model = genai.GenerativeModel('gemini-2.0-pro')
    print("[CHATBOT] Gemini configured successfully with gemini-2.0-pro")
except Exception as e:
    print(f"[CHATBOT ERROR] Failed to configure Gemini: {e}")
    model = None

# Lưu lịch sử chat (trong production nên dùng database)
chat_sessions = {}

def get_product_info(message, session_history=None):
    """Lấy thông tin sản phẩm từ database dựa trên câu hỏi"""
    message_lower = message.lower()
    products = Product.objects.all()
    
    response_data = {
        'type': 'text',
        'text': '',
        'products': [],
        'detailed': False  # Flag để biết có cần chi tiết không
    }
    
    # Kiểm tra xem có hỏi chi tiết về sản phẩm không
    if any(word in message_lower for word in ['chi tiết', 'chi tiet', 'thông tin', 'thong tin', 'mô tả', 'mo ta', 'về sản phẩm', 've san pham', 'sản phẩm đó', 'san pham do']):
        response_data['detailed'] = True
        # Nếu có lịch sử, tìm sản phẩm được nhắc đến gần nhất
        if session_history and len(session_history) > 0:
            # Lấy tin nhắn bot cuối cùng
            for msg in reversed(session_history):
                # Tìm tên sản phẩm trong lịch sử (giả sử có format 'Product Name')
                if "'" in msg.parts[0].text:
                    import re
                    match = re.search(r"'([^']+)'", msg.parts[0].text)
                    if match:
                        product_name = match.group(1)
                        product = products.filter(name__icontains=product_name).first()
                        if product:
                            price = product.new_price if product.new_price > 0 else product.old_price
                            old_price = product.old_price
                            discount = ((old_price - price) / old_price * 100) if price < old_price else 0
                            
                            response_data['text'] = f"Chi tiết về '{product.name}':\n\n"
                            response_data['text'] += f"Tên: {product.name}\n"
                            response_data['text'] += f"Thương hiệu: {product.brand}\n"
                            response_data['text'] += f"Xuất xứ: {product.country}\n"
                            response_data['text'] += f"Giá gốc: {old_price:,.0f}đ\n"
                            response_data['text'] += f"Giá hiện tại: {price:,.0f}đ\n"
                            if discount > 0:
                                response_data['text'] += f"Giảm giá: {discount:.0f}%\n"
                            response_data['text'] += f"\nBạn có thể xem sản phẩm này trên trang chủ hoặc đặt hàng ngay!"
                            
                            response_data['products'] = [{
                                'name': product.name,
                                'price': price,
                                'brand': product.brand,
                                'image': product.image.url if product.image else None,
                                'id': product.id
                            }]
                            return response_data
        return None  # Không tìm thấy sản phẩm trong lịch sử
    
    response_data = {
        'type': 'text',
        'text': '',
        'products': []
    }
    
    # Tìm sản phẩm đắt nhất
    if any(word in message_lower for word in ['đắt nhất', 'dat nhat', 'expensive', 'cao nhất', 'cao nhat']):
        expensive = products.order_by('-new_price').first()
        if expensive:
            price = expensive.new_price if expensive.new_price > 0 else expensive.old_price
            response_data['text'] = f"Sản phẩm đắt nhất hiện tại là '{expensive.name}' với giá {price:,.0f}đ"
            response_data['products'] = [{
                'name': expensive.name,
                'price': price,
                'brand': expensive.brand,
                'image': expensive.image.url if expensive.image else None,
                'id': expensive.id
            }]
        return response_data
    
    # Tìm sản phẩm rẻ nhất
    if any(word in message_lower for word in ['rẻ nhất', 're nhat', 'cheap', 'giảm giá', 'giam gia', 'thấp nhất', 'thap nhat']):
        # Lọc sản phẩm có giá > 0
        cheap = products.filter(new_price__gt=0).order_by('new_price').first()
        if not cheap:
            cheap = products.filter(old_price__gt=0).order_by('old_price').first()
        if cheap:
            price = cheap.new_price if cheap.new_price > 0 else cheap.old_price
            response_data['text'] = f"Sản phẩm rẻ nhất là '{cheap.name}' chỉ {price:,.0f}đ"
            response_data['products'] = [{
                'name': cheap.name,
                'price': price,
                'brand': cheap.brand,
                'image': cheap.image.url if cheap.image else None,
                'id': cheap.id
            }]
        return response_data
    
    # Tìm theo brand
    brands = ['puma', 'nike', 'adidas', 'akka']
    for brand in brands:
        if brand in message_lower:
            brand_products = products.filter(brand__icontains=brand)[:5]
            if brand_products:
                product_list = []
                for p in brand_products:
                    price = p.new_price if p.new_price > 0 else p.old_price
                    product_list.append({
                        'name': p.name,
                        'price': price,
                        'brand': p.brand,
                        'image': p.image.url if p.image else None,
                        'id': p.id
                    })
                response_data['text'] = f"Chúng tôi có {brand_products.count()} sản phẩm {brand.upper()}:"
                response_data['products'] = product_list
            return response_data
    
    # Liệt kê tất cả sản phẩm
    if any(word in message_lower for word in ['có gì', 'co gi', 'sản phẩm', 'san pham', 'list', 'danh sách', 'danh sach']):
        all_products = products[:8]
        if all_products:
            product_list = []
            for p in all_products:
                price = p.new_price if p.new_price > 0 else p.old_price
                product_list.append({
                    'name': p.name,
                    'price': price,
                    'brand': p.brand,
                    'image': p.image.url if p.image else None,
                    'id': p.id
                })
            response_data['text'] = f"Chúng tôi có {products.count()} sản phẩm. Dưới đây là một số sản phẩm nổi bật:"
            response_data['products'] = product_list
        return response_data
    
    # Top 5 giày
    if any(word in message_lower for word in ['giày', 'giay', 'shoe']):
        shoes = products.filter(Q(name__icontains='giày') | Q(name__icontains='giay'))[:5]
        if shoes:
            product_list = []
            for p in shoes:
                price = p.new_price if p.new_price > 0 else p.old_price
                product_list.append({
                    'name': p.name,
                    'price': price,
                    'brand': p.brand,
                    'image': p.image.url if p.image else None,
                    'id': p.id
                })
            response_data['text'] = f"Chúng tôi có {shoes.count()} loại giày thể thao:"
            response_data['products'] = product_list
        return response_data
    
    return None

def format_product_response(product_data):
    """Format response với thông tin sản phẩm"""
    if not product_data or not product_data['products']:
        return None
    
    text = product_data['text'] + "\n\n"
    for i, p in enumerate(product_data['products'], 1):
        text += f"{i}. {p['name']}\n"
        text += f"   Giá: {p['price']:,.0f}đ | Thương hiệu: {p['brand']}\n\n"
    
    text += "Bạn muốn xem chi tiết sản phẩm nào?"
    return text

@csrf_exempt
def chat(request):
    """API endpoint cho chatbot"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        if model is None:
            return JsonResponse({
                'success': False,
                'error': 'Chatbot chưa được cấu hình. Vui lòng kiểm tra API key!'
            }, status=500)
            
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        print(f"[CHATBOT] Received message: {message}")
        
        if not message:
            return JsonResponse({'success': False, 'error': 'Message is required'}, status=400)
        
        # Lấy hoặc tạo chat session
        if session_id not in chat_sessions:
            print(f"[CHATBOT] Creating new session: {session_id}")
            chat_sessions[session_id] = model.start_chat(history=[])
        
        chat = chat_sessions[session_id]
        
        # Thêm context về cửa hàng
        context = """Bạn là trợ lý AI thông minh cho cửa hàng đồ thể thao trực tuyến. 
        Cửa hàng bán các sản phẩm: giày thể thao (Puma, Nike, Adidas), áo thể thao, quần short, phụ kiện thể thao.
        Hãy trả lời câu hỏi của khách hàng một cách thân thiện, hữu ích và chuyên nghiệp.
        Nếu khách hỏi về sản phẩm, giá cả, giao hàng, thanh toán thì hãy trả lời dựa trên thông tin của cửa hàng thể thao.
        Trả lời bằng tiếng Việt và ngắn gọn.
        
        Câu hỏi của khách hàng: """
        
        # Gửi message đến Gemini
        print(f"[CHATBOT] Sending to Gemini...")
        
        # Kiểm tra xem có cần thông tin từ database không
        # Truyền lịch sử chat để AI hiểu context
        product_info = get_product_info(message, chat.history if hasattr(chat, 'history') else None)
        
        if product_info and product_info['products']:
            # Có thông tin sản phẩm từ database
            if product_info.get('detailed'):
                # Trả về chi tiết sản phẩm
                reply_text = product_info['text']
            else:
                # Format danh sách sản phẩm
                reply_text = format_product_response(product_info)
            print(f"[CHATBOT] Response from database: {len(product_info['products'])} products")
        else:
            # Không có sản phẩm cụ thể, dùng AI
            try:
                # Thêm context với thông tin tổng quan
                total_products = Product.objects.count()
                brands = Product.objects.values_list('brand', flat=True).distinct()
                
                enhanced_context = f"""Bạn là trợ lý AI thông minh cho cửa hàng đồ thể thao trực tuyến. 
                
                THÔNG TIN CỬA HÀNG:
                - Tổng số sản phẩm: {total_products}
                - Các thương hiệu: {', '.join(brands)}
                - Sản phẩm: giày thể thao, áo thể thao, quần short, phụ kiện
                - Giao hàng: 2-3 ngày (nội thành), 3-5 ngày (ngoại thành)
                - Thanh toán: COD, chuyển khoản, ví điện tử
                - Freeship cho đơn hàng trên 500.000đ
                
                Hãy trả lời câu hỏi của khách hàng một cách thân thiện, hữu ích và chuyên nghiệp.
                Trả lời bằng tiếng Việt, ngắn gọn và súc tích.
                Nếu khách hỏi về sản phẩm cụ thể, khuyến khích họ hỏi chi tiết hơn.
                
                Câu hỏi của khách hàng: """
                
                response = chat.send_message(enhanced_context + message)
                reply_text = response.text
                print(f"[CHATBOT] Response from Gemini AI")
            except Exception as api_error:
                print(f"[CHATBOT API ERROR] {str(api_error)}")
                
                # Fallback response thông minh dựa trên từ khóa
                message_lower = message.lower()
                
                if any(word in message_lower for word in ['giá', 'gia', 'bao nhiêu', 'cost', 'price']):
                    reply_text = "Giá sản phẩm của chúng tôi rất đa dạng:\n- Giày thể thao: 500.000đ - 5.000.000đ\n- Áo thể thao: 200.000đ - 800.000đ\n- Quần short: 150.000đ - 500.000đ\n\nBạn muốn xem loại sản phẩm nào? Hãy hỏi tôi về 'sản phẩm đắt nhất', 'sản phẩm rẻ nhất', hoặc 'giày Puma'!"
                elif any(word in message_lower for word in ['giao hàng', 'ship', 'delivery', 'van chuyen']):
                    reply_text = "Chúng tôi có dịch vụ giao hàng toàn quốc:\n- Nội thành: 2-3 ngày\n- Ngoại thành: 3-5 ngày\n- Phí ship: 30.000đ\nFreeship cho đơn hàng trên 500.000đ!"
                elif any(word in message_lower for word in ['thanh toán', 'payment', 'pay']):
                    reply_text = "Chúng tôi hỗ trợ nhiều hình thức thanh toán:\n- COD (Thanh toán khi nhận hàng)\n- Chuyển khoản ngân hàng\n- Ví điện tử (Momo, ZaloPay)\nBạn muốn thanh toán theo hình thức nào?"
                elif any(word in message_lower for word in ['hello', 'hi', 'chào', 'xin chào']):
                    reply_text = "Xin chào! Tôi là trợ lý AI của cửa hàng đồ thể thao.\n\nTôi có thể giúp bạn:\n- Tìm sản phẩm đắt nhất / rẻ nhất\n- Xem danh sách sản phẩm\n- Tìm theo thương hiệu (Puma, Nike, Adidas)\n- Tư vấn giá cả, giao hàng\n\nHãy thử hỏi: 'Sản phẩm đắt nhất là gì?' hoặc 'Có những giày Puma nào?'"
                else:
                    reply_text = f"Cửa hàng có {total_products} sản phẩm thể thao!\n\nBạn có thể hỏi tôi:\n- 'Sản phẩm đắt nhất là gì?'\n- 'Sản phẩm rẻ nhất?'\n- 'Có giày Puma nào?'\n- 'Liệt kê sản phẩm'\n\nBạn muốn tìm gì?"
        
        return JsonResponse({
            'success': True,
            'reply': reply_text,
            'session_id': session_id
        })
        
    except Exception as e:
        print(f"[CHATBOT ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'error': f'Xin lỗi, đã có lỗi xảy ra: {str(e)}'
        }, status=500)

@csrf_exempt
def clear_chat(request):
    """Xóa lịch sử chat"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id', 'default')
        
        if session_id in chat_sessions:
            del chat_sessions[session_id]
        
        return JsonResponse({'success': True, 'message': 'Chat cleared'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
