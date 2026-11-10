from django.contrib import admin
from django.urls import path

from chat.views import chat_view, reset_view, health_view

urlpatterns = [
    path("health/", health_view, name="health"),
    path("admin/", admin.site.urls),
    path("", chat_view, name="chat"),
    path("reset/", reset_view, name="reset"),
]
