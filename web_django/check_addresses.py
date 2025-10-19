import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web1.settings')
django.setup()

from authentication.models import Address
from django.contrib.auth.models import User

print("=" * 60)
print("KIỂM TRA ĐỊA CHỈ TRONG DATABASE")
print("=" * 60)

total = Address.objects.count()
print(f"\n📊 Tổng số địa chỉ: {total}")

if total > 0:
    print("\n📍 Danh sách địa chỉ:")
    for addr in Address.objects.all():
        print(f"  - ID: {addr.id}")
        print(f"    User: {addr.user.username}")
        print(f"    Full name: {addr.full_name}")
        print(f"    Phone: {addr.phone}")
        print(f"    Address: {addr.get_full_address()}")
        print(f"    Is default: {addr.is_default}")
        print()
else:
    print("\n⚠️  KHÔNG CÓ ĐỊA CHỈ NÀO TRONG DATABASE!")

print("\n👥 Danh sách users:")
for user in User.objects.all():
    count = Address.objects.filter(user=user).count()
    print(f"  - {user.username}: {count} địa chỉ")

print("=" * 60)
