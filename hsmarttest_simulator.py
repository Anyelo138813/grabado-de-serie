import ctypes
from ctypes import wintypes
from datetime import datetime


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
HICON = ctypes.c_void_p
HCURSOR = ctypes.c_void_p
HBRUSH = ctypes.c_void_p
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_KEYDOWN = 0x0100
WM_SETFONT = 0x0030
VK_RETURN = 0x0D

WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_BORDER = 0x00800000
WS_VSCROLL = 0x00200000
ES_AUTOHSCROLL = 0x0080
LBS_NOTIFY = 0x0001

CW_USEDEFAULT = -2147483648
GWLP_WNDPROC = -4

LB_ADDSTRING = 0x0180
LB_SETCURSEL = 0x0186
LB_RESETCONTENT = 0x0184

BUTTON_CLEAR_ID = 1001


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
user32.RegisterClassW.restype = wintypes.ATOM

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT

user32.CallWindowProcW.argtypes = [WNDPROC, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.CallWindowProcW.restype = LRESULT

user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
user32.SetWindowLongPtrW.restype = ctypes.c_void_p

user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = LRESULT

user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
user32.SetWindowTextW.restype = wintypes.BOOL

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UpdateWindow.argtypes = [wintypes.HWND]
user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.PostQuitMessage.argtypes = [ctypes.c_int]

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE


class HSmartTestSimulator:
    def __init__(self):
        self.hinstance = kernel32.GetModuleHandleW(None)
        self.window_proc = WNDPROC(self._window_proc)
        self.edit_proc = WNDPROC(self._edit_proc)
        self.old_edit_proc = None
        self.hwnd = None
        self.edit_hwnd = None
        self.list_hwnd = None

    def run(self):
        self._register_window_class()
        self._create_window()
        user32.ShowWindow(self.hwnd, 1)
        user32.UpdateWindow(self.hwnd)

        msg = MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _register_window_class(self):
        wc = WNDCLASS()
        wc.lpfnWndProc = self.window_proc
        wc.hInstance = self.hinstance
        wc.lpszClassName = "HSmartTestSimulatorWindow"
        wc.hbrBackground = ctypes.c_void_p(5)
        atom = user32.RegisterClassW(ctypes.byref(wc))
        if not atom and ctypes.get_last_error() != 1410:
            raise ctypes.WinError(ctypes.get_last_error())

    def _create_window(self):
        self.hwnd = user32.CreateWindowExW(
            0,
            "HSmartTestSimulatorWindow",
            "HSmartTest Simulator",
            WS_OVERLAPPEDWINDOW,
            CW_USEDEFAULT,
            CW_USEDEFAULT,
            560,
            420,
            None,
            None,
            self.hinstance,
            None,
        )
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

        self.edit_hwnd = user32.CreateWindowExW(
            0,
            "Edit",
            "",
            WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL,
            24,
            24,
            500,
            28,
            self.hwnd,
            None,
            self.hinstance,
            None,
        )
        if not self.edit_hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

        self.list_hwnd = user32.CreateWindowExW(
            0,
            "ListBox",
            "",
            WS_CHILD | WS_VISIBLE | WS_BORDER | WS_VSCROLL | LBS_NOTIFY,
            24,
            70,
            500,
            260,
            self.hwnd,
            None,
            self.hinstance,
            None,
        )
        if not self.list_hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

        user32.CreateWindowExW(
            0,
            "Button",
            "Limpiar",
            WS_CHILD | WS_VISIBLE,
            24,
            342,
            100,
            30,
            self.hwnd,
            ctypes.c_void_p(BUTTON_CLEAR_ID),
            self.hinstance,
            None,
        )

        old_proc = user32.SetWindowLongPtrW(self.edit_hwnd, GWLP_WNDPROC, ctypes.cast(self.edit_proc, ctypes.c_void_p))
        self.old_edit_proc = WNDPROC(old_proc)
        self._append_log("Simulador listo. Esperando codigos enviados por TCP Client.")

    def _window_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_COMMAND and int(wparam) & 0xFFFF == BUTTON_CLEAR_ID:
            user32.SendMessageW(self.list_hwnd, LB_RESETCONTENT, 0, 0)
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _edit_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_KEYDOWN and int(wparam) == VK_RETURN:
            text = self._get_edit_text()
            if text:
                self._append_log(f"Grabado: {text}")
                user32.SetWindowTextW(self.edit_hwnd, "")
            return 0
        return user32.CallWindowProcW(self.old_edit_proc, hwnd, msg, wparam, lparam)

    def _get_edit_text(self):
        length = user32.GetWindowTextLengthW(self.edit_hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(self.edit_hwnd, buffer, len(buffer))
        return buffer.value

    def _append_log(self, text):
        line = f"{datetime.now():%H:%M:%S.%f}"[:-3] + f" | {text}"
        line_buffer = ctypes.create_unicode_buffer(line)
        line_ptr = ctypes.cast(line_buffer, ctypes.c_void_p).value
        user32.SendMessageW(self.list_hwnd, LB_ADDSTRING, 0, line_ptr)
        user32.SendMessageW(self.list_hwnd, LB_SETCURSEL, 0xFFFFFFFF, 0)


if __name__ == "__main__":
    HSmartTestSimulator().run()
