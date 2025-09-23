from __future__ import annotations

import json
import re
from contextvars import ContextVar
from http.cookies import SimpleCookie
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from werkzeug.exceptions import HTTPException


__all__ = [
    "Flask",
    "Blueprint",
    "request",
    "g",
    "jsonify",
    "abort",
    "Response",
]


_request_var: ContextVar[Request] = ContextVar("flask_request")  # type: ignore[name-defined]
_g_var: ContextVar[SimpleNamespace] = ContextVar("flask_g")


class Request:
    def __init__(
        self,
        method: str,
        path: str,
        json_data: Any = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
    ) -> None:
        self.method = method.upper()
        self.path = path
        self._json = json_data
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.args: Dict[str, str] = {}

    def get_json(self, silent: bool = False) -> Any:
        if self._json is None:
            if silent:
                return None
            raise ValueError("No JSON body present")
        return self._json

    @property
    def json(self) -> Any:
        return self.get_json(silent=True)


class _RequestProxy:
    def __getattr__(self, name: str) -> Any:  # pragma: no cover - simple proxy
        return getattr(_request_var.get(), name)

    def get_json(self, *args: Any, **kwargs: Any) -> Any:
        return _request_var.get().get_json(*args, **kwargs)


request = _RequestProxy()


class _GProxy:
    def __getattr__(self, name: str) -> Any:  # pragma: no cover - simple proxy
        return getattr(_g_var.get(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(_g_var.get(), name, value)

    def __delattr__(self, name: str) -> None:
        delattr(_g_var.get(), name)

    def pop(self, name: str, default: Any = None) -> Any:
        namespace = _g_var.get()
        if hasattr(namespace, name):
            value = getattr(namespace, name)
            delattr(namespace, name)
            return value
        return default

    def __contains__(self, name: str) -> bool:  # pragma: no cover - simple helper
        return hasattr(_g_var.get(), name)


g = _GProxy()


class Headers(dict):
    def __setitem__(self, key: str, value: str) -> None:
        super().__setitem__(key.lower(), value)

    def __getitem__(self, key: str) -> str:  # pragma: no cover - thin wrapper
        return super().__getitem__(key.lower())

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return super().get(key.lower(), default)

    def update(self, other: Dict[str, str]) -> None:  # pragma: no cover - simple wrapper
        for key, value in other.items():
            self[key] = value


class Response:
    def __init__(
        self,
        data: Any = "",
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.data = b""
        self.status_code = status
        self.headers = Headers()
        if headers:
            self.headers.update(headers)
        self.set_data(data)

    def set_data(self, data: Any) -> None:
        if isinstance(data, bytes):
            self.data = data
        else:
            if data is None:
                data = ""
            self.data = str(data).encode("utf-8")

    def get_data(self, as_text: bool = False) -> Any:
        return self.data.decode("utf-8") if as_text else self.data

    def get_json(self) -> Any:
        if not self.data:
            return None
        return json.loads(self.data.decode("utf-8"))

    @property
    def json(self) -> Any:  # pragma: no cover - helper alias
        return self.get_json()

    @property
    def text(self) -> str:  # pragma: no cover - helper alias
        return self.get_data(as_text=True)

    def set_cookie(
        self,
        key: str,
        value: str = "",
        *,
        max_age: Optional[int] = None,
        path: str = "/",
        httponly: bool = False,
        samesite: Optional[str] = None,
        secure: bool = False,
    ) -> None:
        cookie = SimpleCookie()
        cookie[key] = value
        morsel = cookie[key]
        if path:
            morsel["path"] = path
        if max_age is not None:
            morsel["max-age"] = str(max_age)
        if httponly:
            morsel["httponly"] = True
        if samesite:
            morsel["samesite"] = samesite
        if secure:
            morsel["secure"] = True
        header_value = cookie.output(header="").strip()
        existing = self.headers.get("set-cookie")
        if existing:
            header_value = f"{existing}, {header_value}"
        self.headers["Set-Cookie"] = header_value

    def delete_cookie(
        self,
        key: str,
        *,
        path: str = "/",
        httponly: bool = False,
        samesite: Optional[str] = None,
        secure: bool = False,
    ) -> None:
        cookie = SimpleCookie()
        cookie[key] = ""
        morsel = cookie[key]
        if path:
            morsel["path"] = path
        morsel["max-age"] = "0"
        morsel["expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
        if httponly:
            morsel["httponly"] = True
        if samesite:
            morsel["samesite"] = samesite
        if secure:
            morsel["secure"] = True
        self.headers["Set-Cookie"] = cookie.output(header="").strip()


def jsonify(*args: Any, **kwargs: Any) -> Response:
    if args and kwargs:
        raise TypeError("jsonify() accepts either args or kwargs, not both")
    if kwargs:
        payload = kwargs
    elif len(args) == 1:
        payload = args[0]
    else:
        payload = list(args)
    return Response(json.dumps(payload, ensure_ascii=False), headers={"Content-Type": "application/json"})


def abort(code: int, description: Optional[str] = None) -> None:
    raise HTTPException(description=description, code=code)


class Route:
    def __init__(self, methods: List[str], rule: str, view_func: Callable[..., Any]):
        self.methods = [m.upper() for m in methods]
        self.rule = rule or ""
        self.view_func = view_func


class Blueprint:
    def __init__(self, name: str, import_name: str, url_prefix: str = "") -> None:
        self.name = name
        self.import_name = import_name
        self.url_prefix = url_prefix or ""
        self._routes: List[Route] = []

    def route(self, rule: str, methods: Optional[List[str]] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        methods = methods or ["GET"]

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._routes.append(Route(methods, rule, func))
            return func

        return decorator

    def get(self, rule: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route(rule, methods=["GET"])

    def post(self, rule: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route(rule, methods=["POST"])

    def put(self, rule: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route(rule, methods=["PUT"])


class Flask:
    def __init__(self, import_name: str) -> None:
        self.import_name = import_name
        self._routes: List[Tuple[str, re.Pattern[str], Dict[str, Callable[[str], Any]], Callable[..., Any]]] = []
        self._teardown_funcs: List[Callable[[Optional[BaseException]], None]] = []
        self.config: Dict[str, Any] = {}

    def route(self, rule: str, methods: Optional[List[str]] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        bp = Blueprint(self.import_name, self.import_name)

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            bp.route(rule, methods)(func)
            self.register_blueprint(bp)
            return func

        return decorator

    def register_blueprint(self, bp: Blueprint) -> None:
        for route in bp._routes:
            full_rule = _normalize_path(_join_paths(bp.url_prefix, route.rule))
            pattern, converters = _compile_rule(full_rule)
            for method in route.methods:
                self._routes.append((method, pattern, converters, route.view_func))

    def add_url_rule(self, rule: str, view_func: Callable[..., Any], methods: Optional[List[str]] = None) -> None:
        methods = methods or ["GET"]
        pattern, converters = _compile_rule(_normalize_path(rule))
        for method in methods:
            self._routes.append((method.upper(), pattern, converters, view_func))

    def teardown_appcontext(self, func: Callable[[Optional[BaseException]], None]) -> Callable[[Optional[BaseException]], None]:
        self._teardown_funcs.append(func)
        return func

    def _execute_teardown(self, exc: Optional[BaseException]) -> None:
        for func in self._teardown_funcs:
            func(exc)

    def test_client(self) -> "TestClient":
        return TestClient(self)

    def _dispatch_request(self, req: Request) -> Response:
        path = _normalize_path(req.path)
        for method, pattern, converters, view_func in self._routes:
            if method != req.method:
                continue
            match = pattern.match(path)
            if not match:
                continue
            kwargs = {name: converter(match.group(name)) for name, converter in converters.items()}
            rv = view_func(**kwargs)
            return _ensure_response(rv)
        raise HTTPException(description="Not Found", code=404)


class TestClient:
    def __init__(self, app: Flask) -> None:
        self.app = app
        self._cookies: Dict[str, str] = {}

    def __enter__(self) -> "TestClient":  # pragma: no cover - simple context support
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # pragma: no cover - no suppression
        return False

    def get(self, path: str, **kwargs: Any) -> Response:
        return self.open(path, method="GET", **kwargs)

    def post(self, path: str, **kwargs: Any) -> Response:
        return self.open(path, method="POST", **kwargs)

    def put(self, path: str, **kwargs: Any) -> Response:
        return self.open(path, method="PUT", **kwargs)

    def open(self, path: str, method: str = "GET", json: Any = None, headers: Optional[Dict[str, str]] = None) -> Response:
        headers = headers or {}
        cookies = dict(self._cookies)
        request_obj = Request(method, path, json, headers, cookies)
        request_token = _request_var.set(request_obj)
        g_token = _g_var.set(SimpleNamespace())
        error: Optional[BaseException] = None
        try:
            response = self.app._dispatch_request(request_obj)
        except HTTPException as exc:
            response = Response(exc.description or "", status=exc.code)
        except BaseException as exc:  # pragma: no cover - defensive fallback
            error = exc
            if self.app.config.get("TESTING"):
                raise
            response = Response("Internal Server Error", status=500)
        else:
            error = None
        finally:
            self.app._execute_teardown(error)
            _request_var.reset(request_token)
            _g_var.reset(g_token)
        self._store_cookies(response)
        return response

    def _store_cookies(self, response: Response) -> None:
        header = response.headers.get("set-cookie")
        if not header:
            return
        cookie = SimpleCookie()
        cookie.load(header)
        for key, morsel in cookie.items():
            max_age = morsel["max-age"]
            if max_age == "0":
                self._cookies.pop(key, None)
            else:
                self._cookies[key] = morsel.value


def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def _join_paths(prefix: str, rule: str) -> str:
    prefix = prefix or ""
    rule = rule or ""
    segments = [seg for seg in (prefix.strip("/"), rule.strip("/")) if seg]
    if not segments:
        return "/"
    return "/" + "/".join(segments)


def _compile_rule(rule: str) -> Tuple[re.Pattern[str], Dict[str, Callable[[str], Any]]]:
    rule = _normalize_path(rule)
    if rule == "/":
        return re.compile(r"^/$"), {}
    parts = rule.strip("/").split("/")
    pattern = "^"
    converters: Dict[str, Callable[[str], Any]] = {}
    for part in parts:
        pattern += "/"
        if part.startswith("<") and part.endswith(">"):
            inner = part[1:-1]
            if ":" in inner:
                conv_type, name = inner.split(":", 1)
            else:
                conv_type, name = "string", inner
            if conv_type == "int":
                pattern += rf"(?P<{name}>\d+)"
                converters[name] = int
            else:
                pattern += rf"(?P<{name}>[^/]+)"
                converters[name] = str
        else:
            pattern += re.escape(part)
    pattern += "$"
    return re.compile(pattern), converters


def _ensure_response(rv: Any) -> Response:
    if isinstance(rv, Response):
        return rv
    status = None
    headers = None
    data = rv
    if isinstance(rv, tuple):
        if len(rv) == 3:
            data, status, headers = rv
        elif len(rv) == 2:
            data, status = rv
        elif len(rv) == 1:
            data = rv[0]
    if isinstance(data, (dict, list)):
        response = jsonify(data)
    else:
        response = Response(data if data is not None else "")
    if status is not None:
        response.status_code = status
    if headers:
        response.headers.update(headers)
    return response
