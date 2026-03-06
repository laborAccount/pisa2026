from django.urls import include, path
from .views import *
app_name = 'video'

urlpatterns = [
    path('program/', program , name='program'),
    # path('watch/<int:program_id>/', watch_video , name='watch_video'),
]
urls = urlpatterns