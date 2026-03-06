from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

WEEKDAYS = [
    ('mon', '월요일'),
    ('tue', '화요일'),
    ('wed', '수요일'),
    ('thu', '목요일'),
    ('fri', '금요일'),
    ('sat', '토요일'),
    ('sun', '일요일'),
]

def validate_weekdays(value):
    if isinstance(value, list) and 'all' in value:  # ← ["all"] 허용
        return
    if not isinstance(value, list):
        raise ValidationError('리스트여야 합니다.')
    for v in value:
        if v not in dict(WEEKDAYS):
            raise ValidationError(f'잘못된 요일: {v}')

class Organization(models.Model):
    """조직"""
    ORG_TYPE = [
        ('OG01', '한국교육과정평가원'),
        ('OG02', '표집학교'),
        ('OG03', '교육부'),
        ('OG04', '시도교육청'),
    ]
    name = models.CharField(max_length=100, db_comment='기관명')        # 기관명
    org_type = models.CharField(max_length=10, choices=ORG_TYPE, db_comment='기관유형')  # 기관유형
    use_yn = models.BooleanField(default=True, db_comment='사용 여부')
    reg_dt = models.DateTimeField(auto_now_add=True, db_comment='등록일시')
    mod_dt = models.DateTimeField(auto_now=True, db_comment='수정일시')
    
    class Meta:
        db_table = 'tb_organization'


class User(AbstractUser):
    """사용자계정"""
    # 계정의 삭제 상태는 AbstractUser의 is_active 필드로 관리 (True: 활성, False: 비활성)
    AUTH_TYPE = [ # 엑셀 내 사용자 유형 통해 권한 구분
        ('AT01', '사이트관리자'),
        ('AT02', '모든권한'),
        ('AT03', '업무담당자'),
        ('AT04', '감독교사'),
        ('AT05', 'ICT담당자'),
    ]
    username = None  # 기본 username 제거
    USERNAME_FIELD = 'account_id' # 로그인 식별자를 account_id로
    REQUIRED_FIELDS = []
    auth_type = models.CharField(max_length=20, choices=AUTH_TYPE, db_comment='사용자 권한')
    account_id = models.CharField(max_length=20, unique=True, db_comment='사용자 계정')
    viewing_day = models.JSONField(blank=True, default=list, validators=[validate_weekdays], db_comment='시청 가능 일자') # 시청 가능 일자 (YYYY-MM-DD)
    name = models.CharField(max_length=50, blank=True, db_comment='사용자 이름')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, db_comment='소속 기관')
    reg_dt = models.DateTimeField(auto_now_add=True, db_comment='등록일시')
    mod_dt = models.DateTimeField(auto_now=True, db_comment='수정일시')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'tb_user'