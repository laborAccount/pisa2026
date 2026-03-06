from django.urls import include, path
from .views import *
app_name = 'mng'

urlpatterns = [
    path('account/', account , name='account'),
    path('accounts/bulk-update/', regist_accounts , name='regist_accounts'),
    path('accounts/', get_account_list , name='get_account_list'),
    path('program/', get_program_list , name='get_program_list'),
    path('video/upload/', upload_video , name='upload_video'),
    path('accounts/delete/', delete_accounts , name='delete_accounts'),

]
urls = urlpatterns