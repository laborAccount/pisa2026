import os
from django.http import Http404, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from user.models import User
from video.models import Program, Video, VideoProgress
from django.db import transaction, connection
import subprocess
import ffmpeg
import logging
import json
import math
import traceback
from datetime import datetime
# Create your views here.
logger = logging.getLogger(__name__)
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
    try:
        program = Program.objects.get(id=program_id)
        video = get_object_or_404(Video, program=program, use_yn=1)
        progress = VideoProgress.objects.filter(user=request.user, video=video).first()
        
        context['video_id'] = video.id
        context['ext'] = video.ext
        context['duration'] = video.duration
        context['last_position'] = progress.last_position if progress else 0
        context['watched_section'] = progress.watched_section if progress else []
        context['is_completed'] = progress.is_completed if progress else False
        context['completed_at'] = progress.completed_at if progress else ''
        
        return JsonResponse(context)
    except Exception as e:
        trace_back = traceback.format_exc()
        logger.info("===== Error Raise "+request.path+"====")
        logger.info(trace_back + "\n\n")
        context['status'] = 'fail'
        context['msg'] = e.message
        context['self_path'] = request.path
        return JsonResponse(context)

@login_required(login_url='/')
def watch_video(request, video_id):
    context = {}
    try:
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
    
    except Exception as e:
        trace_back = traceback.format_exc()
        logger.info("===== Error Raise "+request.path+"====")
        logger.info(trace_back + "\n\n")
        context['status'] = 'fail'
        context['msg'] = e.message
        context['self_path'] = request.path
        return JsonResponse(context)
    
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
    context = {}
    try:
        body = json.loads(request.body)
        
        user = request.user
        video = get_object_or_404(Video, id=body.get('video_id'), use_yn=True)
        position = body.get('position') #last_position
        section = body.get('section') # watched_section
        logger.info("video >>> %s", video)
        logger.info("video duration >>> %s", video.duration)
        logger.info("position >>> %s", position)
        logger.info("section >>> %s", section)
        with transaction.atomic():
            video_progress, created = VideoProgress.objects.get_or_create(
                video=video,
                user=user,
                defaults={
                    'last_position': position,
                    'watched_section': [section],
                }
            )
            
            logger.info("video_progress created >>> %s", created)
            
            if not created:
                # 기존 sections에 현재 section 추가 (중복 제거)
                sections = set(video_progress.watched_section or [])
                sections.add(section)
                video_progress.watched_section = sorted(list(sections))
                video_progress.last_position = position
                video_progress.save()
            
            # is_completed 계산
            cal_complete_min = math.floor(video.duration / 60 * 9 / 10)
            watched_section = set(video_progress.watched_section)
            complete_watched_section = set(range(1,cal_complete_min+1))
            logger.info("complete_watched_section >>> %s", complete_watched_section)
            logger.info("watched_section >>> %s", watched_section)
            
            if watched_section.issuperset(complete_watched_section) :
                video_progress.is_completed = True
                video_progress.completed_at = datetime.now()
                video_progress.save()
            
        logger.info("video progress watched_section >>> %s", video_progress.watched_section)
        return JsonResponse(context)
    except Exception as e:
        trace_back = traceback.format_exc()
        logger.info("===== Error Raise "+request.path+"====")
        logger.info(trace_back + "\n\n")
        context['status'] = 'fail'
        context['msg'] = e.message
        context['self_path'] = request.path
        return JsonResponse(context)