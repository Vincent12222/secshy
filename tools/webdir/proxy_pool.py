import random
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests


@dataclass
class ProxyStat:
    proxy: str
    ok: bool = False
    fail_count: int = 0
    last_checked_ts: float = 0.0
    last_fail_ts: float = 0.0


def _normalize_proxy(line: str) -> Optional[str]:
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    if "://" not in s:
        # default http
        s = "http://" + s
    return s


def load_proxies(path: Optional[str]) -> List[str]:
    if not path:
        return []
    p = Path(path)
    if not p.is_file():
        return []
    proxies: List[str] = []
    with p.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            proxy = _normalize_proxy(line)
            if proxy:
                proxies.append(proxy)
    # de-dup keep order
    seen = set()
    uniq: List[str] = []
    for x in proxies:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)
    return uniq


class ProxyPool:
    """
    - 读取代理列表
    - 启动前做一次并发可用性探测
    - 扫描时随机轮换代理；失败达到阈值自动剔除（可继续保留以便后续重测）
    """

    def __init__(
        self,
        proxies: List[str],
        test_url: str,
        timeout_ms: int = 5000,
        validate_threads: int = 20,
        max_fail_before_bad: int = 2,
    ):
        self._lock = threading.Lock()
        self._stats: Dict[str, ProxyStat] = {p: ProxyStat(proxy=p) for p in proxies}
        self.test_url = test_url
        self.timeout_ms = timeout_ms
        self.validate_threads = max(1, int(validate_threads))
        self.max_fail_before_bad = max(1, int(max_fail_before_bad))

    def size(self) -> int:
        with self._lock:
            return len(self._stats)

    def summary(self) -> Tuple[int, int]:
        with self._lock:
            ok = sum(1 for s in self._stats.values() if s.ok)
            total = len(self._stats)
        return ok, total

    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        with self._lock:
            ok_list = [s.proxy for s in self._stats.values() if s.ok]
            if not ok_list:
                return None
            proxy = random.choice(ok_list)
        return {"http": proxy, "https": proxy}

    def report_success(self, proxy_url: Optional[str]) -> None:
        if not proxy_url:
            return
        with self._lock:
            st = self._stats.get(proxy_url)
            if not st:
                return
            st.ok = True
            st.fail_count = 0
            st.last_checked_ts = time.time()

    def report_failure(self, proxy_url: Optional[str]) -> None:
        if not proxy_url:
            return
        with self._lock:
            st = self._stats.get(proxy_url)
            if not st:
                return
            st.fail_count += 1
            st.last_fail_ts = time.time()
            st.last_checked_ts = time.time()
            if st.fail_count >= self.max_fail_before_bad:
                st.ok = False

    def warmup(self) -> None:
        proxies = list(self._stats.keys())
        if not proxies:
            return

        q: List[str] = proxies[:]
        q_lock = threading.Lock()

        def pop_one() -> Optional[str]:
            with q_lock:
                if not q:
                    return None
                return q.pop()

        def worker():
            while True:
                p = pop_one()
                if not p:
                    return
                ok = self._test_proxy(p)
                with self._lock:
                    st = self._stats.get(p)
                    if not st:
                        continue
                    st.ok = ok
                    st.last_checked_ts = time.time()
                    st.fail_count = 0 if ok else max(st.fail_count, 1)
                    if not ok:
                        st.last_fail_ts = time.time()

        threads: List[threading.Thread] = []
        for _ in range(min(self.validate_threads, len(proxies))):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

    def _test_proxy(self, proxy: str) -> bool:
        proxies = {"http": proxy, "https": proxy}
        try:
            resp = requests.get(
                self.test_url,
                timeout=self.timeout_ms / 1000.0,
                proxies=proxies,
                verify=False,
                allow_redirects=False,
                headers={"User-Agent": "Mozilla/5.0 webdir-proxy-check"},
            )
            return 100 <= int(resp.status_code) < 600
        except requests.RequestException:
            return False

