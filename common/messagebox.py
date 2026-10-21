from ttkbootstrap.dialogs import Messagebox

class _MessageBoxWrapper:
    @staticmethod
    def showinfo(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        parent = kwargs.pop('parent', None)
        return Messagebox.show_info(message=str(message), title=str(title), parent=parent)
        
    @staticmethod
    def showerror(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        parent = kwargs.pop('parent', None)
        return Messagebox.show_error(message=str(message), title=str(title), parent=parent)
        
    @staticmethod
    def showwarning(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        parent = kwargs.pop('parent', None)
        return Messagebox.show_warning(message=str(message), title=str(title), parent=parent)
        
    @staticmethod
    def askyesno(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        parent = kwargs.pop('parent', None)
        result = Messagebox.yesno(message=str(message), title=str(title), parent=parent)
        if isinstance(result, str):
            return result.lower() == "yes"
        return False

    @staticmethod
    def askokcancel(title=None, message=None, **kwargs):
        kwargs.pop('icon', None)
        kwargs.pop('type', None)
        parent = kwargs.pop('parent', None)
        result = Messagebox.okcancel(message=str(message), title=str(title), parent=parent)
        if isinstance(result, str):
            return result.lower() == "ok"
        return False

messagebox = _MessageBoxWrapper()

showinfo = messagebox.showinfo
showerror = messagebox.showerror
showwarning = messagebox.showwarning
askyesno = messagebox.askyesno
askokcancel = messagebox.askokcancel
