import io
with io.open('client/client.py', 'r', encoding='utf-8') as f:
    content = f.read()
target = '        else:\n            self.request_move(clicked_hex)'
replacement = '''        else:
            loots = getattr(self, "map_data", {}).get("loots", []) if getattr(self, "map_data", None) else []
            loot_found = None
            for l in loots:
                if l["q"] == clicked_hex.q and l["r"] == clicked_hex.r:
                    loot_found = l
                    break
            if loot_found:
                if messagebox.askyesno("Bottino", f"C'e' un forziere qui contenente: {loot_found['qty']}x {loot_found['item']}.\nVuoi raccoglierlo?"):
                    self.network.send({"type": "TAKE_LOOT_REQUEST", "data": {"q": clicked_hex.q, "r": clicked_hex.r}})
            else:
                self.request_move(clicked_hex)'''
if target in content:
    with io.open('client/client.py', 'w', encoding='utf-8') as f:
        f.write(content.replace(target, replacement))
    print('Patched successfully')
else:
    print('Target not found')
