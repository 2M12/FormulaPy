import sys
import os
import io
import json
import time
import ctypes
import hashlib
import shutil
import socket
import threading
import subprocess
import marshal
import ast
from pathlib import Path
from typing import Dict, Any, List

import requests

class FunctionInfo(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char * 256),
        ("has_loop", ctypes.c_int),
        ("has_io", ctypes.c_int),
        ("has_string", ctypes.c_int),
        ("is_jittable", ctypes.c_int),
    ]

class AnalysisResult(ctypes.Structure):
    _fields_ = [
        ("total_functions", ctypes.c_int),
        ("total_loops", ctypes.c_int),
        ("jittable_functions", ctypes.c_int),
        ("functions", FunctionInfo * 512),
    ]

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        RED = GREEN = YELLOW = BLUE = CYAN = WHITE = RESET = ""
    class Style:
        RESET_ALL = ""

APP_NAME = "FormulaPy"
APP_VERSION = "1.0.0"
GITHUB_API = "https://api.github.com/repos/2M12/FormulaPy/releases/latest"

BASE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
ENGINE_DIR = BASE_DIR / "Engine"
CACHE_DIR = BASE_DIR / "cache"
ENV_DIR = BASE_DIR / "env"
DAEMON_DIR = BASE_DIR / "daemon"

DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = 8765
DAEMON_TIMEOUT = 1
DAEMON_LOG_FILE = DAEMON_DIR / "daemon.log"

LOG_COLORS = {
    "INFO": Fore.CYAN,
    "OK": Fore.GREEN,
    "WARN": Fore.YELLOW,
    "ERROR": Fore.RED,
    "DEBUG": Fore.BLUE,
}

BANNER = f"""
{Fore.RED}   ____                    __   ___     
  / __/__  ______ _  __ __/ /__ _/ _ \\__ __
 / _// _ \\/ __/  ' \\/ // / / _ `/ ___/ // /
/_/  \\___/_/ /_/_/_/\\_,_/_/\\_,_/_/   \\_, / 
                                    /___/  
{Style.RESET_ALL}
FormulaPy by 2M12 version {APP_VERSION}
Created by Mikhail Chernov (aka 2M12)
"We transplant the snake onto the speed wheel."
"""


def log(msg: str, level: str = "INFO") -> None:
    color = LOG_COLORS.get(level, Fore.WHITE)
    print(f"{color}[{level}]{Style.RESET_ALL} {msg}")


def ensure_dirs() -> None:
    for d in (BASE_DIR, ENGINE_DIR, CACHE_DIR, ENV_DIR, DAEMON_DIR):
        d.mkdir(parents=True, exist_ok=True)


def check_version() -> None:
    try:
        r = requests.get(GITHUB_API, timeout=3)
        if r.status_code == 200:
            latest = r.json().get("tag_name", "").replace("v", "")
            if latest and latest != APP_VERSION:
                log(f"New version available: {latest}. Please update!", "WARN")
            else:
                log("You are using the latest version.", "OK")
        else:
            log("Could not check for updates.", "WARN")
    except Exception:
        log("Could not check for updates.", "WARN")


def has_gui_or_com(code: str) -> bool:
    keywords = ["PySide6", "PyQt", "tkinter", "QApplication", "wmi", "win32com", "pythoncom"]
    return any(k in code for k in keywords)


class FormulaCore:
    def __init__(self):
        self._load_core()

    def _load_core(self):
        try:
            dll_path = Path(__file__).parent / "formulacore.dll"

            if not dll_path.exists():
                dll_path = Path(sys.executable).parent / "formulacore.dll"

            if not dll_path.exists():
                raise FileNotFoundError(f"formulacore.dll not found")

            self.core = ctypes.CDLL(str(dll_path))

            self.core.core_get_version.restype = ctypes.c_int
            self.core.core_hash_code.argtypes = [ctypes.c_char_p]
            self.core.core_hash_code.restype = ctypes.c_uint64

            self.core.core_optimize_code.argtypes = [ctypes.c_char_p, ctypes.c_int]
            self.core.core_optimize_code.restype = ctypes.c_void_p

            self.core.core_free_string.argtypes = [ctypes.c_void_p]

            self.core_loaded = True
        except Exception as e:
            self.core = None
            self.core_loaded = False
            log(f"Failed to load core: {e}", "DEBUG")

    def get_version(self) -> int:
        return self.core.core_get_version() if self.core_loaded else 0

    def hash_code(self, code: str) -> str:
        if self.core_loaded:
            val = self.core.core_hash_code(code.encode('utf-8'))
            return hex(val)[2:]
        return hashlib.md5(code.encode()).hexdigest()

    def optimize_code(self, code: str, inject_jit: bool) -> str:
        if not self.core_loaded:
            return code

        ptr = self.core.core_optimize_code(code.encode("utf-8"), 1 if inject_jit else 0)
        if ptr:
            result = ctypes.cast(ptr, ctypes.c_char_p).value.decode("utf-8")
            self.core.core_free_string(ptr)
            return result
        return code


class JIT:
    @staticmethod
    def get_headers(mode: str) -> str:
        if mode == "numba":
            return """
try:
    from numba import jit as _numba_jit
    def _formulapy_jit(func):
        _jitted = _numba_jit(nopython=True)(func)
        def _wrapper(*args, **kwargs):
            try: return _jitted(*args, **kwargs)
            except Exception: return func(*args, **kwargs)
        return _wrapper
except Exception:
    def _formulapy_jit(func): return func
"""
        elif mode == "nvcuda":
            return """
try:
    from numba import cuda, jit as _numba_jit
    if cuda.is_available(): _formulapy_jit = cuda.jit
    else:
        def _formulapy_jit(func): return _numba_jit(nopython=True)(func)
except Exception:
    def _formulapy_jit(func): return func
"""
        elif mode == "jax":
            return """
try:
    import jax
    def _formulapy_jit(func): return jax.jit(func)
except Exception:
    def _formulapy_jit(func): return func
"""
        return "\ndef _formulapy_jit(func):\n    return func\n"


class DaemonServer:
    def __init__(self, host="127.0.0.1", port=8765):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.running = True

        while self.running:
            try:
                client, _ = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()
            except:
                break

        self.server_socket.close()

    def _handle_client(self, client):
        try:
            data = b""
            while True:
                chunk = client.recv(65536)
                if not chunk:
                    break
                data += chunk
                if len(chunk) < 65536:
                    break

            payload = json.loads(data.decode("utf-8"))
            cmd = payload.get("command")

            if cmd == "shutdown":
                client.sendall(b'{"status":"ok","result":"shutdown"}')
                self.running = False
                self.server_socket.close()
                os._exit(0)

            elif cmd == "ping":
                client.sendall(b'{"status":"ok","result":"pong"}')

            elif cmd == "run_script":
                code = payload.get("code", "")
                args = payload.get("args", [])

                old_argv = sys.argv[:]
                old_stdout = sys.stdout
                old_stderr = sys.stderr

                sys.argv = ["script.py"] + args
                captured_stdout = io.StringIO()
                captured_stderr = io.StringIO()
                sys.stdout = captured_stdout
                sys.stderr = captured_stderr

                start = time.perf_counter()
                try:
                    exec(compile(code, "script.py", "exec"), {"__name__": "__main__"})
                    exec_time = round((time.perf_counter() - start) * 1000, 2)
                    status = "ok"
                    error = ""
                except SystemExit:
                    exec_time = round((time.perf_counter() - start) * 1000, 2)
                    status = "ok"
                    error = ""
                except Exception as e:
                    exec_time = round((time.perf_counter() - start) * 1000, 2)
                    status = "error"
                    error = str(e)
                finally:
                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr

                result = {
                    "status": status,
                    "execution_time_ms": exec_time,
                    "stdout": captured_stdout.getvalue(),
                    "stderr": captured_stderr.getvalue(),
                }
                if error:
                    result["error"] = error

                client.sendall(json.dumps(result).encode("utf-8"))

        except Exception as e:
            try:
                client.sendall(json.dumps({"status": "error", "error": str(e)}).encode("utf-8"))
            except:
                pass
        finally:
            client.close()


class Daemon:
    @staticmethod
    def is_running() -> bool:
        try:
            with socket.create_connection((DAEMON_HOST, DAEMON_PORT), timeout=DAEMON_TIMEOUT):
                return True
        except Exception:
            return False

    @staticmethod
    def start():
        if Daemon.is_running():
            log("Daemon is already running.", "OK")
            return

        ensure_dirs()
        log("Starting daemon...", "INFO")
        log(f"Daemon endpoint: {DAEMON_HOST}:{DAEMON_PORT}", "DEBUG")

        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--daemon"]
        else:
            cmd = [sys.executable, str(Path(__file__).resolve()), "--daemon"]

        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0

        with open(DAEMON_LOG_FILE, "w") as logf:
            subprocess.Popen(
                cmd,
                stdout=logf,
                stderr=logf,
                stdin=subprocess.DEVNULL,
                close_fds=True,
                creationflags=creationflags,
            )

        for _ in range(20):
            if Daemon.is_running():
                log("Daemon started successfully.", "OK")
                return
            time.sleep(0.2)

        log("Failed to start daemon.", "ERROR")

    @staticmethod
    def stop():
        if not Daemon.is_running():
            log("Daemon is not running.", "WARN")
            return

        Daemon._send({"command": "shutdown"})
        time.sleep(0.5)

        if Daemon.is_running():
            log("Daemon did not stop gracefully.", "WARN")
            answer = input("Force stop daemon? (y/n): ").strip().lower()
            if answer == "y":
                subprocess.run(["taskkill", "/F", "/IM", "python.exe"],
                               capture_output=True, check=False)
                log("Daemon force stopped.", "OK")
            else:
                log("Daemon still running.", "WARN")
        else:
            log("Daemon stopped.", "OK")

    @staticmethod
    def _send(payload: Dict[str, Any], timeout: int = 600) -> Dict[str, Any]:
        try:
            with socket.create_connection((DAEMON_HOST, DAEMON_PORT), timeout=timeout) as s:
                s.sendall(json.dumps(payload).encode("utf-8"))
                data = b""
                while True:
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                return json.loads(data.decode("utf-8"))
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def run_script(code: str, args: List[str]) -> Dict[str, Any]:
        payload = {
            "command": "run_script",
            "code": code,
            "args": args,
        }
        return Daemon._send(payload, timeout=600)


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            try:
                s.write(data)
                s.flush()
            except Exception:
                pass

    def flush(self):
        for s in self.streams:
            try:
                s.flush()
            except Exception:
                pass


def execute_script(code: str, script_path: str, args: List[str]) -> Dict[str, Any]:
    old_argv = sys.argv[:]
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    sys.argv = [script_path] + args

    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()

    daemon_log = open(DAEMON_LOG_FILE, "a", encoding="utf-8")

    sys.stdout = Tee(captured_stdout, daemon_log)
    sys.stderr = Tee(captured_stderr, daemon_log)

    ns = {"__name__": "__main__", "__file__": script_path}

    com_initialized = False
    try:
        import pythoncom
        pythoncom.CoInitialize()
        com_initialized = True
    except Exception:
        pass

    start = time.perf_counter()
    try:
        exec(compile(code, script_path, "exec"), ns)
        exec_time = round((time.perf_counter() - start) * 1000, 2)
        status = "ok"
        error = ""
    except SystemExit:
        exec_time = round((time.perf_counter() - start) * 1000, 2)
        status = "ok"
        error = ""
    except Exception as e:
        exec_time = round((time.perf_counter() - start) * 1000, 2)
        status = "error"
        error = str(e)
    finally:
        if com_initialized:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass

        sys.argv = old_argv
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        daemon_log.close()

    stdout_text = captured_stdout.getvalue()
    stderr_text = captured_stderr.getvalue()

    result = {
        "status": status,
        "execution_time_ms": exec_time,
        "stdout": stdout_text,
        "stderr": stderr_text,
    }

    if status == "error":
        result["error"] = error

    return result


def run_diagnostics(core: FormulaCore) -> None:
    log("Running FormulaPy diagnostics...", "INFO")
    log(f"Python: {sys.version}", "INFO")

    if core.core_loaded:
        log(f"Core DLL: loaded (v{core.get_version()})", "OK")
    else:
        log("Core DLL: not found", "ERROR")

    if Daemon.is_running():
        log("Daemon: already running", "OK")
    else:
        Daemon.start()
        if Daemon.is_running():
            log("Daemon: started successfully", "OK")
            Daemon.stop()
        else:
            log("Daemon: failed to start", "ERROR")

    log("Diagnostics finished.", "OK")


def clear_cache() -> None:
    ensure_dirs()
    count = 0
    for f in CACHE_DIR.iterdir():
        if f.is_file():
            f.unlink()
            count += 1
        elif f.is_dir():
            shutil.rmtree(f)
            count += 1
    log(f"Cache cleared. Removed {count} items.", "OK")


def print_banner() -> None:
    print(BANNER)


def main() -> None:
    ensure_dirs()
    args = sys.argv[1:]

    core = FormulaCore()

    if "--daemon" in args:
        DaemonServer().start()
        return

    if "--stop" in args:
        Daemon.stop()
        return

    if "--diagnostics" in args:
        run_diagnostics(core)
        return

    if "--version" in args or "-v" in args:
        print_banner()
        check_version()
        if core.core_loaded:
            log(f"Core version: {core.get_version()}", "DEBUG")
        return

    if "--clearcache" in args:
        clear_cache()
        return

    if "--help" in args or "-h" in args or not args:
        print_banner()
        print("Usage:")
        print("  formulapy main.py              Run script with daemon and JIT")
        print("  formulapy main.py --nodaemon   Run without daemon")
        print("  formulapy main.py --nojit      Run without JIT")
        print("  formulapy main.py --debug      Show debug logs")
        print("  formulapy main.py --bco        Boot Code Optimization")
        print("  formulapy main.py --nvcuda     Use Numba CUDA JIT")
        print("  formulapy main.py --jax        Use JAX JIT")
        print("  formulapy --diagnostics        Run diagnostics")
        print("  formulapy --stop               Stop daemon")
        print("  formulapy --clearcache         Clear all cache")
        print("  formulapy --version            Show version")
        return

    script_name = args[0]
    script_path = Path(script_name)

    if not script_path.exists():
        log(f"Script not found: {script_name}", "ERROR")
        return

    script_args = args[1:]
    use_daemon = "--nodaemon" not in script_args
    use_debug = "--debug" in script_args
    use_bco = "--bco" in script_args
    use_nvcuda = "--nvcuda" in script_args
    use_jax = "--jax" in script_args
    use_nojit = "--nojit" in script_args

    jit_mode = "numba"
    if use_nvcuda:
        jit_mode = "nvcuda"
    elif use_jax:
        jit_mode = "jax"

    script_args = [a for a in script_args if a not in (
        "--nodaemon", "--debug", "--bco", "--nvcuda", "--jax", "--nojit"
    )]

    code = script_path.read_text(encoding="utf-8")

    if has_gui_or_com(code):
        use_daemon = False
        if use_debug:
            log("GUI/COM detected. Running without daemon.", "DEBUG")

    log(f"FormulaPy by 2M12 version {APP_VERSION}", "INFO")

    if use_debug:
        log(f"Base directory: {BASE_DIR}", "DEBUG")
        log(f"Script: {script_path}", "DEBUG")
        log(f"Daemon: {'enabled' if use_daemon else 'disabled'}", "DEBUG")
        log(f"JIT mode: {'disabled' if use_nojit else jit_mode}", "DEBUG")
        log(f"BCO: {'enabled' if use_bco else 'disabled'}", "DEBUG")
        if core.core_loaded:
            log(f"Core DLL: loaded (v{core.get_version()})", "DEBUG")
        else:
            log("Core DLL: not found", "WARN")

    check_version()

    if core.core_loaded and not use_nojit:
        code = core.optimize_code(code, inject_jit=True)
        code = JIT.get_headers(jit_mode) + code
        if use_debug:
            log("JIT injected via C++ core.", "DEBUG")
    elif core.core_loaded and use_bco:
        code = core.optimize_code(code, inject_jit=False)
        if use_debug:
            log("BCO applied via C++ core.", "DEBUG")

    if use_daemon:
        if not Daemon.is_running():
            Daemon.start()
        else:
            log("Daemon already running.", "DEBUG")
        result = Daemon.run_script(code, script_args)
    else:
        result = execute_script(code, str(script_path), script_args)

    if result.get("status") == "ok":
        stdout_text = result.get("stdout", "")
        if stdout_text:
            sys.stdout.write(stdout_text)
        log(f"Script finished in {result.get('execution_time_ms', 0)} ms", "OK")
    else:
        stderr_text = result.get("stderr", "")
        if stderr_text:
            sys.stderr.write(stderr_text)
        log(f"Error: {result.get('error', 'Unknown error')}", "ERROR")


if __name__ == "__main__":
    main()