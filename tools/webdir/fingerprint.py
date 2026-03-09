from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class FingerRule:
    name: str
    paths: List[str]
    headers: Dict[str, List[str]]
    keywords: List[str]


def _as_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    if isinstance(v, str):
        return [x.strip() for x in v.split(",") if x.strip()]
    return []


def load_finger_rules(raw: Dict[str, Any]) -> List[FingerRule]:
    rules: List[FingerRule] = []
    for name, value in (raw or {}).items():
        if isinstance(value, list):
            rules.append(FingerRule(name=str(name), paths=_as_list(value), headers={}, keywords=[]))
            continue
        if isinstance(value, dict):
            paths = _as_list(value.get("paths"))
            keywords = _as_list(value.get("keywords"))
            headers_raw = value.get("headers") or {}
            headers: Dict[str, List[str]] = {}
            if isinstance(headers_raw, dict):
                for hk, hv in headers_raw.items():
                    headers[str(hk).lower()] = _as_list(hv)
            rules.append(
                FingerRule(
                    name=str(name),
                    paths=paths,
                    headers=headers,
                    keywords=keywords,
                )
            )
            continue
    return rules


def match_finger_rules(
    rules: Iterable[FingerRule],
    *,
    path: str,
    headers: Dict[str, str],
    body: str,
) -> List[str]:
    path_norm = (path or "").rstrip("/") or "/"
    hdr_lower = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    body = body or ""

    hits: List[str] = []
    for r in rules:
        hit = False

        for p in r.paths:
            p_norm = (p or "").strip()
            if not p_norm:
                continue
            if not p_norm.startswith("/"):
                p_norm = "/" + p_norm
            if (p_norm.rstrip("/") or "/") == path_norm:
                hit = True
                break

        if not hit and r.headers:
            for hk, patterns in r.headers.items():
                hv = hdr_lower.get(hk, "")
                if not hv:
                    continue
                for pat in patterns:
                    if pat and pat.lower() in hv.lower():
                        hit = True
                        break
                if hit:
                    break

        if not hit and r.keywords:
            for kw in r.keywords:
                if kw and kw in body:
                    hit = True
                    break

        if hit:
            hits.append(r.name)

    return hits


def quick_header_heuristics(headers: Dict[str, str]) -> List[str]:
    """
    轻量级框架/组件识别（不依赖指纹库），避免太“玄学”，只做高置信度命中。
    """
    hdr = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    hits: List[str] = []

    server = hdr.get("server", "")
    xpb = hdr.get("x-powered-by", "")
    set_cookie = hdr.get("set-cookie", "")

    if "nginx" in server.lower():
        hits.append("Nginx")
    if "apache" in server.lower():
        hits.append("Apache")
    if "iis" in server.lower():
        hits.append("IIS")
    if "tomcat" in server.lower():
        hits.append("Tomcat")

    if "php" in xpb.lower():
        hits.append("PHP")
    if "asp.net" in xpb.lower():
        hits.append("ASP.NET")

    if "jenkins" in set_cookie.lower():
        hits.append("Jenkins")

    # 去重保持顺序
    seen = set()
    uniq: List[str] = []
    for x in hits:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)
    return uniq

