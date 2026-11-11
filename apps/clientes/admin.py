from django.contrib import admin
from .models import *
for model in [obj for obj in globals().values() if isinstance(obj, type) and hasattr(obj, "_meta") and getattr(obj, "__module__", "").startswith("apps.")]:
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass
