"""
ai_report.py - 국가별 AI 민주주의 분석 보고서 생성

Anthropic Claude API를 사용해 각 국가의 DSI 데이터를 기반으로
전문적인 분석 보고서를 생성.
"""

import json
import os
import requests
from dataclasses import dataclass
from typing import Optional


@dataclass
class CountryReport:
    iso3: str
    country: str
    dsi: float
    dims: dict
    alerts: list
    report_ko: str       # 한국어 보고서
    risk_level: str      # STABLE / CAUTION / WARNING / CRITICAL
    key_findings: list   # 핵심 발견사항 3개
    recommendations: list  # 권고사항 2개


def _call_claude(prompt: str, max_tokens: int = 1000) -> str:
    """Anthropic API 직접 호출"""
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"Content-Type": "application/json"},
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    data = response.json()
    return data["content"][0]["text"]


def generate_country_report(
    country: str,
    iso3: str,
    dsi: float,
    dims: dict,
    alerts: list,
    global_avg: float,
) -> CountryReport:
    """
    단일 국가 AI 분석 보고서 생성.
    dims: {electoral, judicial, media, civil, exec_constraints} → 0~100
    alerts: [{"severity": ..., "title": ..., "message": ...}, ...]
    """

    dim_labels = {
        "electoral":        "선거 무결성",
        "judicial":         "사법 독립성",
        "media":            "언론 자유",
        "civil":            "시민사회",
        "exec_constraints": "행정부 견제",
    }

    dims_text = "\n".join(
        f"  - {dim_labels.get(k, k)}: {v:.1f}/100"
        for k, v in dims.items()
    )
    alerts_text = "\n".join(
        f"  - [{a.get('severity','?')}] {a.get('title','')}: {a.get('message','')}"
        for a in alerts
    ) if alerts else "  - 없음"

    # 위험 수준 판단
    if dsi < 30:
        risk_level = "CRITICAL"
    elif dsi < 45:
        risk_level = "WARNING"
    elif dsi < 65:
        risk_level = "CAUTION"
    else:
        risk_level = "STABLE"

    prompt = f"""당신은 V-Dem 데이터 기반 민주주의 분석 전문가입니다.
아래 데이터를 바탕으로 {country}의 민주주의 현황을 분석하세요.

## 입력 데이터
- 국가: {country} ({iso3})
- DSI 종합 점수: {dsi:.1f}/100 (글로벌 평균: {global_avg:.1f})
- 위험 수준: {risk_level}

## 5대 차원 점수
{dims_text}

## 활성 경보
{alerts_text}

## 출력 형식 (JSON만 출력, 다른 텍스트 없이)
{{
  "summary": "2~3문장 핵심 요약 (현재 상태, 주요 강점/약점)",
  "analysis": "4~5문장 상세 분석 (차원별 해석, 지역/역사적 맥락, 추세)",
  "key_findings": [
    "핵심 발견 1 (구체적 수치 포함)",
    "핵심 발견 2 (구체적 수치 포함)",
    "핵심 발견 3 (구체적 수치 포함)"
  ],
  "recommendations": [
    "정책 권고사항 1",
    "정책 권고사항 2"
  ],
  "outlook": "1문장 향후 전망"
}}"""

    try:
        raw = _call_claude(prompt, max_tokens=800)
        # JSON 파싱
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())

        report_ko = (
            f"**요약**\n{data.get('summary', '')}\n\n"
            f"**상세 분석**\n{data.get('analysis', '')}\n\n"
            f"**향후 전망**\n{data.get('outlook', '')}"
        )

        return CountryReport(
            iso3=iso3,
            country=country,
            dsi=dsi,
            dims=dims,
            alerts=alerts,
            report_ko=report_ko,
            risk_level=risk_level,
            key_findings=data.get("key_findings", []),
            recommendations=data.get("recommendations", []),
        )

    except Exception as e:
        # API 실패 시 규칙 기반 폴백
        return _fallback_report(country, iso3, dsi, dims, alerts, risk_level, global_avg, str(e))


def _fallback_report(country, iso3, dsi, dims, alerts, risk_level, global_avg, err="") -> CountryReport:
    """API 실패 시 규칙 기반 보고서"""
    dim_labels = {
        "electoral": "선거 무결성", "judicial": "사법 독립성",
        "media": "언론 자유", "civil": "시민사회", "exec_constraints": "행정부 견제"
    }
    sorted_dims = sorted(dims.items(), key=lambda x: x[1])
    weakest = dim_labels.get(sorted_dims[0][0], sorted_dims[0][0])
    strongest = dim_labels.get(sorted_dims[-1][0], sorted_dims[-1][0])
    gap = dsi - global_avg

    risk_desc = {
        "STABLE":   "안정적인 민주주의 체제를 유지하고 있습니다.",
        "CAUTION":  "일부 민주주의 지표에서 우려가 관찰됩니다.",
        "WARNING":  "민주주의 후퇴 위험이 높은 상태입니다.",
        "CRITICAL": "심각한 민주주의 위기 상황입니다.",
    }[risk_level]

    summary = (
        f"{country}는 DSI {dsi:.1f}점으로 글로벌 평균({global_avg:.1f})보다 "
        f"{'높은' if gap >= 0 else '낮은'} 수준입니다. {risk_desc}"
    )
    analysis = (
        f"5대 차원 중 {strongest}({dims[sorted_dims[-1][0]]:.1f}점)이 가장 양호하며, "
        f"{weakest}({dims[sorted_dims[0][0]]:.1f}점)이 가장 취약한 영역으로 나타났습니다. "
        f"{'경보가 감지되어 지속적인 모니터링이 필요합니다.' if alerts else '현재 특이 경보는 없습니다.'}"
    )

    return CountryReport(
        iso3=iso3, country=country, dsi=dsi, dims=dims, alerts=alerts,
        report_ko=f"**요약**\n{summary}\n\n**상세 분석**\n{analysis}",
        risk_level=risk_level,
        key_findings=[
            f"DSI 종합 점수 {dsi:.1f}/100 (글로벌 평균 대비 {gap:+.1f})",
            f"최강점: {strongest} {dims[sorted_dims[-1][0]]:.1f}점",
            f"최약점: {weakest} {dims[sorted_dims[0][0]]:.1f}점",
        ],
        recommendations=[
            f"{weakest} 분야 제도적 강화 필요",
            "국제 민주주의 지수 정기 모니터링 권고",
        ],
    )


def generate_global_summary(df, all_alerts: list, global_avg: float) -> str:
    """전체 글로벌 현황 AI 요약"""
    critical_countries = df[df["dsi"] < 30]["country"].tolist() if "country" in df.columns else []
    declining = [a for a in all_alerts if (a.get("severity") if isinstance(a, dict) else getattr(a, "severity", "")) == "CRITICAL"]

    prompt = f"""민주주의 분석 전문가로서 현재 글로벌 민주주의 현황을 요약하세요.

데이터:
- 모니터링 국가: {len(df)}개국
- 글로벌 평균 DSI: {global_avg:.1f}/100
- 위기 국가 (DSI<30): {', '.join(critical_countries) if critical_countries else '없음'}
- 총 CRITICAL 경보: {len(declining)}건
- 고위험 국가 (DSI<45): {(df['dsi'] < 45).sum()}개국

3~4문장으로 현재 글로벌 민주주의 동향을 전문적으로 요약하세요. JSON 없이 텍스트만 출력."""

    try:
        return _call_claude(prompt, max_tokens=300)
    except:
        return (
            f"현재 {len(df)}개국을 모니터링 중이며 글로벌 평균 DSI는 {global_avg:.1f}점입니다. "
            f"{'위기 국가(' + ', '.join(critical_countries) + ')에서 심각한 민주주의 후퇴가 관찰됩니다.' if critical_countries else ''} "
            f"총 {len(declining)}건의 CRITICAL 경보가 활성화되어 있어 지속적인 모니터링이 필요합니다."
        )
