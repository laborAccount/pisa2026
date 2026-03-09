import os
from django.http import Http404, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from user.models import User
from video.models import Program, Video, VideoProgress

import subprocess
import ffmpeg
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

@login_required(login_url='/')
def get_video_meta(request, program_id):
    context = {}
    program = Program.objects.get(id=program_id)
    video = get_object_or_404(Video, program=program, use_yn=1)
    progress = VideoProgress.objects.filter(user=request.user, video=video).first()
    
    context['video_id'] = video.id
    context['ext'] = video.ext
    context['progress'] = progress
    context['duration'] = video.duration
    context['last_position'] = progress.last_position if progress else 0
    context['watched_section'] = progress.watched_section if progress else []
    context['is_completed'] = progress.is_completed if progress else False
    return JsonResponse(context)


def watch_video(request, video_id):
    context = {}
    video = get_object_or_404(Video, id=video_id, use_yn=True)
    file_path = os.path.join(video.file_path, video.server_file_name+video.ext)
    if not os.path.exists(file_path):
        raise Http404("Video file not found.")
    
    ext = video.ext.lower()
    file_size = os.path.getsize(file_path)
    range_header = request.META.get('HTTP_RANGE', '').strip()
    
    start, end = 0, file_size - 1
    status = 200
    
    if range_header:
        range_val = range_header.replace('bytes=', '').split('-')
        start = int(range_val[0])
        end = int(range_val[1]) if range_val[1] else file_size - 1
        status = 206
        
    response = StreamingHttpResponse(
        file_iterator(file_path, start, end),
        content_type='video/mp4',
        status=status,
    )
    response['Content-Length'] = end - start + 1
    response['Accept-Ranges'] = 'bytes'
    
    if status == 206:
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        
    return response

def file_iterator(path, start, end, chunk=8192):
    with open(path, 'rb') as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining:
            data = f.read(min(chunk, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data

def save_progress(request):
    try:
        user = request.user
        video = get_object_or_404(Video, id=request.POST.get('video_id'), use_yn=True)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)