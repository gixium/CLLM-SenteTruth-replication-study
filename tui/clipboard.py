"""
tui/clipboard.py
Zero-dependency cross-platform system clipboard access for Textual TUI.
Supports Windows (ctypes Win32 API), macOS (pbpaste/pbcopy), and Linux (xclip/xsel/wl-paste).
"""
from __future__ import annotations

import sys
import shutil
import subprocess


def get_system_clipboard() -> str:
    """Retrieve text from the OS system clipboard."""
    if sys.platform == "win32":
        return _get_windows_clipboard()
    elif sys.platform == "darwin":
        return _get_macos_clipboard()
    else:
        return _get_linux_clipboard()


def set_system_clipboard(text: str) -> bool:
    """Copy text to the OS system clipboard."""
    if sys.platform == "win32":
        return _set_windows_clipboard(text)
    elif sys.platform == "darwin":
        return _set_macos_clipboard(text)
    else:
        return _set_linux_clipboard(text)


# ── Windows implementation (ctypes Win32 user32 / kernel32) ───────────────────

def _get_windows_clipboard() -> str:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.OpenClipboard.restype = wintypes.BOOL
        user32.CloseClipboard.argtypes = []
        user32.CloseClipboard.restype = wintypes.BOOL
        user32.GetClipboardData.argtypes = [wintypes.UINT]
        user32.GetClipboardData.restype = wintypes.HANDLE
        kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalLock.restype = wintypes.LPVOID
        kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalUnlock.restype = wintypes.BOOL

        if not user32.OpenClipboard(None):
            return ""
        try:
            # CF_UNICODETEXT = 13
            h_mem = user32.GetClipboardData(13)
            if not h_mem:
                return ""
            p_data = kernel32.GlobalLock(h_mem)
            if not p_data:
                return ""
            try:
                return ctypes.wstring_at(p_data)
            finally:
                kernel32.GlobalUnlock(h_mem)
        finally:
            user32.CloseClipboard()
    except Exception:
        return ""


def _set_windows_clipboard(text: str) -> bool:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.OpenClipboard.restype = wintypes.BOOL
        user32.CloseClipboard.argtypes = []
        user32.CloseClipboard.restype = wintypes.BOOL
        user32.EmptyClipboard.argtypes = []
        user32.EmptyClipboard.restype = wintypes.BOOL
        user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        user32.SetClipboardData.restype = wintypes.HANDLE
        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalLock.restype = wintypes.LPVOID
        kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalUnlock.restype = wintypes.BOOL

        if not user32.OpenClipboard(None):
            return False
        try:
            user32.EmptyClipboard()
            encoded = (text + "\0").encode("utf-16le")
            # GMEM_MOVEABLE = 0x0002
            h_mem = kernel32.GlobalAlloc(0x0002, len(encoded))
            if not h_mem:
                return False
            p_data = kernel32.GlobalLock(h_mem)
            if not p_data:
                return False
            try:
                ctypes.memmove(p_data, encoded, len(encoded))
            finally:
                kernel32.GlobalUnlock(h_mem)
            # CF_UNICODETEXT = 13
            user32.SetClipboardData(13, h_mem)
            return True
        finally:
            user32.CloseClipboard()
    except Exception:
        return False


# ── macOS implementation (pbpaste / pbcopy) ───────────────────────────────────

def _get_macos_clipboard() -> str:
    try:
        return subprocess.check_output(["pbpaste"], text=True, timeout=1)
    except Exception:
        return ""


def _set_macos_clipboard(text: str) -> bool:
    try:
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(input=text.encode("utf-8"), timeout=1)
        return proc.returncode == 0
    except Exception:
        return False


# ── Linux implementation (wl-paste / xclip / xsel) ────────────────────────────

def _get_linux_clipboard() -> str:
    candidates = [
        ["wl-paste"],
        ["xclip", "-selection", "clipboard", "-o"],
        ["xsel", "-b", "-o"],
    ]
    for cmd in candidates:
        if shutil.which(cmd[0]):
            try:
                return subprocess.check_output(cmd, text=True, timeout=1)
            except Exception:
                pass
    return ""


def _set_linux_clipboard(text: str) -> bool:
    candidates = [
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "-b", "-i"],
    ]
    for cmd in candidates:
        if shutil.which(cmd[0]):
            try:
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                proc.communicate(input=text.encode("utf-8"), timeout=1)
                return proc.returncode == 0
            except Exception:
                pass
    return False
