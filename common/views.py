from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from datetime import datetime
WEEKDAY_MAP = {0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'}
# Create your views here.
def login(request):
    context = {}
    return render(request, 'login.html', context)

def do_login(request):
    context = {}
    if request.method == 'POST':
        username = request.POST.get('accountId')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            # 요일 체크
            viewing_day = user.viewing_day
            if 'all' not in viewing_day:  # all이 아니고 설정이 있을 때만 체크
                today = WEEKDAY_MAP[datetime.now().weekday()]
                if today not in viewing_day:
                    context['error'] = '오늘은 접속 가능한 요일이 아닙니다.'
                    return render(request, 'login.html', context)
            
            auth_login(request, user)  # 세션 생성
            return redirect('video:program')  # 로그인 성공 시 이동할 URL
        else:
            context['error'] = '아이디 또는 비밀번호가 올바르지 않습니다.'
            return render(request, 'login.html', context)  # 실패 시 로그인 페이지로

    return render(request, 'login.html', context)