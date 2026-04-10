"""
regime_classifier.py - 레짐 유형 분류기

공산주의·왕조·허울뿐인 민주주의 탐지.
이름이 아닌 실질 지표로 분류.

레짐 유형:
  LIBERAL_DEMOCRACY     - 자유민주주의
  ELECTORAL_DEMOCRACY   - 선거민주주의 (절차는 있으나 자유 제한)
  DECLINING_REPUBLIC    - 후퇴 중인 공화국 (헝가리, 미국 일부 지표)
  DEMOCRATIC_FACADE     - 민주주의 껍데기 (중국, 러시아, 북한)
  CONSTITUTIONAL_MONARCHY - 입헌군주제 (영국, 스웨덴)
  ABSOLUTE_MONARCHY     - 절대군주제 (사우디, UAE)
  COMMUNIST_STATE       - 일당 공산주의 국가
  HYBRID_REGIME         - 경쟁적 권위주의 (터키, 베네수엘라)
  FAILED_STATE          - 국가 기능 붕괴
  WAR_STATE             - 전쟁으로 거버넌스 심각 훼손
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RegimeProfile:
    iso3: str
    country: str
    regime_type: str
    regime_label_ko: str

    # 공화주의 원칙 5개 차원 (0~100)
    rpi_separation_of_powers: float   # 권력분립
    rpi_term_limits: float            # 임기 제한 준수
    rpi_constitutional_supremacy: float  # 헌법 우위
    rpi_decentralization: float       # 분권화·연방제
    rpi_political_competition: float  # 정치적 경쟁 허용
    rpi_total: float                  # RPI 종합

    # 파사드 지수 (0~100, 높을수록 허울이 강함)
    facade_score: float
    facade_evidence: list             # 파사드 근거

    # 군주제 특성
    is_monarchy: bool
    monarchy_type: Optional[str]      # CONSTITUTIONAL / ABSOLUTE / NONE
    head_of_state_type: str           # ELECTED / HEREDITARY / PARTY_APPOINTED / MILITARY

    # 분쟁 왜곡
    active_conflict: bool
    conflict_intensity: float         # 0~100
    conflict_distortion: float        # 지표 왜곡 정도 (0~100)
    conflict_notes: str

    # 이름 vs 실체 괴리
    name_claims_democracy: bool       # 국가명에 민주주의·인민·공화국 포함
    name_claims_republic: bool
    name_reality_gap: float           # 이름-실체 괴리 점수 (높을수록 허울)

    # 분석 메모
    analyst_notes: str


# ─────────────────────────────────────────────
#  레짐 데이터베이스 (1차 공개 자료 기반)
#  출처: V-Dem, Freedom House, CIA World Factbook,
#        IDEA, International Crisis Group
# ─────────────────────────────────────────────

REGIME_DB: dict[str, RegimeProfile] = {}

def _r(iso3, country, regime_type, regime_label_ko,
        sep, term, const, decent, comp,
        facade, facade_ev,
        is_mon, mon_type, hos_type,
        conflict, c_intensity, c_distort, c_notes,
        name_dem, name_rep, name_gap,
        notes):
    rpi = round(sep*0.25 + term*0.20 + const*0.25 + decent*0.15 + comp*0.15, 1)
    REGIME_DB[iso3] = RegimeProfile(
        iso3=iso3, country=country,
        regime_type=regime_type, regime_label_ko=regime_label_ko,
        rpi_separation_of_powers=sep,
        rpi_term_limits=term,
        rpi_constitutional_supremacy=const,
        rpi_decentralization=decent,
        rpi_political_competition=comp,
        rpi_total=rpi,
        facade_score=facade, facade_evidence=facade_ev,
        is_monarchy=is_mon, monarchy_type=mon_type,
        head_of_state_type=hos_type,
        active_conflict=conflict,
        conflict_intensity=c_intensity,
        conflict_distortion=c_distort,
        conflict_notes=c_notes,
        name_claims_democracy=name_dem,
        name_claims_republic=name_rep,
        name_reality_gap=name_gap,
        analyst_notes=notes,
    )

# ── 자유민주주의 ──────────────────────────────

_r("SWE","Sweden","CONSTITUTIONAL_MONARCHY","입헌군주·자유민주",
   sep=92,term=85,const=94,decent=82,comp=96,
   facade=2,facade_ev=[],
   is_mon=True,mon_type="CONSTITUTIONAL",hos_type="HEREDITARY",
   conflict=False,c_intensity=0,c_distort=0,c_notes="",
   name_dem=False,name_rep=False,name_gap=0,
   notes="군주는 의례적 역할. 실질 권력은 의회. 권력분립 최상위권.")

_r("DEU","Germany","LIBERAL_DEMOCRACY","자유민주공화국",
   sep=90,term=88,const=92,decent=88,comp=92,
   facade=3,facade_ev=[],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=False,c_intensity=0,c_distort=0,c_notes="",
   name_dem=False,name_rep=False,name_gap=0,
   notes="연방제+비례대표+위헌정당 해산 제도. 역사적 교훈 반영된 헌법설계.")

_r("CAN","Canada","CONSTITUTIONAL_MONARCHY","입헌군주·자유민주",
   sep=86,term=82,const=88,decent=85,comp=90,
   facade=3,facade_ev=[],
   is_mon=True,mon_type="CONSTITUTIONAL",hos_type="HEREDITARY",
   conflict=False,c_intensity=0,c_distort=0,c_notes="",
   name_dem=False,name_rep=False,name_gap=0,
   notes="영연방 입헌군주제. 영왕은 명목상 국가원수. 실질 민주주의 강함.")

_r("AUS","Australia","CONSTITUTIONAL_MONARCHY","입헌군주·연방민주",
   sep=85,term=80,const=87,decent=88,comp=89,
   facade=4,facade_ev=[],
   is_mon=True,mon_type="CONSTITUTIONAL",hos_type="HEREDITARY",
   conflict=False,c_intensity=0,c_distort=0,c_notes="",
   name_dem=False,name_rep=False,name_gap=0,
   notes="의무투표제. 연방제 강함. 원주민 권리 미해결 과제.")

_r("FRA","France","LIBERAL_DEMOCRACY","반대통령제 공화국",
   sep=80,term=84,const=85,decent=62,comp=86,
   facade=5,facade_ev=["대통령 행정권 집중 경향"],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=False,c_intensity=0,c_distort=0,c_notes="",
   name_dem=False,name_rep=True,name_gap=5,
   notes="5공화국 반대통령제. 행정권이 대통령에 상대적으로 집중. 헌법위원회 독립적.")

_r("JPN","Japan","CONSTITUTIONAL_MONARCHY","입헌군주·의원내각제",
   sep=82,term=78,const=89,decent=60,comp=78,
   facade=8,facade_ev=["자민당 70년 장기집권","중앙집권 경향"],
   is_mon=True,mon_type="CONSTITUTIONAL",hos_type="HEREDITARY",
   conflict=False,c_intensity=0,c_distort=0,c_notes="",
   name_dem=False,name_rep=False,name_gap=0,
   notes="평화헌법 9조. 천황은 상징. 자민당 준독점 구조가 다원성 제한.")

_r("GBR","United Kingdom","CONSTITUTIONAL_MONARCHY","입헌군주·의원내각제",
   sep=82,term=75,const=80,decent=70,comp=84,
   facade=6,facade_ev=["불문헌법 취약성","상원 비선출"],
   is_mon=True,mon_type="CONSTITUTIONAL",hos_type="HEREDITARY",
   conflict=False,c_intensity=0,c_distort=0,c_notes="",
   name_dem=False,name_rep=False,name_gap=0,
   notes="불문헌법 국가. 의회주권 원칙. 상원 세습귀족 문제. Brexit 후 민주주의 기관 긴장.")

_r("KOR","South Korea","LIBERAL_DEMOCRACY","대통령제 공화국",
   sep=78,term=90,const=82,decent=65,comp=80,
   facade=8,facade_ev=["검찰 정치화 우려","계엄 시도 (2024)"],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=False,c_intensity=5,c_distort=8,c_notes="2024년 12월 비상계엄 시도 — 헌법재판소 탄핵 인용",
   name_dem=False,name_rep=True,name_gap=10,
   notes="5년 단임 대통령제. 2024년 계엄 시도는 공화주의 원칙 중대 위협 사례.")

_r("CHL","Chile","LIBERAL_DEMOCRACY","대통령제 공화국",
   sep=76,term=80,const=78,decent=68,comp=82,
   facade=6,facade_ev=[],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=False,c_intensity=0,c_distort=0,c_notes="",
   name_dem=False,name_rep=True,name_gap=4,
   notes="피노체트 헌법 개정 시도 중. 민주주의 회복 후 공고화 단계.")

# ── 쇠퇴 중인 공화국 ──────────────────────────

_r("USA","United States","DECLINING_REPUBLIC","쇠퇴 중인 공화국",
   sep=70,term=72,const=68,decent=78,comp=65,
   facade=22,facade_ev=[
       "선거인단 제도 → 득표 역전 가능",
       "대법원 정치화 (임명 구조)",
       "의회 기능 마비 반복",
       "Citizens United → 자본의 정치 지배",
       "게리맨더링 구조화",
       "2021.1.6 의회 점거 사건",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=False,c_intensity=10,c_distort=12,
   c_notes="이란·이스라엘 분쟁 개입, 우크라이나 지원 — 국내 정치 왜곡 요인",
   name_dem=False,name_rep=False,name_gap=15,
   notes="Republic이라는 단어를 국가명에 쓰지 않으나 공화주의 창시 국가. "
         "현재 공화주의 원칙 침식 가속 중. '민주주의'를 내세우나 구조적 왜곡 심화.")

_r("POL","Poland","DECLINING_REPUBLIC","회복 중인 공화국",
   sep=62,term=75,const=58,decent=70,comp=72,
   facade=18,facade_ev=[
       "PiS 집권기(2015~2023) 사법부 장악",
       "헌법재판소 구성 편향",
       "공영방송 통제",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=False,c_intensity=5,c_distort=5,c_notes="우크라이나 인접 — 안보 긴장이 국내 정치 압박",
   name_dem=False,name_rep=True,name_gap=20,
   notes="2023년 정권 교체 후 회복 시도 중. 사법 독립성 복원 진행 중.")

_r("HUN","Hungary","DECLINING_REPUBLIC","선거 권위주의",
   sep=30,term=45,const=28,decent=35,comp=35,
   facade=55,facade_ev=[
       "오르반 집권 후 헌법 개정 → 권력 집중",
       "독립 언론 거의 소멸",
       "선거구 게리맨더링",
       "대법원·선거위원회 장악",
       "NGO 탄압 (소로스 법)",
       "나토·EU 내 친러 행보",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=False,c_intensity=5,c_distort=10,c_notes="우크라이나 전쟁 외교 중재 시도",
   name_dem=False,name_rep=True,name_gap=55,
   notes="선거는 열리나 공정 경쟁 불가능. Fareed Zakaria '비자유민주주의' 개념의 원형.")

# ── 하이브리드·권위주의 ──────────────────────

_r("TUR","Turkey","HYBRID_REGIME","선거 권위주의",
   sep=28,term=40,const=25,decent=30,comp=32,
   facade=60,facade_ev=[
       "에르도안 대통령제 개헌 (2017) → 권력 집중",
       "쿠르드 야당 의원 면책특권 박탈",
       "언론인 수감 세계 최다 수준",
       "2016 쿠데타 이후 대규모 숙청",
       "사법부 행정부 종속",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=True,c_intensity=45,c_distort=35,
   c_notes="쿠르드 반군(PKK)과 교전 지속. 시리아 군사 개입. NATO 회원이나 러시아와 협력",
   name_dem=False,name_rep=True,name_gap=60,
   notes="1923년 공화국 수립. 아타튀르크 세속 공화주의에서 이슬람 민족주의 권위주의로 전환.")

_r("BRA","Brazil","HYBRID_REGIME","불안정 공화국",
   sep=55,term=60,const=50,decent=65,comp=60,
   facade=30,facade_ev=[
       "볼소나로 집권기 군부 의존",
       "선거 불복 시도 (2022)",
       "아마존 토착민 권리 침해",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=False,c_intensity=8,c_distort=5,c_notes="내부 치안 불안 (마약 카르텔)",
   name_dem=False,name_rep=True,name_gap=25,
   notes="2022 선거 불복 사태. 군부 영향력 잔존. 룰라 재집권 후 민주주의 회복 시도 중.")

_r("IND","India","HYBRID_REGIME","다수결 민주주의",
   sep=55,term=72,const=52,decent=55,comp=58,
   facade=32,facade_ev=[
       "모디 집권 후 무슬림 소수자 권리 축소",
       "CAA (시민권법 개정) 종교 차별 논란",
       "언론인 표적 수사",
       "선거위원회 독립성 약화 우려",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=True,c_intensity=22,c_distort=15,
   c_notes="카슈미르 분쟁 지속. 파키스탄·중국과 국경 긴장. 마오이스트 내부 분쟁",
   name_dem=False,name_rep=True,name_gap=28,
   notes="세계 최대 민주주의. 그러나 BJP 집권 후 소수자 보호·언론 자유 후퇴.")

_r("MEX","Mexico","HYBRID_REGIME","불완전 민주주의",
   sep=42,term=65,const=40,decent=50,comp=55,
   facade=40,facade_ev=[
       "모레나 당 사법부 개혁 → 판사 직선제 도입",
       "카르텔의 선거 개입",
       "언론인 살해 세계 최다 수준",
       "군부 경찰 임무 확대",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=True,c_intensity=40,c_distort=30,
   c_notes="마약 카르텔과 사실상 내전 상태. 언론인·정치인 암살 지속",
   name_dem=False,name_rep=True,name_gap=38,
   notes="AMLO·클라우디아 샤인바움 집권 후 사법 장악 시도. 카르텔이 실효적 영토 지배.")

_r("ARG","Argentina","HYBRID_REGIME","불안정 공화국",
   sep=60,term=65,const=55,decent=62,comp=68,
   facade=22,facade_ev=[
       "밀레이 집권 후 의회 우회 행정명령 남발",
       "경제 위기 → 민주주의 기관 압박",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=False,c_intensity=2,c_distort=2,c_notes="",
   name_dem=False,name_rep=True,name_gap=18,
   notes="반복적 경제 위기가 민주주의 기관 안정성 훼손. 밀레이 충격 요법 경과 관찰 중.")

_r("NGA","Nigeria","HYBRID_REGIME","불안정 연방",
   sep=38,term=55,const=35,decent=40,comp=42,
   facade=45,facade_ev=[
       "선거 폭력 일상화",
       "군부 개입 역사",
       "보코하람 점령 지역 통치 공백",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=True,c_intensity=55,c_distort=45,
   c_notes="보코하람·ISWAP 북동부 통제. 납치경제. 분리독립 운동(IPOB). 목동-농민 충돌",
   name_dem=False,name_rep=True,name_gap=40,
   notes="아프리카 최대 인구 국가. 선거는 치러지나 공정성·안전 심각 문제.")

_r("ZAF","South Africa","HYBRID_REGIME","약화 중인 민주주의",
   sep=60,term=65,const=62,decent=55,comp=64,
   facade=20,facade_ev=[
       "ANC 30년 집권 → 내부 부패",
       "주마 집권기 국가 포획(State Capture)",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=False,c_intensity=8,c_distort=5,c_notes="갱단 폭력, 파업 진압",
   name_dem=False,name_rep=True,name_gap=15,
   notes="2024 총선 ANC 과반 실패 → 연립정부. 포스트-아파르트헤이트 민주주의 시험대.")

_r("SGP","Singapore","HYBRID_REGIME","관리된 민주주의",
   sep=45,term=50,const=52,decent=30,comp=35,
   facade=42,facade_ev=[
       "PAP 60년 집권",
       "선거법이 야당에 불리하게 설계",
       "언론 국가 통제",
       "명예훼손 소송으로 야당 탄압",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=False,c_intensity=0,c_distort=0,c_notes="",
   name_dem=False,name_rep=True,name_gap=38,
   notes="경제적 번영 + 청렴 + 법치 → 고성능 권위주의. 실질 정치 경쟁 없음.")

_r("IDN","Indonesia","ELECTORAL_DEMOCRACY","선거 민주주의",
   sep=58,term=70,const=55,decent=60,comp=62,
   facade=25,facade_ev=[
       "군부의 사업 참여 허용",
       "올리가르키 지배",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=False,c_intensity=10,c_distort=5,c_notes="파푸아 분리독립 운동 저강도 분쟁",
   name_dem=False,name_rep=True,name_gap=20,
   notes="1998 민주화 이후 빠른 성장. 군부 개혁 미완. 프라보워 대통령 취임(2024) 후 방향 주목.")

# ── 민주주의 파사드 ──────────────────────────

_r("RUS","Russia","DEMOCRATIC_FACADE","권위주의 파사드",
   sep=8,term=5,const=5,decent=10,comp=5,
   facade=92,facade_ev=[
       "푸틴 24년+ 집권 (임기 개헌으로 연장)",
       "실질 야당 없음 (나발니 옥사)",
       "선거 결과 사전 결정",
       "독립 언론 전면 금지",
       "반전 시위대 수천 명 구금",
       "'러시아 연방' 명칭이나 실질은 중앙집권 권위주의",
   ],
   is_mon=False,mon_type=None,hos_type="PARTY_APPOINTED",
   conflict=True,c_intensity=90,c_distort=85,
   c_notes="2022~ 우크라이나 전면 침공. 계엄령·동원령. 점령지 선거 조작. 전쟁이 모든 민주주의 지표 무력화",
   name_dem=False,name_rep=True,name_gap=90,
   notes="공식명: 러시아 연방(Российская Федерация). "
         "연방제·공화국을 명목상 표방하나 실질은 1인 권위주의. "
         "전쟁 중 민주주의 지표 자체가 의미 없는 상태.")

_r("CHN","China","COMMUNIST_STATE","공산당 일당 독재",
   sep=3,term=2,const=2,decent=5,comp=2,
   facade=96,facade_ev=[
       "중화인민공화국 — '인민' '공화국' 모두 허울",
       "시진핑 임기 제한 폐지 (2018 헌법 개정)",
       "전인대 99.9% 찬성률 → 의회 형식화",
       "공산당이 국가·군·사법·언론 전면 통제",
       "독립 노조·종교단체·시민사회 금지",
       "홍콩 자치 소멸 (2020 국가보안법)",
       "신장 위구르 구금 캠프",
   ],
   is_mon=False,mon_type=None,hos_type="PARTY_APPOINTED",
   conflict=True,c_intensity=35,c_distort=30,
   c_notes="대만 해협 군사 긴장 고조. 남중국해 분쟁. 미국과 패권 경쟁",
   name_dem=True,name_rep=True,name_gap=98,
   notes="국가명: 中华人民共和国. '人民'·'共和国' 모두 사용하나 "
         "1949년 이후 공산당 일당 지배 변화 없음. "
         "명칭-실체 괴리 지수 최상위.")

_r("EGY","Egypt","DEMOCRATIC_FACADE","군사 권위주의",
   sep=10,term=8,const=8,decent=12,comp=10,
   facade=88,facade_ev=[
       "시시 군부 쿠데타(2013) 후 집권",
       "2019 헌법 개정 → 임기 연장",
       "야당·NGO·언론인 대규모 구금",
       "시나이 반도 군사 통제",
   ],
   is_mon=False,mon_type=None,hos_type="MILITARY",
   conflict=True,c_intensity=40,c_distort=38,
   c_notes="이스라엘-하마스 전쟁으로 가자 국경 위기. 시나이 IS 분파 활동. 리비아 불안정 영향",
   name_dem=False,name_rep=True,name_gap=85,
   notes="아랍의 봄 이후 군사 쿠데타로 민주주의 완전 역전. "
         "이집트 아랍 공화국 — 공화국 명칭이나 실질 군사 독재.")

# ── 분쟁 당사국 ──────────────────────────────

_r("UKR","Ukraine","ELECTORAL_DEMOCRACY","전시 민주주의",
   sep=52,term=65,const=50,decent=58,comp=60,
   facade=18,facade_ev=[
       "전시 야당 활동 제한",
       "미디어 통합(전시 단일방송)",
       "젤렌스키 전시 권한 집중",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=True,c_intensity=92,c_distort=75,
   c_notes="러시아 전면 침공(2022~). 국토 20% 점령. 계엄령 하 선거 연기. "
           "전시 미디어 통합은 민주주의 기준 적용 왜곡 요인. "
           "민주주의 지표를 평시와 동일 기준 적용 불가.",
   name_dem=False,name_rep=False,name_gap=15,
   notes="침략 전쟁 피해국. 전시 민주주의 제한은 침략의 결과이지 원인이 아님. "
         "전쟁 전 민주주의 개혁 진행 중이었음. 전후 복구 후 재평가 필요.")

_r("ISR","Israel","ELECTORAL_DEMOCRACY","분쟁 민주주의",
   sep=58,term=70,const=45,decent=40,comp=68,
   facade=28,facade_ev=[
       "사법부 개혁 시도 (2023) → 의회 주권 강화 = 견제 약화",
       "아랍계 이스라엘인 2등 시민 논란",
       "점령지(서안·가자) 팔레스타인인 무투표",
       "극우 연정 의존 구조",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",
   conflict=True,c_intensity=88,c_distort=70,
   c_notes="가자 전쟁(2023.10~). 헤즈볼라·이란 미사일 교환. 예멘 후티 공격. "
           "전시 내각·긴급명령으로 민주주의 기관 우회. "
           "국제사법재판소 제소(집단학살 혐의) — 법치 지표 왜곡 요인",
   name_dem=False,name_rep=False,name_gap=25,
   notes="유일한 중동 민주주의로 분류되나 점령지 통치는 민주주의 외부. "
         "전쟁 중 사법 독립성 공격이 겹쳐 복합 위기.")

_r("IRN","Iran","DEMOCRATIC_FACADE","신정 권위주의",
   sep=8,term=10,const=6,decent=8,comp=8,
   facade=90,facade_ev=[
       "이슬람 최고지도자(하메네이)가 선출직 위에 군림",
       "수호위원회가 후보 자격 박탈 → 선거 결과 사전 결정",
       "시위대 대규모 처형 (마흐사 아미니 시위 2022)",
       "이슬람 공화국 — 공화국 명칭 사용",
   ],
   is_mon=False,mon_type=None,hos_type="PARTY_APPOINTED",
   conflict=True,c_intensity=65,c_distort=60,
   c_notes="이스라엘에 탄도미사일 직접 공격(2024). 하마스·헤즈볼라·후티 지원. "
           "핵 프로그램 → 미국·이스라엘과 긴장. 내부 시위 지속 진압",
   name_dem=False,name_rep=True,name_gap=88,
   notes="이슬람 혁명(1979) 이후 신정 공화제. 선거는 형식적으로 존재하나 "
         "이슬람 원칙 수호자가 모든 결정 최종 통제.")

# ── 왕조 ─────────────────────────────────────

_r("SAU","Saudi Arabia","ABSOLUTE_MONARCHY","절대 왕정",
   sep=2,term=0,const=2,decent=5,comp=2,
   facade=15,facade_ev=[
       "파이살 왕가 세습 지배",
       "MBS 반부패 숙청 = 경쟁자 제거",
       "여성 운전 허용 등 부분 개혁 = 안전밸브",
   ],
   is_mon=True,mon_type="ABSOLUTE",hos_type="HEREDITARY",
   conflict=True,c_intensity=30,c_distort=20,
   c_notes="예멘 내전 개입(2015~). 후티 드론 공격. 이란과 갈등",
   name_dem=False,name_rep=False,name_gap=5,
   notes="코란이 헌법. 의회 없음(자문위원회 Majlis). "
         "석유 수익으로 정치 안정 유지. 민주주의 지표 적용 자체가 부적절.")

_r("ARE","United Arab Emirates","ABSOLUTE_MONARCHY","연방 절대군주제",
   sep=5,term=0,const=4,decent=15,comp=3,
   facade=18,facade_ev=[
       "7개 토후국 세습 지배자 연합",
       "국적자 12% — 외국인 88% 무권리",
       "형식적 연방국회(FNC) 비선출",
   ],
   is_mon=True,mon_type="ABSOLUTE",hos_type="HEREDITARY",
   conflict=False,c_intensity=5,c_distort=3,c_notes="예멘 개입 축소. 이스라엘 아브라함 협정",
   name_dem=False,name_rep=False,name_gap=5,
   notes="경제 허브이나 정치 자유 없음. 이주노동자 카팔라 시스템 인권 우려.")

# ── 기타 ─────────────────────────────────────

_r("PRK","North Korea","COMMUNIST_STATE","전체주의 왕조",
   sep=0,term=0,const=0,decent=0,comp=0,
   facade=99,facade_ev=[
       "조선민주주의인민공화국 — '민주주의'·'인민'·'공화국' 모두 허울",
       "김일성→김정일→김정은 3대 세습",
       "99.9% 단일후보 선거",
       "정치범 수용소 22만 명",
       "인터넷·여행·언론 완전 통제",
   ],
   is_mon=False,mon_type=None,hos_type="HEREDITARY",  # 사실상 왕조
   conflict=True,c_intensity=40,c_distort=40,
   c_notes="ICBM·핵실험. 러시아에 무기 지원. 한국과 기술적 전쟁 상태",
   name_dem=True,name_rep=True,name_gap=100,
   notes="국가명에 민주주의+인민+공화국 모두 포함하는 세계 최악의 명칭-실체 괴리. "
         "세습 독재를 '인민민주주의'로 포장.")

_r("CUB","Cuba","COMMUNIST_STATE","공산당 일당 독재",
   sep=5,term=8,const=4,decent=8,comp=3,
   facade=88,facade_ev=[
       "쿠바 공화국 → 1959년 이후 공산당 독재",
       "카스트로 세습 (피델→라울)",
       "반정부 시위 강경 진압 (2021)",
   ],
   is_mon=False,mon_type=None,hos_type="PARTY_APPOINTED",
   conflict=False,c_intensity=5,c_distort=3,c_notes="경제 봉쇄·식량난 위기",
   name_dem=False,name_rep=True,name_gap=82,
   notes="1901년 공화국 → 1959년 혁명 후 공산 독재. 경제난으로 대규모 이민 지속.")

_r("VEN","Venezuela","DEMOCRATIC_FACADE","선거 권위주의",
   sep=10,term=8,const=8,decent=12,comp=10,
   facade=85,facade_ev=[
       "마두로 2024 선거 결과 조작 (야당 압승 → 역전 선포)",
       "야당 후보 수감·망명",
       "선거위원회 행정부 통제",
       "군부 충성 매수 구조",
   ],
   is_mon=False,mon_type=None,hos_type="ELECTED",  # 명목상
   conflict=False,c_intensity=15,c_distort=12,c_notes="게릴라·갱단 통제 지역 존재",
   name_dem=False,name_rep=True,name_gap=83,
   notes="볼리바르 혁명 → 차베스→마두로 권위주의 공고화. "
         "2024 선거 결과 조작으로 민주주의 파사드도 사실상 제거.")


# ─────────────────────────────────────────────
#  조회 헬퍼
# ─────────────────────────────────────────────

def get_regime(iso3: str) -> Optional[RegimeProfile]:
    return REGIME_DB.get(iso3)

def get_all_regimes() -> list[RegimeProfile]:
    return list(REGIME_DB.values())

REGIME_TYPE_LABELS = {
    "LIBERAL_DEMOCRACY":      "자유민주주의",
    "CONSTITUTIONAL_MONARCHY": "입헌군주·민주",
    "ELECTORAL_DEMOCRACY":    "선거민주주의",
    "DECLINING_REPUBLIC":     "쇠퇴 공화국",
    "HYBRID_REGIME":          "혼합 권위주의",
    "DEMOCRATIC_FACADE":      "민주주의 파사드",
    "COMMUNIST_STATE":        "공산당 독재",
    "ABSOLUTE_MONARCHY":      "절대 왕정",
    "FAILED_STATE":           "실패 국가",
    "WAR_STATE":              "전시 국가",
}

REGIME_COLORS = {
    "LIBERAL_DEMOCRACY":       "#16a34a",
    "CONSTITUTIONAL_MONARCHY": "#22c55e",
    "ELECTORAL_DEMOCRACY":     "#84cc16",
    "DECLINING_REPUBLIC":      "#eab308",
    "HYBRID_REGIME":           "#f97316",
    "DEMOCRATIC_FACADE":       "#ef4444",
    "COMMUNIST_STATE":         "#991b1b",
    "ABSOLUTE_MONARCHY":       "#7c3aed",
    "FAILED_STATE":            "#374151",
    "WAR_STATE":               "#dc2626",
}


if __name__ == "__main__":
    import pandas as pd
    rows = []
    for r in get_all_regimes():
        rows.append({
            "국가": r.country,
            "레짐 유형": r.regime_label_ko,
            "RPI": r.rpi_total,
            "파사드": r.facade_score,
            "분쟁": "✓" if r.active_conflict else "",
            "이름-실체 괴리": r.name_reality_gap,
            "비고": r.analyst_notes[:60] + "..." if len(r.analyst_notes) > 60 else r.analyst_notes,
        })
    df = pd.DataFrame(rows).sort_values("RPI", ascending=False)
    print(df.to_string(index=False))
