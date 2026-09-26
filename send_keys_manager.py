import ctypes
from dataclasses import dataclass
from ctypes import wintypes


user32 = ctypes.WinDLL("user32", use_last_error=True)

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.FindWindowExW.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
]
user32.FindWindowExW.restype = wintypes.HWND

user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = wintypes.LPARAM

user32.SendMessageTimeoutW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_size_t),
]
user32.SendMessageTimeoutW.restype = wintypes.LPARAM

user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

WM_SETTEXT = 0x000C
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D
SMTO_ABORTIFHUNG = 0x0002
SETTEXT_TIMEOUT_MS = 1000


@dataclass
class SendResult:
    sent: bool
    window_found: bool
    edit_found: bool
    set_text_ok: bool
    enter_down_ok: bool
    enter_up_ok: bool
    detail: str

    def __bool__(self):
        return self.sent


def _find_hsmarttest_window():
    found = {"hwnd": 0}

    @EnumWindowsProc
    def enum_proc(hwnd, _lparam):
        buffer = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        title = buffer.value
        if title.lower().startswith("hsmarttest"):
            found["hwnd"] = hwnd
            return False
        return True

    user32.EnumWindows(enum_proc, 0)
    return found["hwnd"]


def send(text):
    hwnd = _find_hsmarttest_window()
    if not hwnd:
        return SendResult(False, False, False, False, False, False, "HSmartTest no encontrado")

    hwnd_edit = user32.FindWindowExW(hwnd, 0, "Edit", None)
    target = hwnd_edit or hwnd
    edit_found = bool(hwnd_edit)

    text_buffer = ctypes.create_unicode_buffer(text)
    text_ptr = ctypes.cast(text_buffer, ctypes.c_void_p).value
    result = ctypes.c_size_t(0)
    set_text_ok = bool(
        user32.SendMessageTimeoutW(
            target,
            WM_SETTEXT,
            0,
            text_ptr,
            SMTO_ABORTIFHUNG,
            SETTEXT_TIMEOUT_MS,
            ctypes.byref(result),
        )
    )
    if not set_text_ok:
        return SendResult(
            False,
            True,
            edit_found,
            False,
            False,
            False,
            "Timeout o fallo al escribir en HSmartTest",
        )

    enter_down_ok = bool(user32.PostMessageW(target, WM_KEYDOWN, VK_RETURN, 0))
    enter_up_ok = bool(user32.PostMessageW(target, WM_KEYUP, VK_RETURN, 0))
    sent = enter_down_ok and enter_up_ok
    detail = (
        f"window=ok edit={'ok' if edit_found else 'no'} set_text=ok "
        f"enter_down={'ok' if enter_down_ok else 'fail'} enter_up={'ok' if enter_up_ok else 'fail'}"
    )
    return SendResult(sent, True, edit_found, True, enter_down_ok, enter_up_ok, detail)
