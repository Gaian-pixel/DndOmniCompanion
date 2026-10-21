# server/flow_canvas.py
"""
Flow Canvas: Componente visivo interattivo per la visualizzazione e manipolazione
a nodi della campagna (Campaign Flow Builder).
Supporta rendering Dark Fantasy, curve di Bezier, porte di connessione,
drag & drop, pan, zoom, indicatore di posizione del party e breadcrumbs di sessione.
"""

import math
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Callable, Tuple, Any

from common.theme import (
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT, SURFACE_LIGHT,
    BORDER_COLOR, BORDER_GOLD, ACCENT_GOLD, ACCENT_GOLD_LIGHT,
    ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE, TEXT_COLOR, TEXT_MUTED, TEXT_DARK,
    FONT_MAIN, FONT_BOLD, FONT_SMALL, FONT_BADGE
)
from common.campaign_script import FlowGraph, FlowNode, FlowEdge, NODE_TYPES


NODE_WIDTH = 210
NODE_HEIGHT = 80
PORT_RADIUS = 6


class FlowCanvas(tk.Frame):
    """
    Canvas infinito interattivo a nodi per DndOmniCompanion.
    """
    def __init__(self, master, graph: Optional[FlowGraph] = None, on_change_callback: Optional[Callable] = None, is_dm_live: bool = False):
        super().__init__(master, bg=BG_COLOR)
        self.graph = graph or FlowGraph()
        self.on_change_callback = on_change_callback
        self.is_dm_live = is_dm_live

        # Stato Party e Sessione
        self.active_party_node_id: Optional[str] = None
        self.visited_node_ids: List[str] = []

        # Stato Viewport (Pan e Zoom)
        self.scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

        # Stato Interazioni
        self.selected_node_id: Optional[str] = None
        self.dragged_node_id: Optional[str] = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.pan_start_x = 0
        self.pan_start_y = 0

        # Connessione nodi interattiva (tirando linee tra porte)
        self.connecting_from_node_id: Optional[str] = None
        self.temp_line_id: Optional[int] = None

        # Elementi Canvas
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._bind_events()
        self.render()

    def _bind_events(self):
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<B1-Motion>", self._on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_release)

        # Pan con tasto centrale o destro
        self.canvas.bind("<Button-2>", self._on_pan_start)
        self.canvas.bind("<B2-Motion>", self._on_pan_drag)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<B3-Motion>", self._on_pan_drag)

        # Zoom con rotellina
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)

    # -----------------------------------------------------------------------
    # COORDINATE SYSTEM & ZOOM / PAN
    # -----------------------------------------------------------------------

    def world_to_screen(self, wx: float, wy: float) -> Tuple[float, float]:
        sx = (wx * self.scale) + self.pan_x
        sy = (wy * self.scale) + self.pan_y
        return sx, sy

    def screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        wx = (sx - self.pan_x) / self.scale
        wy = (sy - self.pan_y) / self.scale
        return wx, wy

    def _on_pan_start(self, event):
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def _on_pan_drag(self, event):
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        self.pan_x += dx
        self.pan_y += dy
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.render()

    def _on_mousewheel(self, event):
        factor = 1.1 if event.delta > 0 else 0.9
        new_scale = max(0.4, min(2.5, self.scale * factor))

        # Centra lo zoom attorno alla posizione del cursore
        mx, my = event.x, event.y
        self.pan_x = mx - (mx - self.pan_x) * (new_scale / self.scale)
        self.pan_y = my - (my - self.pan_y) * (new_scale / self.scale)
        self.scale = new_scale
        self.render()

    # -----------------------------------------------------------------------
    # RENDERING DEL GRAFO
    # -----------------------------------------------------------------------

    def set_graph(self, graph: FlowGraph):
        self.graph = graph
        self.render()

    def render(self):
        self.canvas.delete("all")
        self._draw_grid_background()
        self._draw_edges()
        self._draw_nodes()

    def _draw_grid_background(self):
        """Disegna una griglia a punti o linee sottili per orientamento."""
        w = self.canvas.winfo_width() or 1000
        h = self.canvas.winfo_height() or 700
        grid_size = int(40 * self.scale)
        if grid_size <= 15:
            return

        start_x = int(self.pan_x % grid_size)
        start_y = int(self.pan_y % grid_size)

        for x in range(start_x, w, grid_size):
            self.canvas.create_line(x, 0, x, h, fill="#181A1F", width=1)
        for y in range(start_y, h, grid_size):
            self.canvas.create_line(0, y, w, y, fill="#181A1F", width=1)

    def _draw_edges(self):
        """Disegna le connessioni curve tra nodi."""
        for edge in self.graph.edges:
            src = self.graph.nodes.get(edge.from_id)
            dst = self.graph.nodes.get(edge.to_id)
            if not src or not dst:
                continue

            # Coordinate mondo delle porte: Uscita destra di src, Entrata sinistra di dst
            src_wx = src.x + NODE_WIDTH
            src_wy = src.y + NODE_HEIGHT / 2.0

            dst_wx = dst.x
            dst_wy = dst.y + NODE_HEIGHT / 2.0

            # Converti a schermo
            sx1, sy1 = self.world_to_screen(src_wx, src_wy)
            sx2, sy2 = self.world_to_screen(dst_wx, dst_wy)

            # Controlla se fa parte del percorso percorso dal party
            is_visited_edge = (src.id in self.visited_node_ids and dst.id in self.visited_node_ids)
            edge_color = ACCENT_GOLD if is_visited_edge else "#495057"
            edge_width = max(2, int(2.5 * self.scale)) if is_visited_edge else max(1, int(1.5 * self.scale))
            dash_pattern = None if not dst.node_type == "off_track" else (4, 4)

            # Disegna curva Bezier fluida
            ctrl_dist = max(40.0 * self.scale, abs(sx2 - sx1) * 0.5)
            c1x = sx1 + ctrl_dist
            c1y = sy1
            c2x = sx2 - ctrl_dist
            c2y = sy2

            # Genera punti intermedi approssimati per la linea
            pts = []
            for t_step in range(11):
                t = t_step / 10.0
                omt = 1.0 - t
                bx = (omt**3)*sx1 + 3*(omt**2)*t*c1x + 3*omt*(t**2)*c2x + (t**3)*sx2
                by = (omt**3)*sy1 + 3*(omt**2)*t*c1y + 3*omt*(t**2)*c2y + (t**3)*sy2
                pts.extend([bx, by])

            self.canvas.create_line(
                pts, fill=edge_color, width=edge_width,
                arrow=tk.LAST, arrowshape=(int(8*self.scale), int(10*self.scale), int(4*self.scale)),
                dash=dash_pattern, tags=("edge", f"edge_{edge.from_id}_{edge.to_id}")
            )

            # Etichetta bivio / condizione nel mezzo
            if edge.label:
                mid_x = (sx1 + sx2) / 2.0
                mid_y = (sy1 + sy2) / 2.0
                pad_x = 8 * self.scale
                pad_y = 3 * self.scale

                txt_id = self.canvas.create_text(
                    mid_x, mid_y, text=edge.label,
                    fill=ACCENT_GOLD if is_visited_edge else TEXT_COLOR,
                    font=("Segoe UI", max(7, int(8 * self.scale)), "bold")
                )
                bbox = self.canvas.bbox(txt_id)
                if bbox:
                    bg_tag = self.canvas.create_rectangle(
                        bbox[0] - pad_x, bbox[1] - pad_y, bbox[2] + pad_x, bbox[3] + pad_y,
                        fill=SURFACE_COLOR, outline=BORDER_COLOR, width=1
                    )
                    self.canvas.tag_lower(bg_tag, txt_id)

    def _draw_nodes(self):
        """Disegna le schede dei nodi con stile Dark Fantasy."""
        for node in self.graph.nodes.values():
            sx, sy = self.world_to_screen(node.x, node.y)
            w = NODE_WIDTH * self.scale
            h = NODE_HEIGHT * self.scale

            type_info = NODE_TYPES.get(node.node_type, NODE_TYPES["note"])
            accent_col = type_info["color"]
            icon = type_info["icon"]
            type_label = type_info["label"]

            is_selected = (node.id == self.selected_node_id)
            is_active_party = (node.id == self.active_party_node_id)
            is_visited = (node.id in self.visited_node_ids)

            # 1. Alone / Halo dorato pulsante se il Party si trova qui
            if is_active_party:
                halo_pad = 8 * self.scale
                self.canvas.create_rectangle(
                    sx - halo_pad, sy - halo_pad, sx + w + halo_pad, sy + h + halo_pad,
                    fill="", outline=ACCENT_GOLD_LIGHT, width=max(2, int(3 * self.scale)),
                    tags=("party_halo",)
                )
                # Badge "VOI SIETE QUI" sopra al nodo
                self.canvas.create_rectangle(
                    sx + 10 * self.scale, sy - 18 * self.scale, sx + 130 * self.scale, sy - 2 * self.scale,
                    fill=ACCENT_GOLD, outline=""
                )
                self.canvas.create_text(
                    sx + 70 * self.scale, sy - 10 * self.scale,
                    text="📍 PARTY QUI", fill=TEXT_DARK,
                    font=("Segoe UI", max(7, int(8 * self.scale)), "bold")
                )

            # 2. Sfondo della scheda nodo
            bg_col = SURFACE_COLOR_ALT if is_selected else SURFACE_COLOR
            border_col = ACCENT_GOLD if (is_selected or is_active_party) else (BORDER_GOLD if is_visited else BORDER_COLOR)
            border_w = max(2, int(2 * self.scale)) if (is_selected or is_visited) else 1

            self.canvas.create_rectangle(
                sx, sy, sx + w, sy + h,
                fill=bg_col, outline=border_col, width=border_w,
                tags=("node", f"node_{node.id}", node.id)
            )

            # 3. Barra superiore colorata d'accento per tipo
            header_h = 24 * self.scale
            self.canvas.create_rectangle(
                sx, sy, sx + w, sy + header_h,
                fill="#16181C", outline=border_col, width=1,
                tags=("node", f"node_{node.id}", node.id)
            )
            # Strisciolina verticale colorata a sinistra
            self.canvas.create_rectangle(
                sx, sy, sx + (5 * self.scale), sy + h,
                fill=accent_col, outline="",
                tags=("node", f"node_{node.id}", node.id)
            )

            # Icona + Tipo
            f_header = ("Segoe UI", max(7, int(8 * self.scale)), "bold")
            self.canvas.create_text(
                sx + 12 * self.scale, sy + 12 * self.scale,
                text=f"{icon} {type_label.upper()}", fill=accent_col,
                font=f_header, anchor="w",
                tags=("node", f"node_{node.id}", node.id)
            )

            # Titolo del nodo
            f_title = ("Segoe UI", max(8, int(9 * self.scale)), "bold")
            # Taglia se troppo lungo
            display_title = node.title if len(node.title) <= 22 else node.title[:20] + "..."
            self.canvas.create_text(
                sx + 14 * self.scale, sy + 40 * self.scale,
                text=display_title, fill=TEXT_COLOR,
                font=f_title, anchor="w",
                tags=("node", f"node_{node.id}", node.id)
            )

            # Sottotitolo / Dettagli veloci
            sub_text = self._get_node_subtitle(node)
            f_sub = ("Segoe UI", max(6, int(7 * self.scale)))
            self.canvas.create_text(
                sx + 14 * self.scale, sy + 62 * self.scale,
                text=sub_text, fill=TEXT_MUTED,
                font=f_sub, anchor="w",
                tags=("node", f"node_{node.id}", node.id)
            )

            # 4. Porte di Connessione (Ingresso a SX, Uscita a DX)
            port_r = PORT_RADIUS * self.scale
            in_x = sx
            in_y = sy + (h / 2.0)
            out_x = sx + w
            out_y = sy + (h / 2.0)

            # Porta In
            self.canvas.create_oval(
                in_x - port_r, in_y - port_r, in_x + port_r, in_y + port_r,
                fill=SURFACE_COLOR_ALT, outline=accent_col, width=max(1, int(1.5 * self.scale)),
                tags=("port_in", f"port_in_{node.id}", node.id)
            )
            # Porta Out
            self.canvas.create_oval(
                out_x - port_r, out_y - port_r, out_x + port_r, out_y + port_r,
                fill=accent_col, outline=TEXT_DARK, width=1,
                tags=("port_out", f"port_out_{node.id}", node.id)
            )

    def _get_node_subtitle(self, node: FlowNode) -> str:
        d = node.data
        if node.node_type == "scene":
            return d.get("map_file", "Nessuna mappa")[:26]
        elif node.node_type == "encounter":
            m_cnt = len(d.get("monsters", []))
            cr = d.get("cr", "")
            cr_str = f" • CR {cr}" if cr else ""
            return f"{m_cnt} Mostri{cr_str}"
        elif node.node_type == "quest":
            objs = len(d.get("objectives", []))
            return f"{objs} Obiettivi configurati"
        elif node.node_type == "npc":
            return f"{d.get('role', 'Comune')} • {d.get('alignment', 'Neutrale')}"
        elif node.node_type == "hook":
            return "Spunto narrativo di partenza"
        elif node.node_type == "off_track":
            return "⚡ Azione Improvvisata"
        sec_cnt = len(d.get("secrets", []))
        return f"{sec_cnt} Segreti" if sec_cnt > 0 else "Nota narrativa"

    # -----------------------------------------------------------------------
    # GESTIONE EVENTI MOUSE & DRAG & DROP
    # -----------------------------------------------------------------------

    def _on_left_click(self, event):
        items = self.canvas.find_withtag("current")
        if not items:
            self.selected_node_id = None
            self.render()
            return

        item = items[0]
        tags = self.canvas.gettags(item)

        # Controlla se cliccata una porta di uscita per iniziare una connessione
        if "port_out" in tags:
            for t in tags:
                if t in self.graph.nodes:
                    self.connecting_from_node_id = t
                    self.drag_start_x = event.x
                    self.drag_start_y = event.y
                    return

        # Controlla se cliccato un nodo
        for t in tags:
            if t in self.graph.nodes:
                self.selected_node_id = t
                self.dragged_node_id = t
                self.drag_start_x = event.x
                self.drag_start_y = event.y
                self.render()
                return

        self.selected_node_id = None
        self.render()

    def _on_left_drag(self, event):
        # 1. Se stiamo tirando un filo di connessione
        if self.connecting_from_node_id:
            if self.temp_line_id:
                self.canvas.delete(self.temp_line_id)
            self.temp_line_id = self.canvas.create_line(
                self.drag_start_x, self.drag_start_y, event.x, event.y,
                fill=ACCENT_GOLD, width=2, dash=(4, 2), arrow=tk.LAST
            )
            return

        # 2. Se stiamo trascinando un nodo
        if self.dragged_node_id:
            dx = (event.x - self.drag_start_x) / self.scale
            dy = (event.y - self.drag_start_y) / self.scale
            node = self.graph.nodes.get(self.dragged_node_id)
            if node:
                node.x += dx
                node.y += dy
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.render()

    def _on_left_release(self, event):
        # Se stavamo creando una connessione
        if self.connecting_from_node_id:
            if self.temp_line_id:
                self.canvas.delete(self.temp_line_id)
                self.temp_line_id = None

            # Controlla su cosa abbiamo rilasciato
            items = self.canvas.find_overlapping(event.x - 10, event.y - 10, event.x + 10, event.y + 10)
            target_id = None
            for it in items:
                tags = self.canvas.gettags(it)
                for t in tags:
                    if t in self.graph.nodes and t != self.connecting_from_node_id:
                        target_id = t
                        break
                if target_id:
                    break

            if target_id:
                # Evita duplicati
                exists = any(e.from_id == self.connecting_from_node_id and e.to_id == target_id for e in self.graph.edges)
                if not exists:
                    self.graph.edges.append(FlowEdge(from_id=self.connecting_from_node_id, to_id=target_id))
                    if self.on_change_callback:
                        self.on_change_callback()

            self.connecting_from_node_id = None
            self.render()
            return

        # Se abbiamo finito di trascinare un nodo
        if self.dragged_node_id:
            self.dragged_node_id = None
            if self.on_change_callback:
                self.on_change_callback()

    def _on_double_click(self, event):
        items = self.canvas.find_withtag("current")
        if not items:
            return
        tags = self.canvas.gettags(items[0])
        for t in tags:
            if t in self.graph.nodes:
                self._open_node_editor(self.graph.nodes[t])
                return

    def _on_right_click(self, event):
        items = self.canvas.find_withtag("current")
        clicked_node: Optional[FlowNode] = None
        if items:
            for t in self.canvas.gettags(items[0]):
                if t in self.graph.nodes:
                    clicked_node = self.graph.nodes[t]
                    break

        menu = tk.Menu(self, tearoff=0, bg=SURFACE_COLOR, fg=TEXT_COLOR)
        if clicked_node:
            self.selected_node_id = clicked_node.id
            if self.is_dm_live:
                menu.add_command(label="📍 Imposta Party Qui", command=lambda: self.set_active_party_node(clicked_node.id))
                menu.add_separator()
            menu.add_command(label="✏️ Modifica Dettagli...", command=lambda: self._open_node_editor(clicked_node))
            menu.add_command(label="🗑️ Elimina Nodo", command=lambda: self._delete_node(clicked_node.id))
        else:
            # Click su spazio vuoto
            wx, wy = self.screen_to_world(event.x, event.y)
            menu.add_command(label="➕ Aggiungi Scena...", command=lambda: self._quick_add_node("scene", wx, wy))
            menu.add_command(label="⚔️ Aggiungi Incontro...", command=lambda: self._quick_add_node("encounter", wx, wy))
            menu.add_command(label="👤 Aggiungi PNG...", command=lambda: self._quick_add_node("npc", wx, wy))
            menu.add_command(label="📢 Aggiungi Spunto...", command=lambda: self._quick_add_node("hook", wx, wy))
            menu.add_command(label="⚡ Aggiungi Fuori Pista...", command=lambda: self._quick_add_node("off_track", wx, wy))
            menu.add_separator()
            menu.add_command(label="🔍 Centra Vista", command=self.reset_view)

        menu.tk_popup(event.x_root, event.y_root)

    # -----------------------------------------------------------------------
    # OPERAZIONI SUI NODI
    # -----------------------------------------------------------------------

    def set_active_party_node(self, node_id: str):
        self.active_party_node_id = node_id
        if node_id not in self.visited_node_ids:
            self.visited_node_ids.append(node_id)
        self.render()

    def _delete_node(self, node_id: str):
        if node_id in self.graph.nodes:
            del self.graph.nodes[node_id]
            # Elimina connessioni collegate
            self.graph.edges = [e for e in self.graph.edges if e.from_id != node_id and e.to_id != node_id]
            if self.selected_node_id == node_id:
                self.selected_node_id = None
            if self.on_change_callback:
                self.on_change_callback()
            self.render()

    def _quick_add_node(self, node_type: str, wx: float, wy: float):
        type_info = NODE_TYPES.get(node_type, NODE_TYPES["note"])
        new_id = f"node_{len(self.graph.nodes) + 1}_{node_type}"
        new_node = FlowNode(
            id=new_id,
            node_type=node_type,
            title=f"Nuovo {type_info['label']}",
            x=wx,
            y=wy,
            data={}
        )
        self.graph.nodes[new_id] = new_node
        self.selected_node_id = new_id
        if self.on_change_callback:
            self.on_change_callback()
        self.render()

    def reset_view(self):
        self.scale = 1.0
        self.pan_x = 40.0
        self.pan_y = 40.0
        self.render()

    def _open_node_editor(self, node: FlowNode):
        """Apre un dialogo modale pulito per modificare titolo e dati del singolo nodo."""
        dlg = tk.Toplevel(self)
        dlg.title(f"Modifica Nodo • {node.title}")
        dlg.geometry("450x380")
        dlg.configure(bg=BG_COLOR)
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        container = tk.Frame(dlg, bg=BG_COLOR, padx=14, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="Titolo del Nodo:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        ent_title = ttk.Entry(container, font=FONT_MAIN)
        ent_title.insert(0, node.title)
        ent_title.pack(fill=tk.X, pady=(2, 10))

        tk.Label(container, text="Tipo di Nodo:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        combo_type = ttk.Combobox(container, values=list(NODE_TYPES.keys()), state="readonly")
        combo_type.set(node.node_type)
        combo_type.pack(fill=tk.X, pady=(2, 10))

        tk.Label(container, text="Descrizione / Narrazione:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        txt_desc = tk.Text(container, height=6, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_MAIN, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        txt_desc.insert("1.0", node.data.get("read_aloud", "") or node.data.get("notes", ""))
        txt_desc.pack(fill=tk.BOTH, expand=True, pady=(2, 12))

        def save_and_close():
            node.title = ent_title.get().strip() or "Senza Titolo"
            node.node_type = combo_type.get()
            node.data["read_aloud"] = txt_desc.get("1.0", tk.END).strip()
            dlg.destroy()
            if self.on_change_callback:
                self.on_change_callback()
            self.render()

        btn_box = tk.Frame(container, bg=BG_COLOR)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text="Salva Modifiche", command=save_and_close, style="Gold.TButton").pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_box, text="Annulla", command=dlg.destroy).pack(side=tk.RIGHT)
