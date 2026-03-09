from django.urls import include, path
from .views import *
app_name = 'video'

urlpatterns = [
    path('program/', program , name='program'),
    path('meta/<int:program_id>/', get_video_meta, name='get_video_meta'),
    path('watch/<int:video_id>/', watch_video , name='watch_video'),
    path('progress/save/', save_progress, name='save_progress'),
]
urls = urlpatterns