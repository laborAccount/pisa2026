from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from user.models import User
from video.models import Program, Video, VideoProgress
# Create your views here.
@login_required(login_url='/')
def program(request):
    context = {}
    user = request.user
    if user.auth_type in ['AT01', 'AT02']:
        programs = Program.objects.filter(use_yn=True).order_by('order')
        context['programs'] = programs
        
    else :
        programs = Program.objects.filter(video_role=user.auth_type, use_yn=True).order_by('order')
        context['programs'] = programs

    return render(request, 'program_page.html', context)

