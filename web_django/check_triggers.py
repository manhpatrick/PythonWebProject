import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web1.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
triggers = cursor.fetchall()

print("\n📋 DANH SÁCH TRIGGERS TRONG DATABASE:\n")
if triggers:
    for idx, (name,) in enumerate(triggers, 1):
        print(f"{idx}. {name}")
else:
    print("Chưa có trigger nào")
