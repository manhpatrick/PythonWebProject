"""
SQLITE TRIGGERS - Tạo trigger trực tiếp trong database
Chạy file này sau khi makemigrations và migrate
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Tạo SQLite Triggers cho quản lý tồn kho'

    def handle(self, *args, **kwargs):
        with connection.cursor() as cursor:
            
            # ============================================
            # TRIGGER 1: Tự động giữ hàng khi thêm vào giỏ
            # ============================================
            trigger_reserve = """
            CREATE TRIGGER IF NOT EXISTS trigger_reserve_inventory
            AFTER INSERT ON order_orderitem
            WHEN NEW.order_id IN (SELECT id FROM order_order WHERE complete = 0)
            BEGIN
                UPDATE product_productinventory
                SET reserved_quantity = reserved_quantity + NEW.quantity
                WHERE product_id = NEW.product_id AND size = NEW.size;
            END;
            """
            
            # ============================================
            # TRIGGER 2: Tự động trả hàng khi xóa khỏi giỏ
            # ============================================
            trigger_release = """
            CREATE TRIGGER IF NOT EXISTS trigger_release_inventory
            AFTER DELETE ON order_orderitem
            WHEN OLD.order_id IN (SELECT id FROM order_order WHERE complete = 0)
            BEGIN
                UPDATE product_productinventory
                SET reserved_quantity = reserved_quantity - OLD.quantity
                WHERE product_id = OLD.product_id AND size = OLD.size
                AND reserved_quantity >= OLD.quantity;
            END;
            """
            
            # ============================================
            # TRIGGER 3: Cập nhật khi thay đổi số lượng
            # ============================================
            trigger_update = """
            CREATE TRIGGER IF NOT EXISTS trigger_update_inventory
            AFTER UPDATE OF quantity ON order_orderitem
            WHEN NEW.order_id IN (SELECT id FROM order_order WHERE complete = 0)
            BEGIN
                UPDATE product_productinventory
                SET reserved_quantity = reserved_quantity - OLD.quantity + NEW.quantity
                WHERE product_id = NEW.product_id AND size = NEW.size;
            END;
            """
            
            # ============================================
            # TRIGGER 4: Chuyển sang sold khi hoàn tất đơn
            # ============================================
            trigger_complete = """
            CREATE TRIGGER IF NOT EXISTS trigger_complete_sale
            AFTER UPDATE OF complete ON order_order
            WHEN NEW.complete = 1 AND OLD.complete = 0
            BEGIN
                UPDATE product_productinventory
                SET 
                    reserved_quantity = reserved_quantity - (
                        SELECT COALESCE(SUM(quantity), 0) 
                        FROM order_orderitem 
                        WHERE order_id = NEW.id 
                        AND product_id = product_productinventory.product_id 
                        AND size = product_productinventory.size
                    ),
                    sold_quantity = sold_quantity + (
                        SELECT COALESCE(SUM(quantity), 0) 
                        FROM order_orderitem 
                        WHERE order_id = NEW.id 
                        AND product_id = product_productinventory.product_id 
                        AND size = product_productinventory.size
                    )
                WHERE EXISTS (
                    SELECT 1 FROM order_orderitem 
                    WHERE order_id = NEW.id 
                    AND product_id = product_productinventory.product_id
                );
            END;
            """
            
            # ============================================
            # TRIGGER 5: Kiểm tra tồn kho trước khi thêm
            # ============================================
            trigger_check = """
            CREATE TRIGGER IF NOT EXISTS trigger_check_inventory
            BEFORE INSERT ON order_orderitem
            BEGIN
                SELECT CASE
                    WHEN (
                        SELECT stock_quantity - reserved_quantity - sold_quantity
                        FROM product_productinventory
                        WHERE product_id = NEW.product_id AND size = NEW.size
                    ) < NEW.quantity
                    THEN RAISE(ABORT, 'Không đủ hàng trong kho')
                END;
            END;
            """
            
            # Thực thi tất cả triggers
            try:
                cursor.execute(trigger_reserve)
                self.stdout.write(self.style.SUCCESS('✅ Đã tạo trigger_reserve_inventory'))
                
                cursor.execute(trigger_release)
                self.stdout.write(self.style.SUCCESS('✅ Đã tạo trigger_release_inventory'))
                
                cursor.execute(trigger_update)
                self.stdout.write(self.style.SUCCESS('✅ Đã tạo trigger_update_inventory'))
                
                cursor.execute(trigger_complete)
                self.stdout.write(self.style.SUCCESS('✅ Đã tạo trigger_complete_sale'))
                
                cursor.execute(trigger_check)
                self.stdout.write(self.style.SUCCESS('✅ Đã tạo trigger_check_inventory'))
                
                self.stdout.write(self.style.SUCCESS('\n🎉 Tất cả triggers đã được tạo thành công!'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Lỗi: {e}'))
