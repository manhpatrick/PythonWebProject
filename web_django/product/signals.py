"""
DJANGO SIGNALS - Thay thế cho STORED PROCEDURE
Tự động cập nhật tồn kho khi có thay đổi đơn hàng
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from order.models import OrderItem, Order
from product.models import ProductInventory
from django.db import transaction


@receiver(post_save, sender=OrderItem)
def reserve_inventory_on_add_to_cart(sender, instance, created, **kwargs):
    """
    TRIGGER: Khi thêm sản phẩm vào giỏ hàng
    → Tự động GIỮ HÀNG (reserve) trong kho
    """
    if created and not instance.order.complete:
        try:
            inventory = ProductInventory.objects.get(
                product=instance.product,
                size=instance.size
            )
            inventory.reserve(instance.quantity)
            print(f"✅ Đã giữ {instance.quantity} sản phẩm {instance.product.name} size {instance.size}")
        except ProductInventory.DoesNotExist:
            print(f"⚠️ Chưa có tồn kho cho {instance.product.name} size {instance.size}")
        except ValueError as e:
            print(f"❌ Lỗi giữ hàng: {e}")


@receiver(pre_save, sender=OrderItem)
def update_inventory_on_quantity_change(sender, instance, **kwargs):
    """
    TRIGGER: Khi thay đổi số lượng trong giỏ hàng
    → Tự động cập nhật số lượng giữ
    """
    if instance.pk and not instance.order.complete:
        try:
            old_instance = OrderItem.objects.get(pk=instance.pk)
            old_quantity = old_instance.quantity
            new_quantity = instance.quantity
            
            if old_quantity != new_quantity:
                inventory = ProductInventory.objects.get(
                    product=instance.product,
                    size=instance.size
                )
                
                difference = new_quantity - old_quantity
                
                if difference > 0:
                    # Tăng số lượng → reserve thêm
                    inventory.reserve(difference)
                    print(f"➕ Tăng giữ thêm {difference} sản phẩm")
                else:
                    # Giảm số lượng → release bớt
                    inventory.release(abs(difference))
                    print(f"➖ Giảm giữ {abs(difference)} sản phẩm")
                    
        except (OrderItem.DoesNotExist, ProductInventory.DoesNotExist):
            pass


@receiver(post_delete, sender=OrderItem)
def release_inventory_on_remove_from_cart(sender, instance, **kwargs):
    """
    TRIGGER: Khi xóa sản phẩm khỏi giỏ hàng
    → Tự động TRẢ HÀNG (release) về kho
    """
    if not instance.order.complete:
        try:
            inventory = ProductInventory.objects.get(
                product=instance.product,
                size=instance.size
            )
            inventory.release(instance.quantity)
            print(f"🔄 Đã trả {instance.quantity} sản phẩm {instance.product.name} size {instance.size} về kho")
        except ProductInventory.DoesNotExist:
            print(f"⚠️ Không tìm thấy tồn kho")


@receiver(post_save, sender=Order)
def complete_sale_on_order_complete(sender, instance, **kwargs):
    """
    TRIGGER: Khi hoàn tất đơn hàng (complete = True)
    → Chuyển từ RESERVED sang SOLD
    """
    if instance.complete:
        with transaction.atomic():
            for item in instance.orderitem_set.all():
                try:
                    inventory = ProductInventory.objects.select_for_update().get(
                        product=item.product,
                        size=item.size
                    )
                    inventory.complete_sale(item.quantity)
                    print(f"✅ Đã bán {item.quantity} sản phẩm {item.product.name} size {item.size}")
                except ProductInventory.DoesNotExist:
                    print(f"⚠️ Không tìm thấy tồn kho cho {item.product.name} size {item.size}")
                except ValueError as e:
                    print(f"❌ Lỗi hoàn tất bán: {e}")
