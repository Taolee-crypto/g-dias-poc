"""
geopolitical_analyzer.py - G-DIAS 지정학 종합 분석 엔진

기능:
  1. 분쟁 시작 책임 추적 (Conflict Attribution)
  2. 권위주의 동맹 네트워크 (Authoritarian Axis)
  3. 신정·공산·왕정 체제 내부 억압 지수
  4. 경제 무기화 (제재, 에너지 봉쇄)
  5. 핵·생화학 위협 지수

데이터 원칙:
  - UN 안보리 결의안 투표 기록 (공개)
  - ICC/ICJ 제소 및 판결 기록 (공개)
  - SIPRI 군비 지출 (공개)
  - Amnesty International / HRW 연간 보고서 (공개)
  - 언론자유도 (RSF 공식 발표)
  - ACLED 분쟁 개시 데이터
  - 미국 의회조사국(CRS) 보고서 (공개)
"""

from dataclasses import dataclass, field
from typing import Optional
import json


# ══════════════════════════════════════════════
#  분쟁 시작 책임 추적
#  원칙: 국제법(UN 헌장 2조4항) 기준
#        → 먼저 타국 영토에 군사력 투사한 쪽이 침략자
#        단, 선제공격(preemptive)과 예방공격(preventive) 구분
# ══════════════════════════════════════════════

@dataclass
class ConflictAttribution:
    conflict_id: str
    name: str
    initiator: str               # 군사 행동을 먼저 시작한 주체
    initiator_iso3: str
    legal_basis: str             # UN 헌장 기준 평가
    un_resolution: str           # 관련 UN 결의안
    initiator_justification: str # 시작한 쪽의 자체 명분
    legal_assessment: str        # 국제법 평가
    icc_icj_status: str          # ICC/ICJ 상태
    notes: str


CONFLICT_ATTRIBUTIONS = {

    "RUS_UKR": ConflictAttribution(
        conflict_id="RUS_UKR",
        name="러시아-우크라이나 전쟁",
        initiator="러시아",
        initiator_iso3="RUS",
        legal_basis="UN 헌장 2조4항 위반 — 타국 영토 무력 침공",
        un_resolution="ES-11/1 (2022.3.2) — 141개국 찬성, 러시아 규탄",
        initiator_justification="나토 동진 위협, 우크라이나 내 러시아계 보호, 나치 청산",
        legal_assessment="UN 총회 141-5 압도적 다수로 침략 규탄. "
                         "ICJ 2022.3.16 잠정조치 — 즉각 군사작전 중단 명령(러시아 불복). "
                         "ICC 2023.3 푸틴 체포영장 발부(아동 불법 이송 혐의). "
                         "국제법상 침략전쟁으로 규정.",
        icc_icj_status="ICC 체포영장 발부(2023). ICJ 잠정조치 명령(러시아 불이행)",
        notes="크림반도 병합(2014)은 별도 사건. 돈바스 분쟁(2014~)이 전면전으로 확대."
    ),

    "ISR_HAMAS_2023": ConflictAttribution(
        conflict_id="ISR_HAMAS_2023",
        name="이스라엘-하마스 전쟁 (2023~)",
        initiator="하마스",
        initiator_iso3="PSE",
        legal_basis="하마스의 10.7 테러 공격이 군사 행동 개시. "
                    "이스라엘의 반격은 자위권(UN 헌장 51조) 주장. "
                    "단, 가자 봉쇄·집단처벌은 국제인도법 위반 논란.",
        un_resolution="S/2023/773 미국 거부권. A/ES-10/21 인도주의 휴전 촉구.",
        initiator_justification="가자 봉쇄·점령에 대한 저항, 팔레스타인 해방",
        legal_assessment="10.7 공격은 국제인도법상 전쟁범죄 (민간인 1,200명 학살, 인질). "
                         "이스라엘 반격의 비례성 — ICJ 2024.1 잠정조치(집단학살 예방 명령). "
                         "양측 모두 ICC 수사 대상. "
                         "핵심 쟁점: 점령지 자위권 적용 범위.",
        icc_icj_status="ICJ 잠정조치(2024.1). ICC 네타냐후·하마스 지도부 체포영장 청구(2024)",
        notes="1967년 점령의 법적 지위가 현 전쟁의 배경. "
              "이란의 하마스·헤즈볼라·후티 지원이 지역 전쟁화의 핵심 변수."
    ),

    "USA_IRAQ_2003": ConflictAttribution(
        conflict_id="USA_IRAQ_2003",
        name="미국-이라크 전쟁 (2003)",
        initiator="미국·영국 연합군",
        initiator_iso3="USA",
        legal_basis="UN 안보리 승인 없는 선제공격 — 국제법적 정당성 논란",
        un_resolution="1441호 '심각한 결과' 경고. 2003년 침공 승인 결의안 없음.",
        initiator_justification="대량살상무기(WMD) 보유 주장, 알카에다 연계 주장, "
                                "이라크 민주화",
        legal_assessment="WMD 없음으로 확인 — 개전 명분 붕괴. "
                         "코피 아난 UN 사무총장: '명백한 국제법 위반'. "
                         "칠콧 보고서(영국): '평화적 수단 미소진'. "
                         "국제법 학계 다수: 불법 침략전쟁으로 평가.",
        icc_icj_status="ICC 비회원국(미국) — 미국인 기소 불가. 전범 책임 미규명.",
        notes="9/11 이후 '선제공격 독트린'. 이라크 전쟁은 ISIS 탄생의 구조적 원인 제공. "
              "미국의 '민주주의 수출' 실패 사례로 기록."
    ),

    "USA_AFGHANISTAN_2001": ConflictAttribution(
        conflict_id="USA_AFGHANISTAN_2001",
        name="아프가니스탄 전쟁 (2001~2021)",
        initiator="미국·나토",
        initiator_iso3="USA",
        legal_basis="UN 안보리 결의 1368호 지지 — 9/11 이후 자위권 행사 국제적 인정",
        un_resolution="1368호(2001): 9/11 규탄 및 자위권 인정. 1386호: ISAF 설립",
        initiator_justification="9/11 테러 응징, 알카에다 소탕, 탈레반 제거",
        legal_assessment="9/11 직후에는 국제적 지지. "
                         "20년 점령 지속 → 민간인 피해 누적 → 정당성 약화. "
                         "2021 철수 후 탈레반 재집권 — 목표 미달성. "
                         "전쟁 중 드론 공습 민간인 피해 — 국제인도법 위반 조사 중.",
        icc_icj_status="ICC 예비조사(아프간·미군 모두 포함). 미국 ICC 탈퇴 협박.",
        notes="나토 역사상 유일한 집단자위권(5조) 발동. "
              "소련(1979~89)에 이은 강대국 두 번째 아프간 실패."
    ),

    "USA_IRAN_2020": ConflictAttribution(
        conflict_id="USA_IRAN_2020",
        name="미국-이란 긴장 (솔레이마니 암살 2020~)",
        initiator="복합",
        initiator_iso3="USA",
        legal_basis="국가원수급 군사령관 제3국 영토(이라크)에서 드론 암살 — "
                    "이라크 주권 침해, 국제법 논란",
        un_resolution="직접 결의안 없음. 이라크 의회 미군 철수 요구 결의.",
        initiator_justification="솔레이마니의 테러 공격 임박 주장, "
                                "이라크·시리아 미군 공격 보복",
        legal_assessment="이란 이라크 대사관 공격(2019) → 미국 솔레이마니 암살(2020) → "
                         "이란 미사일 반격. 상호 에스컬레이션. "
                         "UN 특별보고관: '불법 초법적 살인'. "
                         "미국: '합법적 자위 행동' 주장.",
        icc_icj_status="ICC 수사 없음(미국 비회원국)",
        notes="이란 핵합의(JCPOA) 트럼프 탈퇴(2018)가 긴장 근본 원인. "
              "2024년 이스라엘-이란 직접 미사일 교환으로 확전."
    ),

    "IRAN_PROXY": ConflictAttribution(
        conflict_id="IRAN_PROXY",
        name="이란 대리전 네트워크",
        initiator="이란 IRGC",
        initiator_iso3="IRN",
        legal_basis="타국 내 민간인 대상 무장단체 지원 — "
                    "테러지원국 지정(미국), 국제법상 간접 침략 논란",
        un_resolution="안보리 결의 2231호(JCPOA). 이란 무기금수 결의 반복 위반.",
        initiator_justification="이스라엘 저항, 팔레스타인 해방, "
                                "미국 제국주의 대항, 이슬람 혁명 수출",
        legal_assessment="하마스·헤즈볼라·후티·이라크 민병대(PMF)에 "
                         "무기·자금·훈련 제공 — UNSC 보고서 반복 확인. "
                         "후티의 국제 상선 공격 → 국제해양법 위반. "
                         "2024년 이스라엘에 탄도미사일 300발 직접 발사.",
        icc_icj_status="직접 제소 없음. 개별 사건별 수사 진행 중.",
        notes="이란은 '저항의 축(Axis of Resistance)' 개념으로 정당화. "
              "실질적으로는 지역 패권 확장 전략."
    ),

    "RUSSIA_IRAN_DPRK_AXIS": ConflictAttribution(
        conflict_id="RUSSIA_IRAN_DPRK_AXIS",
        name="러시아-이란-북한 군사 협력",
        initiator="러시아 주도",
        initiator_iso3="RUS",
        legal_basis="UN 대북제재 결의 위반(북한 무기 이전). "
                    "이란 드론·미사일 기술 이전. 국제 무기금수 위반.",
        un_resolution="UNSC 결의 2397호(대북제재) 등 다수 위반.",
        initiator_justification="주권적 군사 협력, 서방 제재에 대한 집단 대응",
        legal_assessment="UN 전문가패널 2024: 북한이 러시아에 포탄 수백만 발 이전 확인. "
                         "이란 샤헤드-136 드론이 우크라이나 공격에 사용 확인(NAFO·ESA 위성 분석). "
                         "3국 모두 UN 제재 위반. "
                         "러시아의 UN 전문가패널 해산 거부권 행사(2024.3).",
        icc_icj_status="개별 수사 진행. 러시아 ICC 탈퇴(2016).",
        notes="공산주의 이념이 아닌 '반서방'이 결속 원리. "
              "러시아: 에너지·군사기술 / 이란: 드론·미사일 / 북한: 재래식 무기·병력."
    ),
}


# ══════════════════════════════════════════════
#  이란 — 신정 체제 종합 분석
#  (요청 사항 반영: 이란의 실제 구조를 데이터로)
# ══════════════════════════════════════════════

@dataclass
class TheocracyProfile:
    iso3: str
    country: str
    official_name: str
    founding_ideology: str
    actual_power_structure: str
    supreme_leader: str
    election_reality: str
    internal_repression: dict
    economic_governance: dict
    external_aggression: dict
    international_isolation: dict
    data_sources: list


IRAN_PROFILE = TheocracyProfile(
    iso3="IRN",
    country="Iran",
    official_name="이슬람 공화국(Islamic Republic of Iran)",
    founding_ideology="호메이니의 벨라야트-에 파키흐(이슬람 법학자 통치론) — "
                       "이슬람 신학자가 정치 최고권력을 가져야 한다는 신정론",
    actual_power_structure="""
권력 구조 (상위부터):
  1. 최고지도자(하메네이, 1989~현재)
     - 군 통수권, 사법부 임명, IRGC 지휘, 방송 통제
     - 선출 아님 — 전문가회의(역시 수호위원회가 검증한 성직자들)가 임명
  2. 수호위원회(Guardian Council)
     - 12인 구성 (6명 최고지도자 임명, 6명 사법부장 추천)
     - 모든 후보자 자격 심사권 → 선거 결과 사전 결정
     - 입법 거부권
  3. 대통령
     - 수호위원회 통과한 후보만 출마 가능
     - 실권 제한적 (최고지도자가 외교·안보 실권)
  4. 이슬람혁명수비대(IRGC)
     - 정규군과 별도, 최고지도자 직속
     - 이란 경제 30~40% 장악 (건설·석유·통신·금융)
     - 대외 공작·대리전 수행(쿠드스군)
""",
    supreme_leader="알리 하메네이 (1989년~, 35년+ 집권)",
    election_reality="""
선거 현황:
  - 2024 대선: 후보 80명 신청 → 수호위원회 6명만 승인 (93% 탈락)
  - 2021 대선: 투표율 48.8% (이슬람공화국 역대 최저)
  - 2024 총선: 투표율 41% (역대 최저)
  - 개혁파 후보는 반복적으로 자격 박탈
  → '선거가 있으나 선택이 없는' 구조
""",
    internal_repression={
        "마흐사_아미니_시위(2022~2023)": {
            "사망자": "500명+ (이란인권운동가뉴스, 구금 중 포함)",
            "구금자": "18,000명+",
            "처형": "7명+ 시위 관련 처형 (Amnesty International 2023)",
            "출처": "AI, HRW, UN 특별보고관",
        },
        "2019_11월_시위": {
            "사망자": "304명+ (암네스티 인터내셔널)",
            "구금자": "7,000명+",
            "인터넷": "5일 전국 인터넷 차단",
            "출처": "Amnesty International, Netblocks",
        },
        "사형_집행": {
            "2023년_처형수": "853명 (공식확인) — 세계 2위",
            "2022년_처형수": "576명",
            "마약범죄_처형비율": "전체 처형의 50%+",
            "출처": "Iran Human Rights (NGO), Amnesty International",
        },
        "언론_자유": {
            "RSF_순위_2024": "176위 / 180개국",
            "수감_기자수": "세계 3위 (CPJ 2023)",
            "소셜미디어": "인스타그램·왓츠앱·텔레그램·트위터 차단",
            "출처": "RSF Press Freedom Index 2024, CPJ",
        },
        "소수자_탄압": {
            "쿠르드족": "쿠르드 활동가 처형 지속. 2022~24 쿠르드 지역 시위 군 진압",
            "바하이교": "1979년 이후 지속적 박해. 200명+ 처형",
            "LGBT": "동성애 최고 사형 — 실제 집행 다수",
            "출처": "HRW World Report 2024, UNHCR",
        },
    },
    economic_governance={
        "IRGC_경제장악": "GDP의 추정 30~40% 통제 (건설·석유·통신·금융)",
        "제재_영향": "2023 GDP $367B (제재 없었을 시 추정의 40% 수준)",
        "인플레이션": "40%+ (2023, 세계은행)",
        "청년실업": "27%+ (공식통계, 실제 더 높을 것)",
        "두뇌유출": "연간 15만~18만 고학력자 이민 (이란 의회 자체 통계)",
        "출처": "World Bank, IMF, Coface Country Risk",
    },
    external_aggression={
        "대리전_네트워크": {
            "하마스": "연간 $100M+ 자금 지원 (미 재무부 추정)",
            "헤즈볼라": "연간 $700M+ (미 국무부 추정) — 레바논 사실상 국가 내 국가",
            "후티": "예멘 내전 개입, 홍해 상선 공격 지원",
            "이라크_PMF": "이라크 내 친이란 민병대 통제",
            "출처": "US Treasury, US State Dept., UN Panel of Experts",
        },
        "핵_프로그램": {
            "우라늄_농축도": "84% (무기급 90% 직전, IAEA 2023)",
            "JCPOA_탈퇴": "미국 2018 탈퇴 후 이란 단계적 의무 불이행",
            "IAEA_접근": "감시카메라 60% 차단 (2023)",
            "출처": "IAEA Reports 2023-2024",
        },
        "이스라엘_직접공격": {
            "2024_4월": "드론 170대 + 순항미사일 30발 + 탄도미사일 120발",
            "2024_10월": "탄도미사일 180발+ 직접 발사",
            "피해": "이스라엘 방공망 요격 (미국·영국·요르단 지원)",
            "출처": "IDF 공식 발표, CSIS Missile Defense Project",
        },
    },
    international_isolation={
        "제재": "UN·미국·EU·영국 다중 제재. 2012~현재 SWIFT 차단",
        "FATF": "FATF 블랙리스트 (자금세탁·테러자금 고위험국)",
        "외교": "이스라엘·바레인·코모로와 단교. 사우디와 2023 중국 중재 재수교",
        "출처": "FATF, US OFAC, EU Council",
    },
    data_sources=[
        "IAEA 이란 핵 보고서 (2023-2024)",
        "Amnesty International Annual Report 2024",
        "Human Rights Watch World Report 2024",
        "RSF Press Freedom Index 2024",
        "UN 이란 인권 특별보고관 보고서",
        "US Treasury OFAC 제재 목록",
        "UN Panel of Experts (대이란 결의 이행)",
        "Committee to Protect Journalists (CPJ)",
        "World Bank Iran Economic Monitor",
        "FATF Plenary Report",
    ]
)


# ══════════════════════════════════════════════
#  권위주의 동맹 네트워크 분석
#  러시아-중국-이란-북한 "반서방 축"
# ══════════════════════════════════════════════

@dataclass
class AuthoritarianAxis:
    name: str
    members: list
    binding_principle: str      # 이념이 아닌 실제 결속 원리
    military_cooperation: dict
    economic_cooperation: dict
    information_warfare: dict
    internal_commonalities: list
    western_countermeasures: list
    stability_assessment: str
    data_sources: list


ANTI_WESTERN_AXIS = AuthoritarianAxis(
    name="반서방 권위주의 네트워크",
    members=["러시아", "중국", "이란", "북한"],
    binding_principle="""
이념적 공통점이 아닌 '공통의 적'으로 결속:
  - 러시아: 제국주의 부활, 소련 권역 회복
  - 중국: 미국 주도 질서 대체, 대만 통일
  - 이란: 이슬람 혁명 수출, 이스라엘 소멸, 미국 중동 축출
  - 북한: 김씨 왕조 생존, 핵무장 완성
  
  공통: UN·ICC·국제법 무력화, 서방 정보 생태계 교란,
        권위주의 모델 정당화
""",
    military_cooperation={
        "러시아_북한": {
            "내용": "북한 → 러시아: 포탄 수백만 발, 탄도미사일 KN-23, 병력 1만+ (2024)",
            "대가": "러시아 → 북한: 위성기술, 잠수함 기술, 식량·에너지",
            "UN_위반": "UNSC 결의 2397호 위반 — UN 전문가패널 확인",
            "출처": "UN Panel of Experts 2024, 한국 국정원, 미 국방부",
        },
        "러시아_이란": {
            "내용": "이란 → 러시아: 샤헤드 드론 수천 대, 탄도미사일",
            "대가": "러시아 → 이란: Su-35 전투기, S-400 방공시스템, 핵기술 협력",
            "확인": "EU 위성분석, 우크라이나 격추 드론 이란 부품 확인",
            "출처": "ESA, Bellingcat, 미 국무부",
        },
        "중국_러시아": {
            "내용": "중국: 반도체·전자부품·공작기계 공급 (우회 수출로 제재 회피)",
            "군사직접지원": "표면적으로 자제 (서방 제재 우려)",
            "출처": "CSIS, 미 상무부 수출통제 목록",
        },
        "이란_헤즈볼라_하마스_후티": {
            "내용": "이란 IRGC 쿠드스군이 4개 그룹 통합 지휘·조율",
            "출처": "ICG, ISW, ACLED",
        },
    },
    economic_cooperation={
        "러시아_중국": "중러 교역 2023년 $240B 사상 최대. 루블-위안화 결제 확대",
        "이란_중국": "25년 전략협력협정(2021). 중국이 이란 석유 70%+ 구매(제재 우회)",
        "북한_중국": "북중 교역이 북한 대외무역 90%+",
        "달러_이탈": "4개국 모두 SWIFT·달러 결제 우회 시스템 개발 중",
        "출처": "CSIS, IMF, 미 재무부 OFAC",
    },
    information_warfare={
        "러시아": "RT·스푸트니크 글로벌 역정보. 선거 개입(미·프·독 확인). 딥페이크",
        "중국": "유나이티드워크 네트워크. 틱톡 알고리즘 조작 의혹. '늑대전사 외교'",
        "이란": "페이스북·인스타 이란 연계 계정 대규모 삭제(META 2024). 해킹 그룹 APT33",
        "북한": "라자루스 그룹 — 암호화폐 탈취($3B+). 핵무기 자금 조달",
        "출처": "META Threat Intelligence, Microsoft MSTIC, Mandiant",
    },
    internal_commonalities=[
        "국가 통제 미디어 / 독립 언론 탄압",
        "정치 반대파 투옥·암살",
        "선거 조작 또는 경쟁 배제",
        "사법부 행정부 종속",
        "종교·민족 소수자 억압",
        "인터넷 검열·차단",
        "경제 과두제 — 권력과 자본의 결합",
    ],
    western_countermeasures=[
        "SWIFT 차단 (러시아·이란·북한)",
        "수출통제 (반도체·첨단기술)",
        "ICC 체포영장 (푸틴)",
        "나토 동진 확장",
        "우크라이나 군사 지원",
        "AUKUS, Quad 대중국 포위망",
    ],
    stability_assessment="""
동맹 강도: 중간 — '결혼'이 아닌 '편의 동반자'
  - 중국은 러시아 침략전쟁에 공개 지지 자제 (경제 손실 우려)
  - 러시아-이란은 역사적 경쟁 관계 (카스피해, 중앙아시아)
  - 북한은 모든 나라에 이용당하면서 이용하는 구조
  - 공통점: 서방이 강해질수록 결속 강화, 내부에서는 경쟁
""",
    data_sources=[
        "UN Panel of Experts Reports",
        "CSIS China Power",
        "ISW (Institute for the Study of War)",
        "Bellingcat Open Source Intelligence",
        "META/Google/Microsoft Threat Intelligence",
        "Carnegie Endowment for International Peace",
        "Stockholm International Peace Research Institute (SIPRI)",
    ]
)


# ══════════════════════════════════════════════
#  미국 군사행동 균형 분석
#  (G-DIAS는 서방 편향도 인정해야 함)
# ══════════════════════════════════════════════

USA_MILITARY_RECORD = {
    "개입_횟수": "1945년 이후 약 80건+ 해외 군사 개입",
    "합법_개입": [
        "한국전쟁(1950~53) — UN 안보리 결의 82·83호",
        "걸프전(1991) — UN 결의 678호",
        "아프가니스탄(2001) — UN 결의 1368호, 9/11 자위권",
        "리비아(2011) — UN 결의 1973호",
        "ISIS 대응(2014~) — 이라크 정부 요청",
    ],
    "논란_개입": [
        "베트남전(1965~75) — 통킹만 사건 조작 (의회 청문 확인)",
        "이라크(2003) — WMD 거짓 명분, UN 승인 없음",
        "파나마(1989) — UN 결의 없이 침공, 노리에가 체포",
        "그레나다(1983) — 일방적 침공",
        "리비아·시리아 드론 공습 — 의회 승인 없음",
    ],
    "CIA_비밀공작": [
        "이란(1953) — 모사데크 총리 쿠데타 지원 (CIA 2013년 공식 인정)",
        "칠레(1973) — 아옌데 쿠데타 지원",
        "과테말라(1954) — 민주 정부 전복",
        "니카라과(1980s) — 콘트라 반군 지원 (이란-콘트라 스캔들)",
    ],
    "자국_민주주의_훼손": [
        "Citizens United 판결(2010) — 기업 정치자금 무제한",
        "NSA 대규모 시민 감청 (스노든 폭로 2013)",
        "2021.1.6 의회 점거 — 미국 내부 민주주의 위기",
        "게리맨더링 구조화",
        "선거인단 제도 — 득표 역전 가능 구조",
    ],
    "평가": "세계 최강 민주주의 국가이면서 동시에 가장 많은 타국 정치개입 역사. "
           "이중 잣대 문제는 G-DIAS 신뢰성의 핵심 시험대. "
           "미국도 동일한 기준으로 측정해야 함.",
    "출처": ["CIA CREST 기밀해제 문서", "상원 처치위원회 보고서(1975)",
             "칠콧 보고서(2016)", "상원 정보위 NSA 보고서(2014)"],
}


# ══════════════════════════════════════════════
#  국가별 종합 지정학 위험 점수 계산
# ══════════════════════════════════════════════

def calculate_geopolitical_risk(iso3: str, dsi: float, rpi: float,
                                 conflict_intensity: float = 0) -> dict:
    """
    DSI + RPI + 분쟁 + 대외 침략성 + 핵위협을 종합한
    지정학 위험 지수 (GRI, 0~100)
    """
    # 기본 거버넌스 위험 (DSI·RPI가 낮을수록 위험)
    gov_risk = 100 - (dsi * 0.5 + rpi * 0.5)

    # 분쟁 위험
    conflict_risk = conflict_intensity

    # 대외 침략성 (regime_classifier의 facade_score 반영)
    external_aggression_scores = {
        "RUS": 90, "IRN": 75, "PRK": 60, "CHN": 45,
        "USA": 25,  # 군사 개입 많으나 동맹 기반, 민주주의 내부 견제 존재
        "ISR": 35, "SAU": 30,
    }
    ext_agg = external_aggression_scores.get(iso3, 10)

    # 핵 위협
    nuclear_scores = {
        "PRK": 80, "IRN": 65, "RUS": 70, "USA": 20,
        "CHN": 35, "ISR": 30,
    }
    nuclear = nuclear_scores.get(iso3, 0)

    # 종합
    gri = (gov_risk * 0.30 +
           conflict_risk * 0.30 +
           ext_agg * 0.25 +
           nuclear * 0.15)

    return {
        "iso3": iso3,
        "gri": round(min(100, gri), 1),
        "components": {
            "거버넌스_위험": round(gov_risk, 1),
            "분쟁_강도": round(conflict_risk, 1),
            "대외_침략성": round(ext_agg, 1),
            "핵_위협": round(nuclear, 1),
        }
    }


if __name__ == "__main__":
    print("═" * 60)
    print(" G-DIAS 지정학 분석 엔진")
    print("═" * 60)

    print("\n[분쟁 시작 책임 추적]")
    for cid, ca in CONFLICT_ATTRIBUTIONS.items():
        print(f"\n▶ {ca.name}")
        print(f"  시작자: {ca.initiator}")
        print(f"  법적 평가: {ca.legal_assessment[:80]}...")

    print("\n\n[이란 신정 체제 내부 억압 지표]")
    for cat, data in IRAN_PROFILE.internal_repression.items():
        print(f"\n  [{cat}]")
        for k, v in data.items():
            if k != "출처":
                print(f"    {k}: {v}")

    print("\n\n[반서방 동맹 군사 협력]")
    for pair, data in ANTI_WESTERN_AXIS.military_cooperation.items():
        print(f"\n  [{pair}]")
        for k, v in data.items():
            if k != "출처":
                print(f"    {k}: {str(v)[:80]}")

    print("\n\n[미국 균형 분석 — 논란 개입]")
    for item in USA_MILITARY_RECORD["논란_개입"]:
        print(f"  • {item}")
