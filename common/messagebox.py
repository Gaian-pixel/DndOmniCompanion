from ttkbootstrap.dialogs import Messagebox
import tkinter.messagebox as tk_mb

class _MessageBoxWrapper:
    @staticmethod
    def showinfo(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        parent = kwargs.pop('parent', None)
        try:
            return Messagebox.show_info(message=str(message), title=str(title), parent=parent)
        except Exception:
            try:
                return tk_mb.showinfo(title=str(title), message=str(message), parent=parent)
            except Exception:
                return None
        
    @staticmethod
    def showerror(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        parent = kwargs.pop('parent', None)
        try:
            return Messagebox.show_error(message=str(message), title=str(title), parent=parent)
        except Exception:
            try:
                return tk_mb.showerror(title=str(title), message=str(message), parent=parent)
            except Exception:
                return None
        
    @staticmethod
    def showwarning(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        parent = kwargs.pop('parent', None)
        try:
            return Messagebox.show_warning(message=str(message), title=str(title), parent=parent)
        except Exception:
            try:
                return tk_mb.showwarning(title=str(title), message=str(message), parent=parent)
            except Exception:
                return None
        
    @staticmethod
    def askyesno(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        parent = kwargs.pop('parent', None)
        try:
            result = Messagebox.yesno(message=str(message), title=str(title), parent=parent)
            if isinstance(result, str):
                return result.lower() == "yes"
            return bool(result)
        except Exception:
            try:
                return tk_mb.askyesno(title=str(title), message=str(message), parent=parent)
            except Exception:
                return False

    @staticmethod
    def askokcancel(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        parent = kwargs.pop('parent', None)
        try:
            result = Messagebox.okcancel(message=str(message), title=str(title), parent=parent)
            if isinstance(result, str):
                return result.lower() == "ok"
            return bool(result)
        except Exception:
            try:
                return tk_mb.askokcancel(title=str(title), message=str(message), parent=parent)
            except Exception:
                return False

    @staticmethod
    def askyesnocancel(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        parent = kwargs.pop('parent', None)
        try:
            result = Messagebox.yesnocancel(message=str(message), title=str(title), parent=parent)
            if isinstance(result, str):
                low = result.strip().lower()
                if low in ("yes", "sì", "si"):
                    return True
                if low == "no":
                    return False
                return None
            return result
        except Exception:
            try:
                return tk_mb.askyesnocancel(title=str(title), message=str(message), parent=parent)
            except Exception:
                return None

messagebox = _MessageBoxWrapper()

showinfo = messagebox.showinfo
showerror = messagebox.showerror
showwarning = messagebox.showwarning
askyesno = messagebox.askyesno
askokcancel = messagebox.askokcancel
askyesnocancel = messagebox.askyesnocancel
