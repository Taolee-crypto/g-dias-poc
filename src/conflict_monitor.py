"""
conflict_monitor.py - 분쟁 실시간 모니터링

전쟁·분쟁이 민주주의 지표를 어떻게 왜곡하는지 정량화.
분쟁 국가는 DSI/RPI에 '전시 보정' 적용.

데이터 소스:
  - ACLED (Armed Conflict Location & Event Data): acleddata.com
    → 무료 API (등록 필요). 일별 분쟁 이벤트.
  - UCDP (Uppsala Conflict Data Program): ucdp.uu.se
    → 연간 무력충돌 데이터
  - SIPRI (스톡홀름 국제평화연구소): sipri.org
    → 군비지출 데이터
  - OCHA (유엔 인도주의 조정국): reliefweb.int
    → 인도주의 위기 현황

현재 활성 분쟁 (2024~2025 기준):
  - 러시아-우크라이나 전쟁 (2022~)
  - 이스라엘-하마스/헤즈볼라/이란 (2023~)
  - 수단 내전 (2023~)
  - 미얀마 내전 (2021~)
  - 예멘 내전 (2014~)
  - 시리아 내전 (2011~)
  - 사헬 지역 (말리, 부르키나파소, 니제르)
  - 소말리아 알샤바브
  - 나이지리아 보코하람
  - 멕시코 카르텔 분쟁
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import requests


@dataclass
class ConflictStatus:
    iso3: str
    country: str

    # 분쟁 강도 (0~100)
    intensity: float
    # 민주주의 지표 왜곡 정도 (0~100)
    # 높을수록 해당 국가 지표를 전시 맥락으로 해석해야 함
    distortion_factor: float

    conflict_type: list    # 예: ["외부침략", "내전", "테러"]
    parties: list          # 분쟁 주요 당사자
    start_year: int
    status: str            # ACTIVE / CEASEFIRE / LOW_INTENSITY / FROZEN

    # 민주주의 지표 왜곡 분석
    affected_dimensions: dict  # {차원: 왜곡 방향/크기}
    # 예: {"electoral": -20, "media": -30} → 전쟁으로 해당 차원 과소평가

    civilian_impact: str   # 민간인 피해 수준
    displacement: str      # 난민·실향민 현황
    international_involvement: list  # 개입 외부 세력

    latest_update: str
    sources: list


# ─────────────────────────────────────────────
#  활성 분쟁 데이터베이스
#  출처: ACLED, UCDP, OCHA, SIPRI, ICG 2024~2025
# ─────────────────────────────────────────────

CONFLICT_DB: dict[str, ConflictStatus] = {

    "UKR": ConflictStatus(
        iso3="UKR", country="Ukraine",
        intensity=92, distortion_factor=75,
        conflict_type=["외부 침략", "영토 전쟁"],
        parties=["러시아 연방군", "우크라이나 국군", "NATO 지원"],
        start_year=2022,
        status="ACTIVE",
        affected_dimensions={
            "electoral": -25,     # 계엄령으로 선거 연기
            "media": -20,         # 전시 단일 방송
            "civil": -15,         # 시민사회 전시 동원
            "exec_constraints": -10,  # 전시 대통령 권한 집중
        },
        civilian_impact="사망자 30만+ (추정). 민간인 1만 명 이상 사망 (UN 확인). 전력망·수도·병원 인프라 파괴",
        displacement="국내실향민 380만 명. 해외난민 650만 명 (UNHCR 2024)",
        international_involvement=["러시아 (침략)", "미국 (무기지원)", "EU (지원)", "NATO"],
        latest_update="2025-04",
        sources=["ACLED Ukraine 2024", "UCDP GED 2024", "OHCHR Ukraine Report"],
    ),

    "RUS": ConflictStatus(
        iso3="RUS", country="Russia",
        intensity=88, distortion_factor=85,
        conflict_type=["외부 침략 수행국", "국내 탄압"],
        parties=["러시아 연방군", "와그너 그룹(해산)", "체첸 카디로프 군"],
        start_year=2022,
        status="ACTIVE",
        affected_dimensions={
            "electoral": -5,   # 이미 거의 0점 → 추가 왜곡 미미
            "media": -5,       # 이미 전면 통제
            "civil": -20,      # 반전 시위 전면 탄압
            "exec_constraints": -5,
        },
        civilian_impact="반전 시위대 1만 6천+ 명 구금. 군인 사상자 15~20만 추정",
        displacement="우크라이나 점령지 주민 강제 이주",
        international_involvement=["북한 (무기·병력 지원)", "이란 (드론 공급)", "중국 (경제 지원)"],
        latest_update="2025-04",
        sources=["OVD-Info 시위 탄압 데이터", "Mediazona 사상자 집계", "ACLED Russia"],
    ),

    "ISR": ConflictStatus(
        iso3="ISR", country="Israel",
        intensity=85, distortion_factor=70,
        conflict_type=["대테러 작전", "영토 분쟁", "지역 전쟁"],
        parties=["이스라엘 국방군(IDF)", "하마스", "헤즈볼라", "이란 IRGC", "후티"],
        start_year=2023,
        status="ACTIVE",
        affected_dimensions={
            "electoral": -15,  # 전시 내각, 선거 연기
            "judicial": -25,   # 사법부 개혁 + 전시 긴급명령
            "media": -20,      # 전시 검열 강화
            "civil": -30,      # 아랍계 시민 감시 강화
            "exec_constraints": -20,  # 전시 내각 권력 집중
        },
        civilian_impact="가자 팔레스타인인 사망 4만 5천+ (가자보건부). 이스라엘인 1,200명 사망(10.7). "
                        "가자 인구 90% 실향. 북부 이스라엘 10만 명 대피",
        displacement="가자 170만 명 내부 실향. 레바논 피격으로 남부 주민 대피",
        international_involvement=["미국 (무기·외교 지원)", "이란 (하마스·헤즈볼라 지원)",
                                   "카타르 (중재)", "이집트 (국경 통제)", "UN (구호)"],
        latest_update="2025-04",
        sources=["ACLED Israel-Palestine 2024", "OCHA Gaza Situation Report",
                 "UN OHCHR", "B'Tselem"],
    ),

    "IRN": ConflictStatus(
        iso3="IRN", country="Iran",
        intensity=60, distortion_factor=58,
        conflict_type=["대리전 수행", "국내 탄압", "핵 긴장"],
        parties=["IRGC", "하마스·헤즈볼라·후티 지원", "이스라엘 맞대응"],
        start_year=2023,
        status="ACTIVE",
        affected_dimensions={
            "electoral": -5,
            "media": -10,   # 전시 추가 검열
            "civil": -20,   # 시위 강경 진압 가속
        },
        civilian_impact="마흐사 아미니 시위(2022) 이후 500+ 명 처형. 시위대 1만 8천+ 구금",
        displacement="쿠르드·발루치 소수민족 분쟁 지속",
        international_involvement=["이스라엘 (직접 미사일 교환 2024)", "미국 (제재·압박)",
                                   "러시아 (드론 기술 협력)", "중국 (경제 협력)"],
        latest_update="2025-04",
        sources=["ACLED Iran 2024", "Amnesty International Iran Report 2024",
                 "IAEA Iran Nuclear Reports"],
    ),

    "PSE": ConflictStatus(
        iso3="PSE", country="Palestine (Gaza/West Bank)",
        intensity=98, distortion_factor=95,
        conflict_type=["점령", "분쟁", "인도주의 위기"],
        parties=["이스라엘 IDF", "하마스 (가자)", "팔레스타인 자치정부 (서안)"],
        start_year=1967,
        status="ACTIVE",
        affected_dimensions={
            "electoral": -90,
            "judicial": -95,
            "media": -95,
            "civil": -95,
            "exec_constraints": -90,
        },
        civilian_impact="가자 사망자 4만 5천+ (2023.10~). 병원·학교·인프라 90% 파괴. "
                        "기근 위기 (IPC 5단계 기아). 북부 가자 완전 파괴",
        displacement="가자 170만 명 (전체 인구 230만) 내부 실향",
        international_involvement=["이스라엘 (군사 점령)", "이집트 (라파 국경)",
                                   "UN (구호 제한)", "카타르 (중재·자금)", "미국 (이스라엘 지원)"],
        latest_update="2025-04",
        sources=["OCHA Gaza Situation Reports", "WHO Gaza Health Updates",
                 "WFP Food Security Gaza", "ICJ Provisional Measures"],
    ),

    "SDN": ConflictStatus(
        iso3="SDN", country="Sudan",
        intensity=88, distortion_factor=82,
        conflict_type=["내전", "군사 쿠데타"],
        parties=["수단군(SAF)", "신속지원군(RSF)"],
        start_year=2023,
        status="ACTIVE",
        affected_dimensions={"electoral": -80, "civil": -75, "media": -70},
        civilian_impact="사망자 2만+ (2023~). 실향민 세계 최다 (1,000만+). 다르푸르 인종청소 재개",
        displacement="국내실향민 1,000만+. 주변국 난민 200만+",
        international_involvement=["UAE (RSF 지원 의혹)", "이집트 (SAF 지원)", "러시아 (바그너 과거 관여)"],
        latest_update="2025-04",
        sources=["ACLED Sudan 2024", "OCHA Sudan Crisis Update", "Human Rights Watch Sudan"],
    ),

    "MMR": ConflictStatus(
        iso3="MMR", country="Myanmar",
        intensity=75, distortion_factor=72,
        conflict_type=["군사 쿠데타 이후 내전"],
        parties=["군부 쿠데타 정권(SAC)", "저항군(PDF)", "소수민족 무장단체(EAO)"],
        start_year=2021,
        status="ACTIVE",
        affected_dimensions={"electoral": -85, "civil": -80, "media": -85},
        civilian_impact="쿠데타 이후 사망자 5,000+. 정치범 2만+. 로힝야 난민 문제 지속",
        displacement="국내실향민 300만+",
        international_involvement=["중국 (군부 경제 지원)", "러시아 (무기 공급)", "ASEAN (미약한 대응)"],
        latest_update="2025-04",
        sources=["ACLED Myanmar 2024", "Assistance Association for Political Prisoners"],
    ),

    "YEM": ConflictStatus(
        iso3="YEM", country="Yemen",
        intensity=70, distortion_factor=68,
        conflict_type=["내전", "대리전"],
        parties=["후티(안사르 알라)", "예멘 정부군", "사우디 연합군"],
        start_year=2014,
        status="ACTIVE",
        affected_dimensions={"electoral": -70, "civil": -65, "exec_constraints": -60},
        civilian_impact="사망자 37만 7천+ (직접+간접). 세계 최악 인도주의 위기 (UN)",
        displacement="국내실향민 470만+",
        international_involvement=["사우디아라비아 (개입)", "UAE", "이란 (후티 지원)", "미국 (후티 공습 2024)"],
        latest_update="2025-04",
        sources=["ACLED Yemen 2024", "OCHA Yemen Situation Report", "UN Panel of Experts"],
    ),

    "MEX": ConflictStatus(
        iso3="MEX", country="Mexico",
        intensity=42, distortion_factor=35,
        conflict_type=["카르텔 분쟁", "저강도 내전"],
        parties=["시날로아 카르텔", "CJNG", "연방군", "지역 민병대"],
        start_year=2006,
        status="ACTIVE",
        affected_dimensions={
            "electoral": -25,   # 선거 폭력·후보 암살
            "judicial": -30,    # 법관 협박
            "media": -35,       # 언론인 암살 최다
            "exec_constraints": -20,
        },
        civilian_impact="마약 전쟁 사망자 45만+ (2006~2024). 연간 살인율 세계 최상위권. "
                        "언론인 살해 세계 1~3위 수준",
        displacement="국내실향민 38만+ (카르텔 강제 이주)",
        international_involvement=["미국 (소비 시장·무기 공급)", "펜타닐 원료 중국 공급"],
        latest_update="2025-04",
        sources=["ACLED Mexico 2024", "Reporters Without Borders Mexico",
                 "INEGI 살인통계", "Global Initiative Against Transnational Organized Crime"],
    ),

    "NGA": ConflictStatus(
        iso3="NGA", country="Nigeria",
        intensity=55, distortion_factor=45,
        conflict_type=["테러", "분리독립 운동", "목동-농민 충돌"],
        parties=["보코하람", "ISWAP", "IPOB", "연방군"],
        start_year=2009,
        status="ACTIVE",
        affected_dimensions={"electoral": -30, "civil": -25, "exec_constraints": -20},
        civilian_impact="보코하람 사망자 35만+ (2009~). 북동부 실향민 200만+",
        displacement="북동부 실향민 200만+",
        international_involvement=["미국 (대테러 지원)", "프랑스 (사헬 협력)", "중국 (인프라 투자)"],
        latest_update="2025-04",
        sources=["ACLED Nigeria 2024", "UNHCR Nigeria", "Global Terrorism Index"],
    ),

    "KOR": ConflictStatus(
        iso3="KOR", country="South Korea",
        intensity=8, distortion_factor=10,
        conflict_type=["헌정 위기"],
        parties=["윤석열 대통령", "국회", "헌법재판소"],
        start_year=2024,
        status="LOW_INTENSITY",
        affected_dimensions={
            "electoral": -10,
            "exec_constraints": -15,  # 계엄 시도 자체가 견제 구조 위협
        },
        civilian_impact="비상계엄(2024.12.3) 6시간 해제. 탄핵 시위·지지 집회 동시 진행. 직접 폭력 없음",
        displacement="없음",
        international_involvement=["미국 (한미동맹·군사 공조)", "북한 (군사 도발 지속)"],
        latest_update="2025-04",
        sources=["헌법재판소 탄핵 결정 2025.4", "국회의사록 2024.12"],
    ),
}


def get_conflict(iso3: str) -> Optional[ConflictStatus]:
    return CONFLICT_DB.get(iso3)

def get_active_conflicts() -> list[ConflictStatus]:
    return [c for c in CONFLICT_DB.values() if c.status == "ACTIVE"]

def apply_conflict_correction(dsi: float, rpi: float,
                               conflict: ConflictStatus) -> dict:
    """
    전시 국가 지표 보정.
    분쟁이 민주주의 지표를 과소/과대 평가하는 것을 명시적으로 표시.
    """
    if not conflict or conflict.intensity < 10:
        return {"dsi_corrected": dsi, "rpi_corrected": rpi,
                "distortion": 0, "note": ""}

    # 피침략국 vs 침략국 vs 내전국 구분
    correction_note = ""
    dsi_adj = dsi
    rpi_adj = rpi

    if "외부 침략" in conflict.conflict_type and "수행국" not in conflict.conflict_type[0]:
        # 피침략국: 일부 민주주의 제한은 침략의 결과 → 상향 보정
        correction = conflict.distortion_factor * 0.4
        dsi_adj = min(100, dsi + correction * 0.3)
        rpi_adj = min(100, rpi + correction * 0.2)
        correction_note = f"[피침략국 보정 +{correction*0.3:.1f}] 전시 제한은 침략 결과"
    elif "침략 수행국" in str(conflict.conflict_type):
        # 침략국: 지표가 오히려 과대 평가될 수 있음 → 하향 보정
        correction = conflict.distortion_factor * 0.3
        dsi_adj = max(0, dsi - correction * 0.2)
        rpi_adj = max(0, rpi - correction * 0.2)
        correction_note = f"[침략국 하향 보정 -{correction*0.2:.1f}] 전쟁 개시 책임"
    else:
        # 내전·테러: 중립 보정
        correction_note = f"[분쟁 왜곡 {conflict.distortion_factor:.0f}%] 전시 맥락 고려 필요"

    return {
        "dsi_original": round(dsi, 1),
        "dsi_corrected": round(dsi_adj, 1),
        "rpi_original": round(rpi, 1),
        "rpi_corrected": round(rpi_adj, 1),
        "distortion": conflict.distortion_factor,
        "note": correction_note,
        "conflict_type": conflict.conflict_type,
        "intensity": conflict.intensity,
    }


if __name__ == "__main__":
    print("=== 활성 분쟁 현황 ===")
    for c in sorted(get_active_conflicts(), key=lambda x: -x.intensity):
        print(f"\n[{c.intensity:3.0f}] {c.country}")
        print(f"  유형: {', '.join(c.conflict_type)}")
        print(f"  왜곡: {c.distortion_factor}% | 최신: {c.latest_update}")
        print(f"  민간인: {c.civilian_impact[:80]}...")
