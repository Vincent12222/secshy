import queue
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import requests
import urllib3
import yaml

from fingerprint import load_finger_rules, match_finger_rules, quick_header_heuristics
from proxy_pool import ProxyPool, load_proxies
from ua_pool import load_ua_list, pick_random_ua


@dataclass
class DirScanSettings:
    method: str = "GET"
    recursion: bool = True
    recursion_mode: str = "dir_listing"  # dir_listing | html_links
    max_depth: int = 2
    max_enqueue: int = 5000
    ext_filter: List[str] = None
    code_filter: List[str] = None
    key_filter: str = ""
    len_filter: str = ""
    file_exts: List[str] = None
    delay: float = 0.0
    threads: int = 50
    timeout_ms: int = 15000
    user_agent: str = "Mozilla/5.0 webdir-scanner"
    random_ua: bool = False
    ua_file: Optional[str] = None
    proxy_enable: bool = False
    proxy_file: Optional[str] = None
    proxy_test_url: Optional[str] = None
    proxy_timeout_ms: int = 5000
    proxy_validate_threads: int = 20
    framework_detect: bool = True


def _default_settings() -> DirScanSettings:
    return DirScanSettings(
        method="GET",
        recursion=True,
        recursion_mode="dir_listing",
        max_depth=2,
        max_enqueue=5000,
        ext_filter=["js", "gif", "jpg", "png", "css"],
        code_filter=["400", "404", "5xx"],
        key_filter="",
        len_filter="",
        file_exts=["jsp", "php", "asp", "aspx"],
        delay=0.0,
        threads=50,
        timeout_ms=15000,
        user_agent="Mozilla/5.0 webdir-scanner",
        random_ua=False,
        ua_file=None,
        proxy_enable=False,
        proxy_file=None,
        proxy_test_url=None,
        proxy_timeout_ms=5000,
        proxy_validate_threads=20,
        framework_detect=True,
    )


def load_config(
    cfg_path: Optional[str] = None,
    finger_path: Optional[str] = None,
) -> Tuple[DirScanSettings, Dict[str, Any]]:
    """
    从当前 webdir 目录下的 config.yaml / FingerDir.yaml 读取配置。
    不再依赖 TscanPlus 原始项目结构。
    """
    base_dir = Path(__file__).resolve().parent

    cfg_file = Path(cfg_path) if cfg_path else base_dir / "config.yaml"
    finger_file = Path(finger_path) if finger_path else base_dir / "FingerDir.yaml"

    settings = _default_settings()

    if cfg_file.is_file():
        with cfg_file.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        settings.method = str(cfg.get("DirSelectMethod", settings.method)).upper()
        settings.recursion = bool(cfg.get("DirRecursion", settings.recursion))
        settings.recursion_mode = str(cfg.get("DirRecursionMode", settings.recursion_mode) or settings.recursion_mode)
        settings.max_depth = int(cfg.get("DirMaxDepth", settings.max_depth) or settings.max_depth)
        settings.max_enqueue = int(cfg.get("DirMaxEnqueue", settings.max_enqueue) or settings.max_enqueue)
        settings.ext_filter = [
            e.strip() for e in str(cfg.get("DirExtFilter", ",".join(settings.ext_filter))).split(",") if e.strip()
        ]
        settings.code_filter = [
            c.strip() for c in str(cfg.get("DirCodeFilter", ",".join(settings.code_filter))).split(",") if c.strip()
        ]
        settings.key_filter = str(cfg.get("DirKeyFilter", settings.key_filter)).strip()
        settings.len_filter = str(cfg.get("DirLenFilter", settings.len_filter)).strip()
        settings.file_exts = [
            e.strip() for e in str(cfg.get("DirFileExt", ",".join(settings.file_exts))).split(",") if e.strip()
        ]
        settings.delay = float(cfg.get("DirTimeDelayStr", settings.delay) or 0)
        settings.threads = int(cfg.get("DirThreadStr", settings.threads) or settings.threads)
        settings.timeout_ms = int(cfg.get("CfgWebTimeout", settings.timeout_ms) or settings.timeout_ms)
        settings.user_agent = str(cfg.get("Cfguatxt", settings.user_agent))
        settings.random_ua = bool(cfg.get("RandomUAEnable", settings.random_ua))
        settings.ua_file = cfg.get("UAFile", settings.ua_file)
        settings.proxy_enable = bool(cfg.get("ProxyEnable", settings.proxy_enable))
        settings.proxy_file = cfg.get("ProxyFile", settings.proxy_file)
        settings.proxy_test_url = cfg.get("ProxyTestUrl", settings.proxy_test_url)
        settings.proxy_timeout_ms = int(cfg.get("ProxyTimeoutMs", settings.proxy_timeout_ms) or settings.proxy_timeout_ms)
        settings.proxy_validate_threads = int(
            cfg.get("ProxyValidateThreads", settings.proxy_validate_threads) or settings.proxy_validate_threads
        )
        settings.framework_detect = bool(cfg.get("FrameworkDetectEnable", settings.framework_detect))

    finger: Dict[str, Any] = {}
    if finger_file.is_file():
        with finger_file.open("r", encoding="utf-8") as f:
            finger = yaml.safe_load(f) or {}

    return settings, finger


def build_finger_paths(finger: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    兼容旧版 FingerDir.yaml（值为 list[path]）。
    新版（值为 dict）由 fingerprint.py 负责更丰富的匹配逻辑。
    """
    return {
        str(name): [str(p) for p in paths]
        for name, paths in (finger or {}).items()
        if isinstance(paths, list)
    }


def status_code_in_filter(code: int, filters: List[str]) -> bool:
    code_str = str(code)
    for f in filters:
        f = f.strip()
        if not f:
            continue
        if f.lower().endswith("xx"):
            if code_str.startswith(f[0]):
                return True
        elif f.lower() == "5xx":
            if 500 <= code < 600:
                return True
        else:
            try:
                if int(f) == code:
                    return True
            except ValueError:
                continue
    return False


@dataclass(frozen=True)
class ScanResult:
    status: int
    url: str
    path: str
    tags: List[str]
    frameworks: List[str]
    content_type: str
    depth: int


class AdjustableLimiter:
    def __init__(self, limit: int):
        self._cond = threading.Condition()
        self._limit = max(1, int(limit))
        self._active = 0

    def set_limit(self, limit: int) -> None:
        with self._cond:
            self._limit = max(1, int(limit))
            self._cond.notify_all()

    def acquire(self, stop_event: threading.Event) -> bool:
        with self._cond:
            while not stop_event.is_set() and self._active >= self._limit:
                self._cond.wait(timeout=0.2)
            if stop_event.is_set():
                return False
            self._active += 1
            return True

    def release(self) -> None:
        with self._cond:
            self._active = max(0, self._active - 1)
            self._cond.notify_all()


_HREF_RE = re.compile(r"""href\s*=\s*["']([^"'#]+)""", re.IGNORECASE)


def _extract_links(html: str) -> List[str]:
    if not html:
        return []
    return [m.group(1).strip() for m in _HREF_RE.finditer(html) if m.group(1).strip()]


def _normalize_path(p: str) -> Optional[str]:
    if not p:
        return None
    p = p.strip()
    if not p:
        return None
    if not p.startswith("/"):
        p = "/" + p
    u = urlparse(p)
    return u.path or "/"


class DirScanner:
    def __init__(
        self,
        base_url: str,
        settings: DirScanSettings,
        dict_paths: List[str],
        finger_paths: Dict[str, List[str]],
        finger_rules: Iterable,
        verify_ssl: bool,
        limiter: AdjustableLimiter,
        proxy_pool: Optional[ProxyPool],
        ua_list: List[str],
        on_result: Optional[Callable[[str], None]] = None,
        on_scan_result: Optional[Callable[[ScanResult], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ):
        if not base_url.startswith("http"):
            base_url = "http://" + base_url
        self.base_url = base_url.rstrip("/")
        self.base_origin = urlparse(self.base_url).netloc
        self.settings = settings
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.user_agent})

        self.dict_paths = dict_paths
        self.finger_paths = finger_paths
        self.finger_rules = list(finger_rules or [])
        self.limiter = limiter
        self.proxy_pool = proxy_pool
        self.ua_list = ua_list or []

        self.queue: "queue.Queue[Tuple[str, int]]" = queue.Queue()
        self.visited: Set[str] = set()
        self.lock = threading.Lock()
        self.enqueued_count = 0

        self.on_result = on_result
        self.on_scan_result = on_scan_result
        self.stop_event = stop_event or threading.Event()

    def enqueue_initial(self):
        for p in self.dict_paths:
            self._enqueue_path(p, depth=0)
        for _, paths in self.finger_paths.items():
            for p in paths:
                self._enqueue_path(p, depth=0)

    def _enqueue_path(self, path: str, depth: int):
        path = path.strip()
        if not path:
            return
        if not path.startswith("/"):
            path = "/" + path
        if self.settings.recursion and depth > self.settings.max_depth:
            return
        with self.lock:
            if path in self.visited:
                return
            self.visited.add(path)
            if self.settings.max_enqueue and self.enqueued_count >= self.settings.max_enqueue:
                return
            self.enqueued_count += 1
        self.queue.put((path, depth))

    def worker(self):
        while not self.stop_event.is_set():
            try:
                path, depth = self.queue.get_nowait()
            except queue.Empty:
                return
            try:
                self.scan_path(path, depth)
            finally:
                self.queue.task_done()

    def _iter_exts(self, path: str) -> List[str]:
        if (path or "").endswith("/"):
            return [""]
        last = (path or "").split("/")[-1]
        if "." in last and not last.endswith("."):
            return [""]
        exts = [""]
        if self.settings.file_exts:
            exts.extend(["." + e for e in self.settings.file_exts])
        return exts

    def scan_path(self, path: str, depth: int):
        exts = self._iter_exts(path)
        for ext in exts:
            if self.stop_event.is_set():
                return

            url = f"{self.base_url}{path}{ext}"
            try:
                if not self.limiter.acquire(self.stop_event):
                    return

                proxy_dict = None
                proxy_url = None
                if self.proxy_pool:
                    proxy_dict = self.proxy_pool.get_random_proxy()
                    if proxy_dict:
                        proxy_url = proxy_dict.get("http")

                headers = {}
                if self.settings.random_ua:
                    headers["User-Agent"] = pick_random_ua(self.ua_list, self.settings.user_agent)

                resp = self.session.request(
                    self.settings.method,
                    url,
                    timeout=self.settings.timeout_ms / 1000.0,
                    allow_redirects=False,
                    verify=self.verify_ssl,
                    proxies=proxy_dict,
                    headers=headers or None,
                )
            except requests.RequestException as e:
                if self.on_result:
                    self.on_result(f"[ERR] {url} - {e}")
                if self.proxy_pool and proxy_url:
                    self.proxy_pool.report_failure(proxy_url)
                continue
            finally:
                self.limiter.release()

            if self.proxy_pool and proxy_url:
                self.proxy_pool.report_success(proxy_url)

            if self.settings.code_filter and status_code_in_filter(resp.status_code, self.settings.code_filter):
                continue

            content_type = resp.headers.get("Content-Type", "")
            if self.settings.ext_filter and any(
                url.lower().endswith("." + ext_name) for ext_name in self.settings.ext_filter
            ):
                continue

            body = resp.text or ""
            if self.settings.key_filter and self.settings.key_filter not in body:
                continue

            if self.settings.len_filter:
                try:
                    min_len = int(self.settings.len_filter)
                    if len(body) < min_len:
                        continue
                except ValueError:
                    pass

            tags = []
            if any(k in body for k in ["Directory listing for", "Parent Directory", "Index of", "folder listing:"]):
                tags.append("目录枚举点")

            for name, paths in self.finger_paths.items():
                for fp in paths:
                    if fp.rstrip("/") == path.rstrip("/"):
                        tags.append(f"指纹:{name}")
                        break

            frameworks: List[str] = []
            if self.settings.framework_detect:
                frameworks.extend(match_finger_rules(self.finger_rules, path=path, headers=dict(resp.headers), body=body))
                frameworks.extend(quick_header_heuristics(dict(resp.headers)))
                seen_fw: Set[str] = set()
                frameworks = [x for x in frameworks if not (x in seen_fw or seen_fw.add(x))]

            tag_str = f" [{' '.join(tags)}]" if tags else ""
            fw_str = f" <{', '.join(frameworks)}>" if frameworks else ""
            line = f"{resp.status_code} {url}{tag_str}{fw_str}"
            if self.on_result:
                self.on_result(line)
            if self.on_scan_result:
                self.on_scan_result(
                    ScanResult(
                        status=int(resp.status_code),
                        url=url,
                        path=path,
                        tags=list(tags),
                        frameworks=list(frameworks),
                        content_type=str(content_type),
                        depth=int(depth),
                    )
                )

            if self.settings.recursion and resp.status_code == 200 and content_type.startswith("text/"):
                self._maybe_enqueue_children(
                    url=url,
                    base_path=path,
                    depth=depth,
                    content_type=content_type,
                    body=body,
                    tags=tags,
                )

            if self.settings.delay > 0:
                time.sleep(self.settings.delay)

    def _maybe_enqueue_children(
        self,
        *,
        url: str,
        base_path: str,
        depth: int,
        content_type: str,
        body: str,
        tags: List[str],
    ) -> None:
        if depth >= self.settings.max_depth:
            return

        is_dir_listing = "目录枚举点" in tags
        mode = (self.settings.recursion_mode or "dir_listing").strip().lower()

        if mode == "dir_listing" and not is_dir_listing:
            return
        if mode not in {"dir_listing", "html_links"}:
            mode = "dir_listing"
            if not is_dir_listing:
                return

        if "html" not in (content_type or "").lower() and not is_dir_listing:
            return

        links = _extract_links(body)
        if not links:
            return

        base_for_join = url if url.endswith("/") else (url + "/")
        for href in links:
            if self.stop_event.is_set():
                return
            href = href.strip()
            if not href or href.startswith(("javascript:", "mailto:")):
                continue

            joined = urljoin(base_for_join, href)
            pu = urlparse(joined)
            if pu.netloc and pu.netloc != self.base_origin:
                continue

            new_path = _normalize_path(pu.path or "/")
            if not new_path:
                continue

            # 收敛：目录优先；文件只探测一次（不会继续扩散）
            if new_path.endswith("/"):
                self._enqueue_path(new_path, depth=depth + 1)
            else:
                self._enqueue_path(new_path, depth=min(depth + 1, self.settings.max_depth))


def load_dict_from_file(path: Optional[str]) -> List[str]:
    if not path:
        return []
    lines: List[str] = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                lines.append(line)
    except FileNotFoundError:
        pass
    return lines


def load_builtin_dicts() -> List[str]:
    """
    加载 webdir/DirDict 目录下的所有字典，行为尽量贴近原版：
    - 每个 .txt 文件按行读取
    - 忽略空行和以 # 开头的注释行
    """
    base_dir = Path(__file__).resolve().parent
    dict_dir = base_dir / "DirDict"
    paths: List[str] = []

    if not dict_dir.is_dir():
        return paths

    for txt in sorted(dict_dir.glob("*.txt")):
        paths.extend(load_dict_from_file(str(txt)))

    # 去重，保持顺序
    seen: Set[str] = set()
    unique_paths: List[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique_paths.append(p)
    return unique_paths


def run_scan(
    url: str,
    config_path: Optional[str],
    finger_path: Optional[str],
    dict_file: Optional[str],
    threads_override: Optional[int],
    insecure: bool,
    on_result: Callable[[str], None],
    stop_event: threading.Event,
    on_scan_result: Optional[Callable[[ScanResult], None]] = None,
    on_log: Optional[Callable[[str], None]] = None,
    concurrency_getter: Optional[Callable[[], int]] = None,
    settings_override: Optional[Dict[str, Any]] = None,
) -> None:
    if insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    settings, finger = load_config(config_path, finger_path)
    if threads_override:
        settings.threads = threads_override

    # GUI 覆盖（优先级最高）
    if settings_override:
        for k, v in settings_override.items():
            if not hasattr(settings, k):
                continue
            setattr(settings, k, v)

    finger_paths = build_finger_paths(finger)
    finger_rules = load_finger_rules(finger)
    ua_list = load_ua_list(settings.ua_file)

    dict_paths: List[str] = []
    if dict_file:
        dict_paths.extend(load_dict_from_file(dict_file))
    if not dict_paths:
        # 若未指定自定义字典，则自动加载 webdir/DirDict 下的所有字典
        dict_paths = load_builtin_dicts()
    if not dict_paths:
        # 兜底内置少量常见路径，防止完全为空
        dict_paths = [
            "/",
            "/login",
            "/admin",
            "/manage",
            "/console",
            "/portal",
            "/web",
        ]

    proxy_pool: Optional[ProxyPool] = None
    if settings.proxy_enable:
        proxies = load_proxies(settings.proxy_file)
        if not proxies:
            if on_log:
                on_log("[!] 代理池已启用，但未加载到任何代理（将退回直连）。")
        else:
            test_url = settings.proxy_test_url or (url if url.startswith("http") else ("http://" + url))
            proxy_pool = ProxyPool(
                proxies=proxies,
                test_url=test_url,
                timeout_ms=settings.proxy_timeout_ms,
                validate_threads=settings.proxy_validate_threads,
            )
            if on_log:
                on_log(f"[*] 代理池：加载 {proxy_pool.size()} 条代理，开始可用性检测...")
            proxy_pool.warmup()
            ok, total = proxy_pool.summary()
            if on_log:
                on_log(f"[*] 代理池：可用 {ok}/{total}")
            if proxy_pool.size() == 0:
                proxy_pool = None

    limiter = AdjustableLimiter(limit=settings.threads)
    if concurrency_getter:
        try:
            limiter.set_limit(int(concurrency_getter()))
        except Exception:  # noqa: BLE001
            pass
    if concurrency_getter:
        def limiter_sync():
            while not stop_event.is_set():
                try:
                    limiter.set_limit(int(concurrency_getter()))
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(0.2)

        threading.Thread(target=limiter_sync, daemon=True).start()

    scanner = DirScanner(
        base_url=url,
        settings=settings,
        dict_paths=dict_paths,
        finger_paths=finger_paths,
        finger_rules=finger_rules,
        verify_ssl=not insecure,
        limiter=limiter,
        proxy_pool=proxy_pool,
        ua_list=ua_list,
        on_result=on_result,
        on_scan_result=on_scan_result,
        stop_event=stop_event,
    )
    scanner.enqueue_initial()

    threads: List[threading.Thread] = []
    for _ in range(settings.threads):
        t = threading.Thread(target=scanner.worker, daemon=True)
        t.start()
        threads.append(t)

    scanner.queue.join()


