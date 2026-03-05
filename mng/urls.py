from django.urls import include, path
from .views import *
app_name = 'mng'

urlpatterns = [
    path('account/', account , name='account'),
    path('accounts/bulk-update/', regist_accounts , name='regist_accounts'),
    path('program/', get_program_list , name='get_program_list'),
    path('video/upload/', upload_video , name='upload_video'),
]
urls = urlpatterns