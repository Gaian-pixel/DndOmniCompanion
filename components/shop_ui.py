import tkinter as tk
from tkinter import ttk, simpledialog
from common.messagebox import messagebox

class ShopDialog(tk.Toplevel):
    def __init__(self, parent, game_state, is_dm=False, network_or_server=None):
        super().__init__(parent)
        self.title("Negozi e Botteghe")
        self.minsize(500, 400)
        self.transient(parent)
        self.grab_set()

        from common.theme import apply_modern_window_style
        apply_modern_window_style(self)

        self.game_state = game_state
        self.is_dm = is_dm
        self.network = network_or_server
        
        self.create_widgets()
        self.refresh_shops()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top_frame, text="Seleziona Negozio:", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        self.shop_var = tk.StringVar()
        self.shop_combo = ttk.Combobox(top_frame, textvariable=self.shop_var, state="readonly")
        self.shop_combo.pack(side=tk.LEFT, padx=10)
        self.shop_combo.bind("<<ComboboxSelected>>", self.on_shop_selected)
        
        if self.is_dm:
            ttk.Button(top_frame, text="➕ Nuovo Negozio", command=self.add_shop).pack(side=tk.LEFT, padx=5)
            ttk.Button(top_frame, text="➕ Aggiungi Oggetto", command=self.add_item).pack(side=tk.LEFT, padx=5)
            
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("name", "price")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        self.tree.heading("name", text="Oggetto")
        self.tree.heading("price", text="Prezzo (mo)")
        self.tree.column("name", width=250)
        self.tree.column("price", width=100, anchor=tk.CENTER)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scrollbar.set)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        if not self.is_dm:
            ttk.Button(btn_frame, text="💰 Compra Selezionato", command=self.buy_item, style="Success.TButton").pack(side=tk.LEFT)
        else:
            ttk.Button(btn_frame, text="❌ Rimuovi Oggetto", command=self.remove_item, style="Danger.TButton").pack(side=tk.LEFT)

    def _get_shops(self):
        if isinstance(self.game_state, dict):
            return self.game_state.get("shops", {})
        return getattr(self.game_state, "shops", {})

    def refresh_shops(self):
        shops = self._get_shops()
        shop_names = list(shops.keys())
        self.shop_combo['values'] = shop_names
        if shop_names and not self.shop_var.get():
            self.shop_var.set(shop_names[0])
        self.on_shop_selected()
            
    def on_shop_selected(self, event=None):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        shop_name = self.shop_var.get()
        if not shop_name: return
        
        shops = self._get_shops()
        shop = shops.get(shop_name, {})
        for item in shop.get("items", []):
            self.tree.insert("", tk.END, values=(item.get("name"), item.get("price")))

    def add_shop(self):
        name = simpledialog.askstring("Nuovo Negozio", "Nome della bottega:", parent=self)
        if not name: return
        shops = self._get_shops()
        if name not in shops:
            shops[name] = {"items": []}
            self._sync()
            self.refresh_shops()
            self.shop_var.set(name)
            self.on_shop_selected()

    def add_item(self):
        shop_name = self.shop_var.get()
        if not shop_name: return
        name = simpledialog.askstring("Nuovo Oggetto", "Nome dell'oggetto:", parent=self)
        if not name: return
        price = simpledialog.askinteger("Prezzo", f"Prezzo di {name} (in monete d'oro):", parent=self, minvalue=0)
        if price is None: return
        
        shops = self._get_shops()
        shops[shop_name]["items"].append({"name": name, "price": price})
        self._sync()
        self.on_shop_selected()

    def remove_item(self):
        shop_name = self.shop_var.get()
        if not shop_name: return
        sel = self.tree.selection()
        if not sel: return
        item_name = self.tree.item(sel[0], "values")[0]
        
        shops = self._get_shops()
        items = shops[shop_name]["items"]
        shops[shop_name]["items"] = [i for i in items if i.get("name") != item_name]
        self._sync()
        self.on_shop_selected()

    def buy_item(self):
        shop_name = self.shop_var.get()
        if not shop_name: return
        sel = self.tree.selection()
        if not sel: return
        item_name = self.tree.item(sel[0], "values")[0]
        price = self.tree.item(sel[0], "values")[1]
        
        if messagebox.askyesno("Conferma Acquisto", f"Vuoi comprare '{item_name}' per {price} mo?"):
            if self.network:
                from common.network_utils import send_message
                send_message(self.network.conn, {"type": "BUY_ITEM_REQUEST", "data": {"shop_name": shop_name, "item_name": item_name}})
        
    def _sync(self):
        if self.is_dm and self.network:
            self.game_state._trigger_gui_update()
            from common.protocol import make_game_state
            from server.network import broadcast
            broadcast(self.network.game_state, make_game_state(self.network.game_state.get_state_dict()))

