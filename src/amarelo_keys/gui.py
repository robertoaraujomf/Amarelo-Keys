#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
from .config import ConfigManager, KeyMapping


class AmareloKeysGUI(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='br.com.amarelosoftware.amarelo-keys')
        self.config = ConfigManager()
        self.connect('activate', self.on_activate)
    
    def on_activate(self, app):
        self.window = Gtk.ApplicationWindow.new(app)
        self.window.set_title("Amarelo Keys")
        self.window.set_default_size(700, 500)
        
        self._build_ui()
        self.window.present()
    
    def _build_ui(self):
        header = Gtk.HeaderBar.new()
        
        title_label = Gtk.Label.new("Amarelo Keys")
        title_label.set_markup("<b>Amarelo Keys</b>")
        header.set_title_widget(title_label)
        
        header.set_show_title_buttons(True)
        self.window.set_titlebar(header)
        
        add_btn = Gtk.Button.new_with_label("+ Adicionar")
        add_btn.connect('clicked', lambda _: self._show_add_dialog())
        header.pack_start(add_btn)
        
        scrolled = Gtk.ScrolledWindow.new()
        scrolled.set_vexpand(True)
        self.window.set_child(scrolled)
        
        self.list_box = Gtk.ListBox.new()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.set_child(self.list_box)
        
        self._refresh_list()
    
    def _refresh_list(self):
        while (child := self.list_box.get_first_child()):
            self.list_box.remove(child)
        
        for mapping in self.config.get_all_mappings():
            self._add_mapping_row(mapping)
        
        if not self.config.get_all_mappings():
            label = Gtk.Label.new("Nenhum mapeamento configurado.\nClique em + Adicionar para começar.")
            label.set_halign(Gtk.Align.CENTER)
            label.set_valign(Gtk.Align.CENTER)
            self.list_box.append(label)
    
    def _add_mapping_row(self, mapping: KeyMapping):
        box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        
        trigger_label = Gtk.Label.new(f"🔑 {mapping.trigger_key}")
        trigger_label.set_width_chars(15)
        
        arrow = Gtk.Label.new("→")
        
        target_label = Gtk.Label.new(f"⌨️ {mapping.target_key}")
        target_label.set_width_chars(15)
        
        disable_switch = Gtk.Switch.new()
        disable_switch.set_active(mapping.disable_original)
        disable_switch.connect('state-set', 
            lambda s, state: self.config.update_mapping(
                mapping.trigger_key, disable_original=state))
        
        disable_label = Gtk.Label.new("Desativar original")
        disable_label.set_width_chars(12)
        
        enabled_switch = Gtk.Switch.new()
        enabled_switch.set_active(mapping.enabled)
        enabled_switch.connect('state-set',
            lambda s, state: self.config.update_mapping(
                mapping.trigger_key, enabled=state))
        
        delete_btn = Gtk.Button.new_from_icon_name("edit-delete")
        delete_btn.connect('clicked', lambda _: self._delete_mapping(mapping))
        
        box.append(trigger_label)
        box.append(arrow)
        box.append(target_label)
        box.append(disable_label)
        box.append(disable_switch)
        box.append(Gtk.Label.new("Ativo"))
        box.append(enabled_switch)
        box.append(delete_btn)
        
        self.list_box.append(box)
    
    def _delete_mapping(self, mapping: KeyMapping):
        self.config.remove_mapping(mapping.trigger_key)
        self._refresh_list()
    
    def _show_add_dialog(self):
        dialog = Gtk.Dialog.new()
        dialog.set_title("Adicionar Mapeamento")
        dialog.set_transient_for(self.window)
        dialog.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Adicionar", Gtk.ResponseType.OK
        )
        dialog.set_default_size(400, 200)
        
        content = dialog.get_content_area()
        content.set_spacing(12)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        
        content.append(Gtk.Label.new("Pressione a tecla de atalho (gatilho):"))
        
        trigger_entry = Gtk.Entry.new()
        trigger_entry.set_placeholder_text("Aguardando tecla...")
        trigger_entry.set_editable(False)
        content.append(trigger_entry)
        
        content.append(Gtk.Label.new("Digite a(s) tecla(s) de destino:"))
        
        target_entry = Gtk.Entry.new()
        target_entry.set_placeholder_text("Ex: m, tab, ctrl+c")
        content.append(target_entry)
        
        disable_check = Gtk.CheckButton.new_with_label("Desativar função original da tecla gatilho")
        content.append(disable_check)
        
        def on_key_press(entry, event):
            key_name = self._get_key_name_from_event(event)
            if key_name:
                trigger_entry.set_text(key_name)
            return True
        
        trigger_entry.add_controller(Gtk.EventControllerKey.new(
            key_press_callback=on_key_press
        ))
        
        dialog.connect('response', lambda d, resp: self._handle_add_response(
            d, resp, trigger_entry.get_text(), target_entry.get_text(), disable_check.get_active()
        ))
        dialog.present()
    
    def _get_key_name_from_event(self, event) -> str:
        keymap = Gdk.Keymap.get_for_display(Gdk.Display.get_default())
        keyval = event.keyval
        
        if keyval >= 32 and keyval <= 126:
            return chr(keyval).lower()
        
        key_name = Gdk.keyval_name(keyval)
        if key_name:
            key_name = key_name.lower()
            key_name = key_name.replace('_', ' ')
            return key_name
        
        return ""
    
    def _handle_add_response(self, dialog, response, trigger, target, disable_original):
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK and trigger and target:
            self.config.add_mapping(trigger, target, disable_original)
            self._refresh_list()


def launch_gui():
    app = AmareloKeysGUI()
    app.run(None)
