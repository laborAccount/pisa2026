from django.db import models
from user.models import User

class Program(models.Model):
    ROLE = [
        ('AT03', '업무담당자'),
        ('AT04', '감독교사'),
        ('AT05', 'ICT담당자')
    ]
    video_role = models.CharField(max_length=10, choices=ROLE, db_comment='시청 가능 역할')
    order = models.PositiveIntegerField(db_comment='차시 순서')          # 차시 순서 (1, 2)
    title = models.CharField(max_length=200, db_comment='프로그램명')
    use_yn = models.BooleanField(default=True, db_comment='사용 여부')
    reg_dt = models.DateTimeField(auto_now_add=True, db_comment='등록일시')
    mod_dt = models.DateTimeField(auto_now=True, db_comment='수정일시')
    class Meta:
        db_table = 'tb_program'

class Video(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, null=True, db_comment='프로그램 FK')
    file_path = models.CharField(max_length=200, db_comment='파일 경로')
    origin_file_name = models.CharField(max_length=200, default='', db_comment='원본 파일명')
    server_file_name = models.CharField(max_length=200, default='', db_comment='서버 파일명')
    ext = models.CharField(max_length=20, db_comment='파일 확장자')
    duration = models.PositiveIntegerField(db_comment='총 길이 (초)')       # 총 길이 (초)
    file_size = models.BigIntegerField(db_comment='파일 크기')
    use_yn = models.BooleanField(default=True, db_comment='사용 여부')
    reg_dt = models.DateTimeField(auto_now_add=True, db_comment='등록일시')
    mod_dt = models.DateTimeField(auto_now=True, db_comment='수정일시')
    
    class Meta:
        db_table = 'tb_video'
        
        
class VideoProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_comment='사용자ID')  # 사용자
    video = models.ForeignKey(Video, on_delete=models.CASCADE, db_comment='영상ID')
    last_position = models.PositiveIntegerField(default=0, db_comment='마지막 재생 위치(초)')  # 마지막 재생 위치(초) - 드래그 대응
    watched_section = models.JSONField(default=list, db_comment='실제 시청 누적 시간 SET 정보') # 실제 시청 누적 시간 SET 정보
    is_completed = models.BooleanField(default=False, db_comment='이수 완료 여부')        # 이수 완료 여부
    completed_at = models.DateTimeField(null=True, blank=True, db_comment='이수 완료 일시')
    reg_dt = models.DateTimeField(auto_now_add=True, db_comment='등록일시')
    mod_dt = models.DateTimeField(auto_now=True, db_comment='수정일시')

    class Meta:
        db_table = 'tb_video_progress'
        unique_together = ('user', 'video')  # 유저+영상 조합은 1개만