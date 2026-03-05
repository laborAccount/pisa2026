from django.db import models

class Code(models.Model):
    """공통 코드"""
    code = models.CharField(max_length=10,db_comment='코드 값')     # 'UT01', 'UT02', 'UT03', 'UT04' [User]/ 'OG01', 'OG02', 'OG03', 'OG04' [Organization] / 'AT01', 'AT02', 'AT03', 'AT04' 'AT05'[AUTH]
    group_code = models.CharField(max_length=10, db_comment='그룹 코드') 
    name = models.CharField(max_length=100, db_comment='코드명')    # '평가원 담당자', '업무 담당자', '감독교사', 'ICT 담당자' / '한국교육과정평가원', '표집학교', '교육부', '시도교육청' / '사이트관리자', '모든권한', '표집학교', '교육부', '시도교육청'
    order = models.PositiveIntegerField(default=0, db_comment='정렬 순서')  # 정렬 순서
    code_descipt = models.CharField(max_length=200, db_comment='코드 설명') # 코드 설명
    use_yn = models.BooleanField(default=True, db_comment='사용 여부')
    reg_dt = models.DateTimeField(auto_now_add=True, db_comment='등록일시')
    mod_dt = models.DateTimeField(auto_now=True, db_comment='수정일시')

    class Meta:
        db_table = 'tb_code'
        unique_together = ('group_code', 'code')
        ordering = ['group_code', 'order']
