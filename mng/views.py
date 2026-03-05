from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.files import File
from settings import settings
from user.models import *
from common.models import *
from video.models import *
from django.db import transaction, connection
import os
import json
import re as regexp
import numpy as np
import pandas as pd
import logging
import traceback
import ffmpeg
import uuid
WEEKDAY_MAP = {
    '월': 'mon',
    '화': 'tue',
    '수': 'wed',
    '목': 'thu',
    '금': 'fri',
    '토': 'sat',
    '일': 'sun',
    '모든요일': 'all',
}

# Create your views here.
logger = logging.getLogger(__name__)
def account(request):
    context = {}
    auth = Code.objects.filter(group_code='001',order__gte=3).order_by('order').values()
    context['auth'] = list(auth)
    logger.info('context >>> %s', context)
    return render(request, 'account.html', context)


# 엑셀 파일로 사용자 일괄 등록
def regist_accounts(request):
    context = {}
    try:
        if request.method == 'POST':
            uploaded_file = request.FILES.get('file')
            if uploaded_file:
                _, ext = os.path.splitext(uploaded_file.name.lower())
                if ext not in ('.xls', '.xlsx'):
                    return JsonResponse({'error': '지원하지 않는 파일 형식입니다.'}, status=400)

                if ext == '.xls':
                    df = pd.read_excel(uploaded_file, engine='xlrd')
                elif ext == '.xlsx':
                    df = pd.read_excel(uploaded_file)
                # convert all NaN to Python None for later JSON/DB handling
                # also replace via numpy in case pandas kept nan during to_dict
                df = df.replace({np.nan: None})
                
                # Process the DataFrame as needed (e.g., convert to list of dictionaries)
                accounts_data = df.to_dict(orient='records')
                with transaction.atomic(): 
                    # 1. 조직 정보 수집 dict
                    org_map = {}  # {(name, org_type): Organization 객체}
                    for account in accounts_data:
                        account_id = account.get('아이디')
                        account_pw = account.get('비밀번호')
                        ko_auth_type = account.get('사용자 유형') # 평가원 담당자(모든권한) / 업무 담당자(학교책임자) / 감독교사 / ICT 담당자
                        ko_role =  account.get('지역/시도') # 교육부 / 시.도교육청 / 한국교육과정평가원 / 지역[서울,부산,..] (표집학교)
                        viewing_day = account.get('시청 요일') # 월,화,수
                        organazation_name = account.get('학교/부서') # 기관명
                        
                        ko_role = account.get('지역/시도')
                        # 조직역할
                        if ko_role == '한국교육과정평가원':
                            role = 'OG01'
                        elif ko_role == '교육부':
                            role = 'OG03'
                        elif ko_role == '시도교육청':
                            role = 'OG04'
                        elif ko_role is None : # 시스템 관리자
                            if account_id == 'admin':
                                role = None
                            else :
                                raise Exception('지역/시도 정보가 없습니다.')
                        else : 
                            role = 'OG02' # 지역명으로 들어오는 경우는 표집학교로 간주
                        
                        if organazation_name and role:
                            key = (organazation_name, role)
                            if key not in org_map:
                                org_map[key] = Organization(name=organazation_name, org_type=role)
                    
                    print("org_map >>>", org_map)
                    
                    # 조직 bulk create 전에 기존 DB 조회
                    existing_orgs = Organization.objects.filter(
                        name__in=[key[0] for key in org_map.keys()],
                        org_type__in=[key[1] for key in org_map.keys()]
                    )
                    
                    # 기존 조직 lookup에 먼저 셋팅
                    org_lookup = {}
                    for org in existing_orgs:
                        org_lookup[(org.name, org.org_type)] = org
                    
                    # 기존에 없는 것만 필터링해서 bulk_create
                    new_orgs = [
                        org for key, org in org_map.items() if key not in org_lookup
                    ]
                    
                    # 조직 bulk create
                    if new_orgs:
                        created_orgs = Organization.objects.bulk_create(new_orgs)
                        # 새로 생성된 것도 org_lookup에 추가
                        for org in created_orgs:
                            org_lookup[(org.name, org.org_type)] = org
                    
                    # 2.사용자 정보 셋팅
                    bulk_accounts = []
                    
                    # 기존 등록된 account_id 조회
                    existing_account_ids = set(
                        User.objects.filter(
                            account_id__in=[account.get('아이디') for account in accounts_data]
                        ).values_list('account_id', flat=True)
                    )
                    
                    for account in accounts_data:
                        
                        account_id = account.get('아이디')
                        if account_id in existing_account_ids: # 이미 존재하는 계정 스킵
                            continue
                        
                        account_pw = account.get('비밀번호')
                        ko_auth_type = account.get('사용자 유형') # 평가원 담당자(모든권한) / 업무 담당자(학교책임자) / 감독교사 / ICT 담당자
                        ko_role =  account.get('지역/시도') # 교육부 / 시.도교육청 / 한국교육과정평가원 / 지역[서울,부산,..] (표집학교)
                        viewing_day = account.get('시청 요일') # 월,화,수
                        organazation_name = account.get('학교/부서') # 기관명
                        
                        # print("account_id >>>", account_id)
                        # print("account_pw >>>", account_pw)
                        # print("auth_type >>>", ko_auth_type)
                        # print("ko_role >>>", ko_role)
                        # print("viewing_day >>>", viewing_day)
                        # print("organazation_name >>>", organazation_name)
                        # print("=================================")
                        
                        # 권한 유형
                        if ko_auth_type == '모든권한':
                            auth_type = 'AT02'
                        elif ko_auth_type == '학교책임자': # 업무담당자
                            auth_type = 'AT03'
                        elif ko_auth_type == '감독교사':
                            auth_type = 'AT04'
                        elif ko_auth_type == 'ICT 담당자':
                            auth_type = 'AT05'
                        else :
                            if account_id == 'admin':
                                auth_type = 'AT01' # 사이트관리자
                            else :
                                raise Exception('사용자 유형 정보가 없습니다.')
                        
                        # 조직역할
                        if ko_role == '한국교육과정평가원':
                            role = 'OG01'
                        elif ko_role == '교육부':
                            role = 'OG03'
                        elif ko_role == '시도교육청':
                            role = 'OG04'
                        elif ko_role is None : # 시스템 관리자
                            if account_id == 'admin':
                                role = None
                            else :
                                raise Exception('지역/시도 정보가 없습니다.')
                        else : 
                            role = 'OG02' # 지역명으로 들어오는 경우는 표집학교로 간주
                        
                        # 시청 요일
                        if viewing_day:
                            tmp_viewing_day = [day.strip() for day in viewing_day.split(',')]
                            viewing_day_list = [WEEKDAY_MAP.get(day, day) for day in tmp_viewing_day]
                        else:
                            if account_id == 'admin':
                                viewing_day_list = []
                            else:
                                raise Exception('시청 요일 정보가 없습니다.')

                        # 기관정보셋팅
                        organization = org_lookup.get((organazation_name, role)) if organazation_name and role else None
                            
                        # 사용자 정보 셋팅
                        user = User(account_id=account_id)
                        user.set_password(account_pw)
                        user.auth_type = auth_type
                        user.viewing_day = viewing_day_list
                        user.name = account_pw # 사용자이름이 패스워드(합의)
                        user.organization = organization
                        bulk_accounts.append(user)
                        
                    # Bulk create organizations first to get their IDs
                    print("bulk_accounts >>>", bulk_accounts)
                    User.objects.bulk_create(bulk_accounts)
            
            context['status'] = 'success'        
            return JsonResponse(context)
        
    except Exception as e:
        trace_back = traceback.format_exc()
        logger.info("===== Error Raise "+request.path+"====")
        logger.info(trace_back + "\n\n")
        context['status'] = 'fail'
        context['msg'] = e.message
        context['self_path'] = request.path
        return JsonResponse(context)
    

# 프로그램에 해당하는 video 업로드
def upload_video(request):
    context = {}
    try:
        if request.method == 'POST':
            uploaded_file = request.FILES.get('file')
            auth_type = request.POST.get('auth_type')
            program_id = request.POST.get('program')
            logger.info("upload video auth_type >>> %s", auth_type)
            logger.info("upload video program_id >>> %s", program_id)
            
            with transaction.atomic():
                if uploaded_file:
                    origin_file_name, ext = os.path.splitext(uploaded_file.name.lower())
                    if ext not in ('.mp4', '.avi'):
                        context['status'] = 'fail'
                        context['msg'] = '지원하지 않는 파일 형식입니다.'
                        return JsonResponse(context)
                    
                    # 존재하는 권한의 프로그램 동영상인지 확인
                    existing_video = Video.objects.filter(program_id=program_id, use_yn=True) # 프로그램에 해당하는 video가 존재하는지 확인 (프로그램ID로 video 검색)
                    if existing_video.exists():
                        existing_video = existing_video.first()
                        existing_video.use_yn = False
                        existing_video.save()
                        existing_file_path = os.path.join(existing_video.file_path, existing_video.server_file_name + existing_video.ext)
                        if os.path.exists(existing_file_path) : # 기존 파일이 존재하는 경우 삭제
                            os.remove(existing_file_path)
                    
                    # UUID(서버 파일명)
                    server_file_name = str(uuid.uuid4())
                    # 저장 경로
                    file_path = os.path.join(settings.VIDEO_ROOT, auth_type, program_id)
                    os.makedirs(file_path, exist_ok=True) # 디렉토리 없으면 생성
                    save_path = os.path.join(settings.VIDEO_ROOT, auth_type, program_id, server_file_name + ext)
                    # 파일 저장
                    with open(save_path, 'wb') as f:
                        for chunk in uploaded_file.chunks():
                            f.write(chunk)
                    # ffmpeg로 메타정보 추출
                    probe = ffmpeg.probe(save_path)
                    # video 스트림 META
                    # video_stream['width']       # 가로 해상도 (예: 1920)
                    # video_stream['height']      # 세로 해상도 (예: 1080)
                    # video_stream['codec_name']  # 코덱 (예: h264)
                    # video_stream['r_frame_rate'] # 프레임레이트 (예: 30/1)
                    # video_stream['bit_rate']    # 비트레이트
                    # video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
                    duration = int(float(probe['format']['duration']))
                    file_size = int(probe['format']['size'])
                    # Video 저장
                    program = Program.objects.get(id=program_id)
                    Video.objects.create(
                        program=program,
                        file_path=file_path,
                        origin_file_name=origin_file_name,
                        server_file_name=server_file_name,
                        ext=ext,
                        duration=duration,
                        file_size=file_size,
                    )

                else:
                    context['status'] = 'fail'
                    context['msg'] = '파일이 업로드되지 않았습니다.'
                    return JsonResponse(context)

            context['status'] = 'success'
            return JsonResponse(context)
    except Exception as e:
        trace_back = traceback.format_exc()
        logger.info("===== Error Raise "+request.path+"====")
        logger.info(trace_back + "\n\n")
        context['status'] = 'fail'
        context['msg'] = e.message
        context['self_path'] = request.path
        return JsonResponse(context)

# 관리자 권한 Select시 Program list 정보
def get_program_list(request):
    context = {}
    try:
        if request.method == 'GET':
            video_role = request.GET.get('video_role')
            programs = Program.objects.filter(video_role=video_role, use_yn=True).order_by('order').values()
            context['programs'] = list(programs)
            return JsonResponse(context)
    except Exception as e:
        trace_back = traceback.format_exc()
        logger.info("===== Error Raise "+request.path+"====")
        logger.info(trace_back + "\n\n")
        context['status'] = 'fail'
        context['msg'] = e.message
        context['self_path'] = request.path
        return JsonResponse(context)