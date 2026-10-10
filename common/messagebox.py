from ttkbootstrap.dialogs import Messagebox

class _MessageBoxWrapper:
    @staticmethod
    def showinfo(title=None, message=None, **kwargs):
        # Ignore unsupported kwargs
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        return Messagebox.show_info(message=str(message), title=str(title))
        
    @staticmethod
    def showerror(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        return Messagebox.show_error(message=str(message), title=str(title))
        
    @staticmethod
    def showwarning(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        return Messagebox.show_warning(message=str(message), title=str(title))
        
    @staticmethod
    def askyesno(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        result = Messagebox.yesno(message=str(message), title=str(title))
        if isinstance(result, str):
            return result.lower() == "yes"
        return False

    @staticmethod
    def askokcancel(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        result = Messagebox.okcancel(message=str(message), title=str(title))
        if isinstance(result, str):
            return result.lower() == "ok"
        return False

messagebox = _MessageBoxWrapper()

showinfo = messagebox.showinfo
showerror = messagebox.showerror
showwarning = messagebox.showwarning
askyesno = messagebox.askyesno
askokcancel = messagebox.askokcancel
