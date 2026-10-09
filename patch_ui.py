import io
with io.open('components/ui_components.py', 'r', encoding='utf-8') as f:
    content = f.read()
target = '        for name, pdata in self.players_data.items():'
replacement = '''        # Draw Loots
        loots_data = self.map_data.get("loots", [])
        for l in loots_data:
            lh = Hex(l["q"], l["r"])
            if fow_enabled and not is_dm and lh not in fow_revealed:
                continue
            cx, cy = self.hex_layout.hex_to_pixel(lh)
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            self.create_rectangle(sx-10, sy-10, sx+10, sy+10, fill="gold", outline="brown")
            self.create_text(sx, sy, text="Loot", font=("", max(8, int(10*self.zoom_level))))
            
        # Draw Lights
        lights_data = self.map_data.get("lights", [])
        for l in lights_data:
            lh = Hex(l["q"], l["r"])
            if fow_enabled and not is_dm and lh not in fow_revealed:
                continue
            cx, cy = self.hex_layout.hex_to_pixel(lh)
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            self.create_oval(sx-5, sy-5, sx+5, sy+5, fill="yellow", outline="orange")
            
        for name, pdata in self.players_data.items():'''
if target in content:
    with io.open('components/ui_components.py', 'w', encoding='utf-8') as f:
        f.write(content.replace(target, replacement))
    print('Patched UI successfully')
else:
    print('Target not found')
