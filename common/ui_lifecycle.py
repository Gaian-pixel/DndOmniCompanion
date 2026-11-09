"""
ui_lifecycle.py - Gestione sicura del ciclo di vita dei widget Tkinter e dei timer after().
Previene memory leak, callback orfane e i tipici errori Tcl/Tk:
- "invalid command name ... while executing (after script)"
- "cannot invoke 'event' command: application has been destroyed"
- "bgerror failed to handle background error"
"""

import sys
import weakref

def safe_after(widget, delay_ms, func, *args, **kwargs):
    """
    Pianifica l'esecuzione di func su widget in modo sicuro:
    1. Verifica che il widget esista prima di pianificare.
    2. Registra l'ID del timer per poterlo cancellare alla chiusura.
    3. All'attivazione del timer, riverifica che il widget sia ancora vivo.
    4. Cattura silenziosamente gli errori di interprete Tcl distrutto.
    """
    if widget is None:
        return None
    try:
        if hasattr(widget, "winfo_exists") and not widget.winfo_exists():
            return None
    except Exception:
        return None

    if getattr(widget, "_is_closing", False) or getattr(widget, "_destroyed", False):
        return None

    timer_box = [None]

    def _safe_wrapper():
        # Rimuovi timer dai tracciati
        if hasattr(widget, "_safe_timers") and timer_box[0] in widget._safe_timers:
            widget._safe_timers.discard(timer_box[0])
        try:
            if hasattr(widget, "winfo_exists") and widget.winfo_exists():
                if not getattr(widget, "_is_closing", False) and not getattr(widget, "_destroyed", False):
                    func(*args, **kwargs)
        except Exception as e:
            err = str(e)
            if not any(t in err for t in ("destroyed", "application has been destroyed", "invalid command name")):
                print(f"[safe_after] Eccezione in callback: {e}")

    try:
        tid = widget.after(delay_ms, _safe_wrapper)
        timer_box[0] = tid

        if not hasattr(widget, "_safe_timers"):
            widget._safe_timers = set()
            try:
                widget.bind("<Destroy>", lambda e: _on_widget_destroy(e, widget), add="+")
            except Exception:
                pass
        widget._safe_timers.add(tid)
        return tid
    except Exception:
        return None

def cancel_safe_timer(widget, timer_id):
    """Cancella un timer pianificato tramite safe_after."""
    if not widget or not timer_id:
        return
    try:
        if hasattr(widget, "after_cancel"):
            widget.after_cancel(timer_id)
    except Exception:
        pass
    if hasattr(widget, "_safe_timers"):
        widget._safe_timers.discard(timer_id)

def cancel_all_after_timers(widget):
    """Cancella tutti i timer pianificati su un widget e ricorsivamente sui suoi figli."""
    if not widget:
        return
    timers = list(getattr(widget, "_safe_timers", []))
    for tid in timers:
        try:
            widget.after_cancel(tid)
        except Exception:
            pass
    if hasattr(widget, "_safe_timers"):
        widget._safe_timers.clear()
    try:
        children = list(getattr(widget, "children", {}).values())
        for child in children:
            cancel_all_after_timers(child)
    except Exception:
        pass

def _on_widget_destroy(event, widget):
    """Callback automatica scatenata su evento <Destroy> per pulire timer pendenti."""
    if event and getattr(event, "widget", None) == widget:
        cancel_all_after_timers(widget)

def safe_destroy_window(window):
    """
    Distrugge una finestra Toplevel o Tk principale svuotando prima
    la coda degli eventi Tcl e cancellando tutti i timer pendenti.
    """
    if not window:
        return
    try:
        window._is_closing = True
        window._destroyed = True
    except Exception:
        pass

    cancel_all_after_timers(window)

    try:
        if hasattr(window, "update_idletasks") and window.winfo_exists():
            window.update_idletasks()
    except Exception:
        pass

    try:
        if hasattr(window, "destroy"):
            window.destroy()
    except Exception:
        pass

def suppress_tk_bgerror(root):
    """
    Registra una procedura bgerror sicura nell'interprete Tcl per sopprimere
    i warning asincroni generati da widget distrutti durante la chiusura delle finestre o nei test.
    """
    if not root:
        return
    try:
        if hasattr(root, "tk") and hasattr(root.tk, "eval"):
            root.tk.eval('''
proc bgerror {msg} {
    if {[string match "*application has been destroyed*" $msg] || [string match "*cannot invoke*" $msg] || [string match "*invalid command name*" $msg]} {
        return
    }
}
''')
    except Exception:
        pass
