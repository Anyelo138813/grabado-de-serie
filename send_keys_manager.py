import ctypes
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

user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

WM_SETTEXT = 0x000C
WM_KEYDOWN = 0x0100
VK_RETURN = 0x0D


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
        return False

    hwnd_edit = user32.FindWindowExW(hwnd, 0, "Edit", None)
    target = hwnd_edit or hwnd

    text_buffer = ctypes.create_unicode_buffer(text)
    text_ptr = ctypes.cast(text_buffer, ctypes.c_void_p).value
    user32.SendMessageW(target, WM_SETTEXT, 0, text_ptr)
    user32.PostMessageW(target, WM_KEYDOWN, VK_RETURN, 0)
    return True
