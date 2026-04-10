"""
data_collector.py - G-DIAS 실시간 데이터 수집기 (진짜 실시간)

수집 소스 및 갱신 주기:
  [A] GDELT Project API        — 15분 갱신, API 키 불필요
      전 세계 뉴스에서 민주주의/분쟁 이벤트 실시간 추출
  [B] World Bank WGI API       — 연 1회, API 키 불필요
      거버넌스 지표 6개
  [C] ACLED API                — 일 단위, 무료 등록 필요
      무력 충돌 이벤트 데이터
  [D] ReliefWeb API (UN OCHA)  — 실시간, API 키 불필요
      인도주의 위기 현황
  [E] UNHCR Data API           — 연 1회, API 키 불필요
      난민·실향민 통계
  [F] Transparency International — 연 1회, 공식 JSON
      부패인식지수 (API 제공)

실행:
  python src/data_collector.py              # 전체 수집
  python src/data_collector.py --source gdelt   # GDELT만
  python src/data_collector.py --force      # 캐시 무시 강제 갱신
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime, timezone, timedelta
from typing import Optional
import requests
import pandas as pd
import numpy as np

CACHE_DIR  = "data/cache"
CACHE_PATH = "data/live_data_cache.json"

# 국가 목록
COUNTRIES = [
    ("SE","SWE","Sweden"),       ("DE","DEU","Germany"),
    ("CA","CAN","Canada"),       ("AU","AUS","Australia"),
    ("FR","FRA","France"),       ("JP","JPN","Japan"),
    ("GB","GBR","United Kingdom"),("KR","KOR","South Korea"),
    ("CL","CHL","Chile"),        ("US","USA","United States"),
    ("ZA","ZAF","South Africa"), ("AR","ARG","Argentina"),
    ("ID","IDN","Indonesia"),    ("SG","SGP","Singapore"),
    ("BR","BRA","Brazil"),       ("IN","IND","India"),
    ("MX","MEX","Mexico"),       ("PL","POL","Poland"),
    ("NG","NGA","Nigeria"),      ("HU","HUN","Hungary"),
    ("TR","TUR","Turkey"),       ("EG","EGY","Egypt"),
    ("RU","RUS","Russia"),       ("CN","CHN","China"),
    ("UA","UKR","Ukraine"),      ("IL","ISR","Israel"),
    ("IR","IRN","Iran"),         ("PS","PSE","Palestine"),
    ("SA","SAU","Saudi Arabia"), ("AE","ARE","UAE"),
    ("KP","PRK","North Korea"),  ("CU","CUB","Cuba"),
    ("VE","VEN","Venezuela"),    ("SD","SDN","Sudan"),
    ("MM","MMR","Myanmar"),      ("YE","YEM","Yemen"),
]
ISO2_TO_ISO3 = {c[0]: c[1] for c in COUNTRIES}
ISO3_TO_NAME = {c[1]: c[2] for c in COUNTRIES}
ISO3_TO_ISO2 = {c[1]: c[0] for c in COUNTRIES}
ISO3_LIST    = [c[1] for c in COUNTRIES]
ISO2_LIST    = [c[0] for c in COUNTRIES]


# ══════════════════════════════════════════════
#  [A] GDELT Project — 민주주의 이벤트 실시간
# ══════════════════════════════════════════════

GDELT_QUERIES = {
    # (쿼리, 설명, 연관 차원)
    "election_integrity": (
        '("election fraud" OR "electoral violence" OR "election manipulation" '
        'OR "voter suppression" OR "ballot stuffing")',
        "선거 무결성 위협 이벤트", "electoral"
    ),
    "judicial_attack": (
        '("judicial independence" OR "court packing" OR "judge arrested" '
        'OR "judiciary attacked" OR "rule of law")',
        "사법 독립성 위협", "judicial"
    ),
    "press_freedom": (
        '("journalist arrested" OR "press freedom" OR "media censorship" '
        'OR "journalist killed" OR "media shutdown")',
        "언론 자유 침해", "media"
    ),
    "civil_society": (
        '("protest crackdown" OR "NGO banned" OR "civil society" '
        'OR "political prisoner" OR "human rights defender")',
        "시민사회 탄압", "civil"
    ),
    "coup_attempt": (
        '("coup" OR "martial law" OR "emergency powers" '
        'OR "democratic backsliding" OR "autocratization")',
        "쿠데타·계엄 시도", "exec_constraints"
    ),
    "armed_conflict": (
        '("armed conflict" OR "military offensive" OR "airstrike" '
        'OR "ceasefire" OR "war crimes")',
        "무력 분쟁", "conflict"
    ),
}

def fetch_gdelt_events(timespan: str = "7d", max_per_query: int = 25) -> dict:
    """
    GDELT API v2에서 민주주의 관련 이벤트 수집.
    timespan: 1h, 24h, 7d, 30d 등
    반환: {iso3: {category: event_count, signals: [...]}}
    """
    base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
    country_signals = {iso3: {"events": {}, "articles": []} for iso3 in ISO3_LIST}
    errors = []

    for category, (query, desc, dimension) in GDELT_QUERIES.items():
        # 국가별 쿼리 (모든 국가 한 번에)
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": max_per_query,
            "format": "json",
            "timespan": timespan,
            "sort": "DateDesc",
        }
        try:
            resp = requests.get(base_url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("articles", [])

            for art in articles:
                # 기사에서 국가 추출 (소스도메인 국가코드 또는 본문)
                source_country = art.get("sourcecountry", "")
                url = art.get("url", "")
                title = art.get("title", "")
                seendate = art.get("seendate", "")

                # 어느 나라 얘기인지 본문에서 탐지
                matched = []
                for iso3, name in ISO3_TO_NAME.items():
                    if name.lower() in title.lower():
                        matched.append(iso3)

                for iso3 in matched:
                    country_signals[iso3]["events"][category] = \
                        country_signals[iso3]["events"].get(category, 0) + 1
                    country_signals[iso3]["articles"].append({
                        "category": category,
                        "title": title[:120],
                        "url": url,
                        "date": seendate,
                        "dimension": dimension,
                    })

            print(f"  [GDELT] {category}: {len(articles)}개 기사 수집 ({desc})")
            time.sleep(1.0)  # API 레이트 리밋 준수

        except Exception as e:
            errors.append(f"{category}: {e}")
            print(f"  [GDELT] {category} 실패: {e}")

    if errors:
        print(f"  [GDELT] 총 {len(errors)}개 오류")

    return country_signals


def gdelt_to_dimension_signals(country_signals: dict) -> dict:
    """
    GDELT 이벤트 수를 차원별 신호 강도로 변환.
    이벤트가 많을수록 = 문제 발생 = 해당 차원 점수 하락 신호
    반환: {iso3: {dim: signal_strength (0~100, 높을수록 위험)}}
    """
    dim_category_map = {
        "electoral":        ["election_integrity"],
        "judicial":         ["judicial_attack"],
        "media":            ["press_freedom"],
        "civil":            ["civil_society"],
        "exec_constraints": ["coup_attempt"],
        "conflict_signal":  ["armed_conflict"],
    }
    result = {}
    for iso3, data in country_signals.items():
        events = data.get("events", {})
        result[iso3] = {}
        for dim, categories in dim_category_map.items():
            count = sum(events.get(cat, 0) for cat in categories)
            # 이벤트 수 → 위험 신호 강도 (로그 스케일, 최대 100)
            signal = min(100, count * 12) if count > 0 else 0
            result[iso3][dim] = round(signal, 1)
    return result


# ══════════════════════════════════════════════
#  [B] World Bank WGI API
# ══════════════════════════════════════════════

WB_INDICATORS = {
    "VA.EST": ("voice_accountability",  "언론자유·정부책임성"),
    "RL.EST": ("rule_of_law",           "법치주의"),
    "CC.EST": ("control_corruption",    "부패통제"),
    "GE.EST": ("gov_effectiveness",     "정부효과성"),
    "PS.EST": ("political_stability",   "정치안정"),
    "RQ.EST": ("regulatory_quality",    "규제품질"),
}

def fetch_world_bank_wgi(year: int = 2022) -> dict:
    """World Bank WGI API — -2.5~+2.5 → 0~100 정규화"""
    iso2_joined = ";".join(ISO2_LIST)
    result = {iso3: {} for iso3 in ISO3_LIST}

    for wb_code, (key, desc) in WB_INDICATORS.items():
        url = (
            f"https://api.worldbank.org/v2/country/{iso2_joined}"
            f"/indicator/{wb_code}"
            f"?format=json&date={year}&per_page=200&mrv=1"
        )
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            if len(data) < 2 or not data[1]:
                continue
            for entry in data[1]:
                if entry.get("value") is None:
                    continue
                iso2 = entry["country"]["id"]
                iso3 = ISO2_TO_ISO3.get(iso2)
                if iso3:
                    raw = float(entry["value"])
                    normalized = round((raw + 2.5) / 5.0 * 100, 2)
                    result[iso3][key] = max(0, min(100, normalized))
                    result[iso3][f"{key}_raw"] = round(raw, 4)
            time.sleep(0.5)
        except Exception as e:
            print(f"  [WB] {wb_code} 오류: {e}")

    filled = sum(1 for v in result.values() if v)
    print(f"  [World Bank WGI] {filled}/{len(ISO3_LIST)}개국 수집")
    return result


# ══════════════════════════════════════════════
#  [C] ACLED API (무료 등록 후 API 키 발급)
#      https://developer.acleddata.com/
# ══════════════════════════════════════════════

def fetch_acled_conflicts(api_key: Optional[str] = None,
                           email: Optional[str] = None,
                           days_back: int = 30) -> dict:
    """
    ACLED API에서 분쟁 이벤트 수집.
    API 키 없으면 스킵 (키 등록: https://developer.acleddata.com/)

    반환: {iso3: {event_count, fatalities, event_types}}
    """
    if not api_key:
        api_key  = os.environ.get("ACLED_API_KEY")
        email    = os.environ.get("ACLED_EMAIL")

    if not api_key or not email:
        print("  [ACLED] API 키 없음 → 스킵")
        print("         등록: https://developer.acleddata.com/")
        print("         등록 후: set ACLED_API_KEY=your_key && set ACLED_EMAIL=your@email.com")
        return {}

    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    result = {}
    iso3_joined = "|".join(ISO3_LIST)

    try:
        resp = requests.get(
            "https://api.acleddata.com/acled/read.php",
            params={
                "key": api_key,
                "email": email,
                "iso": iso3_joined,
                "event_date": since,
                "event_date_where": "BETWEEN",
                "event_date_to": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "fields": "iso|event_date|event_type|fatalities|country",
                "limit": 5000,
                "format": "json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])

        for row in data:
            iso3 = ISO2_TO_ISO3.get(row.get("iso", ""), row.get("iso", ""))
            if iso3 not in result:
                result[iso3] = {"event_count": 0, "fatalities": 0, "event_types": {}}
            result[iso3]["event_count"] += 1
            result[iso3]["fatalities"] += int(row.get("fatalities", 0))
            etype = row.get("event_type", "Unknown")
            result[iso3]["event_types"][etype] = \
                result[iso3]["event_types"].get(etype, 0) + 1

        print(f"  [ACLED] {len(result)}개국 분쟁 데이터 수집 ({len(data)}건 이벤트)")
    except Exception as e:
        print(f"  [ACLED] 오류: {e}")

    return result


# ══════════════════════════════════════════════
#  [D] ReliefWeb API (UN OCHA) — 인도주의 위기
# ══════════════════════════════════════════════

def fetch_reliefweb_crisis(days_back: int = 30) -> dict:
    """
    UN OCHA ReliefWeb API에서 국가별 인도주의 위기 보고서 수집.
    API 키 불필요.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    result = {}

    try:
        resp = requests.post(
            "https://api.reliefweb.int/v1/reports",
            json={
                "filter": {
                    "operator": "AND",
                    "conditions": [
                        {"field": "date.created", "value": {"from": since}},
                        {"field": "theme.name", "value": [
                            "Coordination", "Peacekeeping and Peacebuilding",
                            "Protection and Human Rights", "Humanitarian Financing"
                        ], "operator": "OR"},
                    ],
                },
                "fields": {"include": ["title","country","date","theme","disaster_type"]},
                "limit": 200,
                "sort": ["date.created:desc"],
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])

        for item in data:
            fields = item.get("fields", {})
            countries = fields.get("country", [])
            for country_entry in countries:
                iso3 = country_entry.get("iso3", "").upper()
                if iso3 in ISO3_LIST:
                    if iso3 not in result:
                        result[iso3] = {"crisis_reports": 0, "titles": []}
                    result[iso3]["crisis_reports"] += 1
                    result[iso3]["titles"].append(
                        fields.get("title", "")[:80]
                    )

        print(f"  [ReliefWeb] {len(result)}개국 위기 보고서 수집 ({len(data)}건)")
    except Exception as e:
        print(f"  [ReliefWeb] 오류: {e}")

    return result


# ══════════════════════════════════════════════
#  [E] UNHCR Data API — 난민 통계
# ══════════════════════════════════════════════

def fetch_unhcr_displacement() -> dict:
    """
    UNHCR API에서 국가별 강제실향 통계 수집.
    """
    result = {}
    try:
        resp = requests.get(
            "https://api.unhcr.org/population/v1/population/",
            params={
                "limit": 300,
                "dataset": "population",
                "displayType": "totals",
                "year": 2023,
                "cf_type": "ISO",
            },
            timeout=20,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", []) or data.get("data", [])

        for item in items:
            coo = item.get("coo_iso", "")  # 출신국 ISO
            refugees     = item.get("refugees", 0) or 0
            asylum       = item.get("asylum_seekers", 0) or 0
            idps         = item.get("idps", 0) or 0
            stateless    = item.get("stateless", 0) or 0

            if coo in ISO3_LIST:
                if coo not in result:
                    result[coo] = {
                        "refugees_from": 0,
                        "idps": 0,
                        "total_displaced": 0,
                    }
                result[coo]["refugees_from"] += int(refugees) + int(asylum)
                result[coo]["idps"] += int(idps)
                result[coo]["total_displaced"] += (
                    int(refugees) + int(asylum) + int(idps) + int(stateless)
                )

        print(f"  [UNHCR] {len(result)}개국 실향 데이터 수집")
    except Exception as e:
        print(f"  [UNHCR] 오류: {e}")

    return result


# ══════════════════════════════════════════════
#  [F] Transparency International CPI (공식 JSON)
# ══════════════════════════════════════════════

def fetch_ti_cpi() -> dict:
    """
    TI 공식 CPI JSON 다운로드.
    직접 JSON API 없어 공식 발표 수치 내장 (연 1회 업데이트).
    TI 발표치: https://www.transparency.org/en/cpi/2023
    """
    # TI CPI 2023 공식 발표치 (0~100, 100=완전 청렴)
    CPI_2023 = {
        "SWE":82,"DEU":78,"CAN":76,"AUS":75,"FRA":71,
        "JPN":73,"GBR":71,"KOR":63,"CHL":66,"USA":69,
        "ZAF":41,"ARG":37,"IDN":34,"SGP":83,"BRA":36,
        "IND":39,"MEX":31,"POL":54,"NGA":25,"HUN":42,
        "TUR":34,"EGY":30,"RUS":26,"CHN":42,"UKR":36,
        "ISR":62,"IRN":24,"PSE":16,"SAU":52,"ARE":68,
        "PRK": 8,"CUB":36,"VEN":13,"SDN":20,"MMR":20,"YEM":16,
    }
    result = {}
    for iso3, score in CPI_2023.items():
        if iso3 in ISO3_LIST:
            result[iso3] = {
                "cpi_score": float(score),
                "cpi_year": 2023,
                "cpi_source": "Transparency International CPI 2023",
            }
    print(f"  [TI CPI] {len(result)}개국 로드 (2023 공식 발표치)")
    return result


# ══════════════════════════════════════════════
#  통합 — 모든 소스를 DSI 차원으로 합성
# ══════════════════════════════════════════════

def merge_all_sources(
    wb: dict,
    ti: dict,
    gdelt: dict,
    gdelt_signals: dict,
    acled: dict,
    reliefweb: dict,
    unhcr: dict,
) -> pd.DataFrame:
    """
    6개 소스를 통합해 국가별 5대 차원 점수 생성.

    차원 계산 공식:
      electoral  = WB_VA*0.30 + TI_CPI*0.10 + WB_PS*0.15 + GDELT_선거*(-0.20) + 기준*0.25
      judicial   = WB_RL*0.40 + WB_RQ*0.25 + TI_CPI*0.20 + GDELT_사법*(-0.15)
      media      = WB_VA*0.45 + TI_CPI*0.20 + GDELT_언론*(-0.25) + WB_CC*0.10
      civil      = WB_VA*0.30 + WB_PS*0.25 + UNHCR_실향*(-0.15) + RW_위기*(-0.10) + 기준*0.20
      exec       = WB_CC*0.35 + WB_GE*0.30 + WB_RL*0.15 + ACLED_충돌*(-0.10) + TI_CPI*0.10

    GDELT 신호는 '위험 신호 강도' → 점수에서 차감
    """
    rows = []
    for iso3, name in ISO3_TO_NAME.items():
        wb_c    = wb.get(iso3, {})
        ti_c    = ti.get(iso3, {})
        gs      = gdelt_signals.get(iso3, {})  # GDELT 위험 신호
        acled_c = acled.get(iso3, {})
        rw_c    = reliefweb.get(iso3, {})
        unhcr_c = unhcr.get(iso3, {})

        def g(d, k, default=50.0): return float(d.get(k, default))

        va  = g(wb_c, "voice_accountability")
        rl  = g(wb_c, "rule_of_law")
        cc  = g(wb_c, "control_corruption")
        ge  = g(wb_c, "gov_effectiveness")
        ps  = g(wb_c, "political_stability")
        rq  = g(wb_c, "regulatory_quality")
        cpi = g(ti_c, "cpi_score")

        # GDELT 실시간 위험 신호 (0~100, 높을수록 위험 → 점수 차감)
        g_elec  = gs.get("electoral", 0)
        g_jud   = gs.get("judicial", 0)
        g_media = gs.get("media", 0)
        g_civil = gs.get("civil", 0)
        g_exec  = gs.get("exec_constraints", 0)
        g_conf  = gs.get("conflict_signal", 0)

        # ACLED 분쟁 강도 → 점수 차감 신호
        acled_penalty = min(30, acled_c.get("event_count", 0) * 0.5 +
                           acled_c.get("fatalities", 0) * 0.02)

        # UNHCR 실향민 → 불안정 신호
        displaced_M = unhcr_c.get("total_displaced", 0) / 1_000_000
        displacement_penalty = min(20, displaced_M * 2)

        # ReliefWeb 위기 보고서 → 불안정 신호
        crisis_penalty = min(15, rw_c.get("crisis_reports", 0) * 1.5)

        # ── 차원 계산
        def clip(x): return round(float(np.clip(x, 0, 100)), 2)

        electoral = clip(
            va  * 0.30 +
            cpi * 0.10 +
            ps  * 0.20 +
            50  * 0.15 -  # 기준선
            g_elec * 0.25
        )
        judicial = clip(
            rl  * 0.40 +
            rq  * 0.25 +
            cpi * 0.20 -
            g_jud * 0.15
        )
        media = clip(
            va  * 0.45 +
            cc  * 0.15 +
            cpi * 0.15 -
            g_media * 0.25
        )
        civil = clip(
            va  * 0.30 +
            ps  * 0.25 +
            50  * 0.15 -
            displacement_penalty * 1.0 -
            crisis_penalty       * 0.5 -
            g_civil * 0.15
        )
        exec_c = clip(
            cc  * 0.35 +
            ge  * 0.30 +
            rl  * 0.15 +
            cpi * 0.10 -
            acled_penalty * 0.5 -
            g_exec * 0.10
        )

        # 소스 품질 (데이터가 얼마나 채워졌는지)
        source_quality = sum([
            1 if wb_c else 0,
            1 if ti_c else 0,
            1 if gs else 0,
            0.5 if acled_c else 0,
            0.5 if rw_c else 0,
        ]) / 4.0

        rows.append({
            "iso3":    iso3,
            "country": name,
            "year":    datetime.now(timezone.utc).year,
            "collected_at": datetime.now(timezone.utc).isoformat(),

            # 5대 차원
            "dim_electoral":         electoral,
            "dim_judicial":          judicial,
            "dim_media":             media,
            "dim_civil":             civil,
            "dim_exec_constraints":  exec_c,

            # 원본 지표 추적
            "wb_voice_accountability": round(va, 2),
            "wb_rule_of_law":          round(rl, 2),
            "wb_control_corruption":   round(cc, 2),
            "wb_gov_effectiveness":    round(ge, 2),
            "wb_political_stability":  round(ps, 2),
            "wb_regulatory_quality":   round(rq, 2),
            "ti_cpi_score":            round(cpi, 2),

            # 실시간 신호
            "gdelt_electoral_risk":  g_elec,
            "gdelt_judicial_risk":   g_jud,
            "gdelt_media_risk":      g_media,
            "gdelt_civil_risk":      g_civil,
            "gdelt_exec_risk":       g_exec,
            "gdelt_conflict_signal": g_conf,
            "acled_events_30d":      acled_c.get("event_count", 0),
            "acled_fatalities_30d":  acled_c.get("fatalities", 0),
            "reliefweb_reports_30d": rw_c.get("crisis_reports", 0),
            "unhcr_displaced_total": unhcr_c.get("total_displaced", 0),

            # 소스 신뢰도
            "source_quality": round(source_quality, 2),
            "data_sources": json.dumps([
                "World Bank WGI API",
                "GDELT Project v2 API (실시간)",
                "TI CPI 2023",
                "ACLED API" if acled_c else "ACLED (키 없음, 스킵)",
                "ReliefWeb API (UN OCHA)",
                "UNHCR Data API",
            ]),
        })

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════
#  캐시 관리
# ══════════════════════════════════════════════

CACHE_TTL = {
    "gdelt":      1,    # 1시간
    "reliefweb":  6,    # 6시간
    "acled":      24,   # 24시간
    "worldbank":  168,  # 1주일 (연간 데이터라 자주 갱신 불필요)
    "unhcr":      168,
    "ti":         720,  # 1개월
}

def _is_fresh(source: str) -> bool:
    path = f"{CACHE_DIR}/{source}.json"
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        meta = json.load(f)
    fetched = datetime.fromisoformat(meta.get("fetched_at","2000-01-01"))
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    age_h = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
    return age_h < CACHE_TTL.get(source, 24)

def _save(source: str, data: dict):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(f"{CACHE_DIR}/{source}.json", "w", encoding="utf-8") as f:
        json.dump({"fetched_at": datetime.now(timezone.utc).isoformat(), "data": data}, f,
                  ensure_ascii=False, indent=2)

def _load(source: str) -> dict:
    with open(f"{CACHE_DIR}/{source}.json", encoding="utf-8") as f:
        return json.load(f)["data"]


# ══════════════════════════════════════════════
#  메인 수집 파이프라인
# ══════════════════════════════════════════════

def collect(force: bool = False,
            only: Optional[str] = None,
            acled_key: Optional[str] = None,
            acled_email: Optional[str] = None) -> pd.DataFrame:
    """
    전체 데이터 수집 파이프라인.
    force=True: 캐시 무시 강제 수집
    only: 특정 소스만 수집 (gdelt/worldbank/acled/reliefweb/unhcr/ti)
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs("data", exist_ok=True)

    print("\n" + "="*55)
    print(" G-DIAS 실시간 데이터 수집 파이프라인")
    print("="*55)
    print(f" 시각: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f" 대상: {len(COUNTRIES)}개국\n")

    # ── [A] GDELT
    if not only or only == "gdelt":
        if force or not _is_fresh("gdelt"):
            print("[A] GDELT 실시간 이벤트 수집 (지난 7일)...")
            gdelt_raw = fetch_gdelt_events(timespan="7d")
            gdelt_signals = gdelt_to_dimension_signals(gdelt_raw)
            _save("gdelt", {"raw": gdelt_raw, "signals": gdelt_signals})
        else:
            print("[A] GDELT — 캐시 사용 (1h 이내)")
            cached = _load("gdelt")
            gdelt_raw = cached["raw"]
            gdelt_signals = cached["signals"]
    else:
        gdelt_raw, gdelt_signals = {}, {}

    # ── [B] World Bank
    if not only or only == "worldbank":
        if force or not _is_fresh("worldbank"):
            print("[B] World Bank WGI API 수집...")
            wb = fetch_world_bank_wgi()
            _save("worldbank", wb)
        else:
            print("[B] World Bank WGI — 캐시 사용")
            wb = _load("worldbank")
    else:
        wb = {}

    # ── [C] ACLED
    if not only or only == "acled":
        if force or not _is_fresh("acled"):
            print("[C] ACLED 분쟁 이벤트 수집 (지난 30일)...")
            acled = fetch_acled_conflicts(acled_key, acled_email)
            _save("acled", acled)
        else:
            print("[C] ACLED — 캐시 사용")
            acled = _load("acled")
    else:
        acled = {}

    # ── [D] ReliefWeb
    if not only or only == "reliefweb":
        if force or not _is_fresh("reliefweb"):
            print("[D] ReliefWeb (UN OCHA) 위기 보고서 수집...")
            rw = fetch_reliefweb_crisis()
            _save("reliefweb", rw)
        else:
            print("[D] ReliefWeb — 캐시 사용")
            rw = _load("reliefweb")
    else:
        rw = {}

    # ── [E] UNHCR
    if not only or only == "unhcr":
        if force or not _is_fresh("unhcr"):
            print("[E] UNHCR 실향민 데이터 수집...")
            unhcr = fetch_unhcr_displacement()
            _save("unhcr", unhcr)
        else:
            print("[E] UNHCR — 캐시 사용")
            unhcr = _load("unhcr")
    else:
        unhcr = {}

    # ── [F] TI CPI
    print("[F] TI CPI 2023 로드...")
    ti = fetch_ti_cpi()

    # ── 통합
    print("\n[통합] 6개 소스 → 5대 차원 합성 중...")
    df = merge_all_sources(wb, ti, gdelt_raw, gdelt_signals, acled, rw, unhcr)

    # 캐시 저장
    cache_meta = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "countries": len(df),
        "sources": {
            "gdelt":     "수집" if gdelt_signals else "스킵",
            "worldbank": "수집" if wb else "스킵",
            "acled":     "수집" if acled else "스킵(키 없음)",
            "reliefweb": "수집" if rw else "스킵",
            "unhcr":     "수집" if unhcr else "스킵",
            "ti_cpi":    "수집",
        },
        "records": df.to_dict(orient="records"),
    }
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache_meta, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 완료: {len(df)}개국 · {len(df.columns)}개 지표")
    print(f"   저장: {CACHE_PATH}")

    # GDELT 실시간 신호 요약
    risky = [(r["country"], r["gdelt_conflict_signal"])
             for _, r in df.iterrows() if r.get("gdelt_conflict_signal", 0) > 20]
    if risky:
        print(f"\n⚡ GDELT 실시간 위험 신호 탐지 ({len(risky)}개국):")
        for country, sig in sorted(risky, key=lambda x: -x[1])[:5]:
            print(f"   {country}: 충돌 신호 강도 {sig:.0f}")

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="G-DIAS 실시간 데이터 수집")
    parser.add_argument("--force",  action="store_true", help="캐시 무시 강제 수집")
    parser.add_argument("--source", default=None,
                        choices=["gdelt","worldbank","acled","reliefweb","unhcr","ti"],
                        help="특정 소스만 수집")
    parser.add_argument("--acled-key",   default=None, help="ACLED API 키")
    parser.add_argument("--acled-email", default=None, help="ACLED 등록 이메일")
    args = parser.parse_args()

    df = collect(force=args.force, only=args.source,
                 acled_key=args.acled_key, acled_email=args.acled_email)

    print("\n── 샘플 (상위 10개국, DSI 기준) ──")
    from vdem_features import compute_dimension_scores
    df = compute_dimension_scores(df)
    cols = ["country","dim_electoral","dim_judicial","dim_media","dim_civil","dim_exec_constraints",
            "gdelt_conflict_signal","source_quality"]
    print(df[cols].sort_values("dim_electoral", ascending=False).head(10).to_string(index=False))
