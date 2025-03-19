from django.urls import path
from .views import ChatView, receive_message


urlpatterns = [
    path(
        "",  ChatView.as_view(template_name="app_chat.html"), name="index",
    ),
    path(
       "api/chat/", receive_message, name="receive_message",
    ),
]
