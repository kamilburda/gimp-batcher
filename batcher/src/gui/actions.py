"""Widgets to interactively edit actions (procedures/constraints)."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

import gi
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi
from gi.repository import GObject
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Pango

import pygimplib as pg
from pygimplib import pdb

from src import actions as actions_
from src.gui import editable_label as editable_label_
from src.gui import placeholders as gui_placeholders_
from src.gui import messages as gui_messages_


class ActionBox(pg.gui.ItemBox):
  """A scrollable vertical box that allows the user to add, edit and remove
  actions interactively.

  An action represents a procedure or constraint that can be applied to a
  GIMP item (image, layer, ...). Actions can be created via the `src.actions`
  module.

  Actions are applied starting from the top (i.e. actions ordered higher take
  precedence).

  The box connects events to the passed actions that keeps the actions and
  the box in sync. For example, when adding an action via `src.actions.add()`,
  the item for the action is automatically added to the box. Conversely, when
  calling `add_item()` from this class, both the action and the item are
  added to the actions and the GUI, respectively.
  
  Signals:
  
  * ``'action-box-item-added'`` - An item (action) was added via `add_item()`.
    
    Arguments:
    
    * The added item.
    
  * ``'action-box-item-reordered'`` - An item (action) was reordered via
    `reorder_item()`.
    
    Arguments:
    
    * The reordered item.
    * The new position of the reordered item (starting from 0).
    
  * ``'action-box-item-removed'`` - An item (action) was removed via
    `remove_item()`.
    
    Arguments:
    
    * The removed item.
  """
  
  __gsignals__ = {
    'action-box-item-added': (
      GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
    'action-box-item-reordered': (
      GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT, GObject.TYPE_INT)),
    'action-box-item-removed': (
      GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
  }
  
  _ADD_BUTTON_HBOX_SPACING = 6
  
  def __init__(
        self,
        actions: pg.setting.Group,
        builtin_actions: Optional[Dict[str, Any]] = None,
        add_action_text: Optional[str] = None,
        edit_action_text: Optional[str] = None,
        allow_custom_actions: bool = True,
        add_custom_action_text: Optional[str] = None,
        item_spacing: int = pg.gui.ItemBox.ITEM_SPACING,
        **kwargs):
    super().__init__(item_spacing=item_spacing, **kwargs)
    
    self._actions = actions
    self._builtin_actions = builtin_actions if builtin_actions is not None else {}
    self._add_action_text = add_action_text
    self._edit_action_text = edit_action_text
    self._allow_custom_actions = allow_custom_actions
    self._add_custom_action_text = add_custom_action_text
    
    self._pdb_procedure_browser_dialog = None
    
    self._init_gui()
    
    self._after_add_action_event_id = self._actions.connect_event(
      'after-add-action',
      lambda _actions, action, orig_action_dict: self._add_item_from_action(action))
    
    self._after_reorder_action_event_id = self._actions.connect_event(
      'after-reorder-action',
      lambda _actions, action, current_position, new_position: (
        self._reorder_action(action, new_position)))
    
    self._before_remove_action_event_id = self._actions.connect_event(
      'before-remove-action',
      lambda _actions, action: self._remove_action(action))
    
    self._before_clear_actions_event_id = self._actions.connect_event(
      'before-clear-actions', lambda _actions: self._clear())
  
  def add_item(
        self,
        action_dict_or_pdb_proc_name: Union[Dict[str, Any], str],
  ) -> _ActionBoxItem:
    self._actions.set_event_enabled(self._after_add_action_event_id, False)
    action = actions_.add(self._actions, action_dict_or_pdb_proc_name)
    self._actions.set_event_enabled(self._after_add_action_event_id, True)
    
    item = self._add_item_from_action(action)
    
    self.emit('action-box-item-added', item)
    
    return item
  
  def reorder_item(self, item, new_position):
    processed_new_position = self._reorder_item(item, new_position)
    
    self._actions.set_event_enabled(self._after_reorder_action_event_id, False)
    actions_.reorder(self._actions, item.action.name, processed_new_position)
    self._actions.set_event_enabled(self._after_reorder_action_event_id, True)
    
    self.emit('action-box-item-reordered', item, new_position)
  
  def remove_item(self, item):
    self._remove_item(item)
    
    self._actions.set_event_enabled(self._before_remove_action_event_id, False)
    actions_.remove(self._actions, item.action.name)
    self._actions.set_event_enabled(self._before_remove_action_event_id, True)
    
    self.emit('action-box-item-removed', item)
  
  def _init_gui(self):
    self._button_add = Gtk.Button(relief=Gtk.ReliefStyle.NONE)

    if self._add_action_text is not None:
      button_hbox = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL,
        spacing=self._ADD_BUTTON_HBOX_SPACING,
      )
      button_hbox.pack_start(
        Gtk.Image.new_from_icon_name(GimpUi.ICON_LIST_ADD, Gtk.IconSize.MENU), False, False, 0)
      
      label_add = Gtk.Label(
        label=self._add_action_text,
        use_underline=True,
      )
      button_hbox.pack_start(label_add, False, False, 0)

      self._button_add.add(button_hbox)
    else:
      self._button_add.set_image(
        Gtk.Image.new_from_icon_name(GimpUi.ICON_LIST_ADD, Gtk.IconSize.BUTTON))

    self._button_add.connect('clicked', self._on_button_add_clicked)
    
    self._vbox.pack_start(self._button_add, False, False, 0)
    
    self._actions_menu = Gtk.Menu()
    # key: tuple of menu path components; value: `Gtk.MenuItem`
    self._builtin_actions_submenus = {}
    self._init_actions_menu_popup()
  
  def _add_item_from_action(self, action):
    self._init_action_item_gui(action)

    item = _ActionBoxItem(action)
    
    super().add_item(item)
    
    return item
  
  def _init_action_item_gui(self, action):
    action.initialize_gui()

    if isinstance(action['display_name'].gui, pg.setting.SETTING_GUI_TYPES.label):
      label_widget = action['display_name'].gui.widget
      label_widget.set_ellipsize(Pango.EllipsizeMode.END)
      label_widget.connect(
        'size-allocate', self._on_action_item_gui_label_size_allocate, label_widget)
  
  @staticmethod
  def _on_action_item_gui_label_size_allocate(item_gui_label, allocation, item_gui):
    if pg.gui.label_fits_text(item_gui_label):
      item_gui.set_tooltip_text(None)
    else:
      item_gui.set_tooltip_text(item_gui_label.get_text())
  
  def _reorder_action(self, action, new_position):
    item = next((item_ for item_ in self._items if item_.action.name == action.name), None)
    if item is not None:
      self._reorder_item(item, new_position)
    else:
      raise ValueError(f'action "{action.name}" does not match any item in "{self}"')
  
  def _reorder_item(self, item, new_position):
    return super().reorder_item(item, new_position)
  
  def _remove_action(self, action):
    item = next((item_ for item_ in self._items if item_.action.name == action.name), None)
    
    if item is not None:
      self._remove_item(item)
    else:
      raise ValueError(f'action "{action.get_path()}" does not match any item in "{self}"')
  
  def _remove_item(self, item):
    if self._get_item_position(item) == len(self._items) - 1:
      self._button_add.grab_focus()
    
    super().remove_item(item)
  
  def _clear(self):
    for _unused in range(len(self._items)):
      self._remove_item(self._items[0])
  
  def _init_actions_menu_popup(self):
    for action_dict in self._builtin_actions.values():
      self._add_action_to_menu_popup(action_dict)
    
    if self._allow_custom_actions:
      self._actions_menu.append(Gtk.SeparatorMenuItem())
      self._add_add_custom_action_to_menu_popup()
    
    self._actions_menu.show_all()
  
  def _on_button_add_clicked(self, button):
    self._actions_menu.popup_at_pointer(None)
  
  def _add_action_to_menu_popup(self, action_dict):
    if action_dict.get('menu_path') is None:
      current_parent_menu = self._actions_menu
    else:
      parent_names = tuple(action_dict['menu_path'].split(pg.MENU_PATH_SEPARATOR))

      current_parent_menu = self._actions_menu
      for i in range(len(parent_names)):
        current_names = parent_names[:i + 1]

        if current_names not in self._builtin_actions_submenus:
          self._builtin_actions_submenus[current_names] = Gtk.MenuItem(
            label=current_names[-1], use_underline=False)
          self._builtin_actions_submenus[current_names].set_submenu(Gtk.Menu())

          current_parent_menu.append(self._builtin_actions_submenus[current_names])

        current_parent_menu = self._builtin_actions_submenus[current_names].get_submenu()

    menu_item = Gtk.MenuItem(label=action_dict['display_name'], use_underline=False)
    menu_item.connect('activate', self._on_actions_menu_item_activate, action_dict)

    current_parent_menu.append(menu_item)
  
  def _on_actions_menu_item_activate(self, menu_item, action_dict):
    self.add_item(action_dict)
  
  def _add_add_custom_action_to_menu_popup(self):
    menu_item = Gtk.MenuItem(label=self._add_custom_action_text, use_underline=False)
    menu_item.connect('activate', self._on_add_custom_action_menu_item_activate)
    self._actions_menu.append(menu_item)
  
  def _on_add_custom_action_menu_item_activate(self, menu_item):
    if self._pdb_procedure_browser_dialog:
      self._pdb_procedure_browser_dialog.show()
    else:
      self._pdb_procedure_browser_dialog = self._create_pdb_procedure_browser_dialog()
  
  def _create_pdb_procedure_browser_dialog(self):
    dialog = GimpUi.ProcBrowserDialog(
      title=_('Procedure Browser'),
      role=pg.config.PLUGIN_NAME,
    )

    dialog.add_buttons(
      Gtk.STOCK_ADD, Gtk.ResponseType.OK, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
    
    dialog.set_default_response(Gtk.ResponseType.OK)
    
    dialog.connect('response', self._on_pdb_procedure_browser_dialog_response)
    
    dialog.show_all()
    
    return dialog
  
  def _on_pdb_procedure_browser_dialog_response(self, dialog, response_id):
    if response_id == Gtk.ResponseType.OK:
      procedure_name = dialog.get_selected()
      if procedure_name:
        pdb_proc_action_dict = actions_.get_action_dict_for_pdb_procedure(procedure_name)
        pdb_proc_action_dict['enabled'] = False
        
        self.add_item(pdb_proc_action_dict)
    
    dialog.hide()


class _ActionBoxItem(pg.gui.ItemBoxItem):

  _LABEL_ACTION_NAME_MAX_WIDTH_CHARS = 50
  _ACTION_NAME_STYLE_CLASS = 'action-enabled'
  
  def __init__(self, action):
    self._action = action

    self._hbox_action_name = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    self._event_box_action_name = Gtk.EventBox()
    self._event_box_action_name.add(self._hbox_action_name)

    super().__init__(self._event_box_action_name, button_display_mode='always')

    self._label_action_name = self._create_label_action_name()
    self._label_action_name_for_editing = self._create_label_action_name_for_editing()

    self._action_settings_widget = _ActionSettingsWidget(self._action)
    self._action_settings_widget.show_all()
    self._action_settings_widget.set_no_show_all(True)
    self.vbox.pack_start(self._action_settings_widget, False, False, 0)

    self._button_enabled_images = {
      False: Gtk.Image.new_from_icon_name('checkbox', Gtk.IconSize.BUTTON),
      True: Gtk.Image.new_from_icon_name('checkbox-checked', Gtk.IconSize.BUTTON),
    }

    self._button_enabled = self._setup_item_button(
      self._button_enabled_images[self._action['enabled'].value], position=0)
    self._button_enabled.connect('clicked', self._on_button_enabled_clicked)

    self._button_edit = self._setup_item_button(GimpUi.ICON_EDIT, position=0)
    self._button_edit.connect('clicked', self._on_button_edit_clicked)

    self._button_warning = self._setup_item_indicator_button(GimpUi.ICON_DIALOG_WARNING, position=0)
    self._button_warning.hide()
    
    self._display_warning_message_event_id = None

    self._update_item_widget_style_based_on_enabled_state()
    self._show_hide_action_settings()
  
  @property
  def action(self):
    return self._action

  @property
  def button_edit(self):
    return self._button_edit

  @property
  def button_enabled(self):
    return self._button_enabled
  
  def set_tooltip(self, text):
    self.widget.set_tooltip_text(text)
  
  def has_warning(self):
    return self._button_warning.get_visible()
  
  def set_warning(self, show, main_message=None, failure_message=None, details=None, parent=None):
    if show:
      self.set_tooltip(failure_message)

      if self._display_warning_message_event_id is not None:
        self._button_warning.disconnect(self._display_warning_message_event_id)

      self._display_warning_message_event_id = self._button_warning.connect(
        'clicked',
        self._on_button_warning_clicked, main_message, failure_message, details, parent)
      
      self._button_warning.show()
    else:
      self._button_warning.hide()
      
      self.set_tooltip(None)
      if self._display_warning_message_event_id is not None:
        self._button_warning.disconnect(self._display_warning_message_event_id)
        self._display_warning_message_event_id = None

  def _create_label_action_name(self):
    label_action_name = self._action['display_name'].gui.widget
    label_action_name.set_max_width_chars(self._LABEL_ACTION_NAME_MAX_WIDTH_CHARS)

    self._label_action_name_css_provider = self._create_and_attach_css_provider_to_widget(
      label_action_name, self._ACTION_NAME_STYLE_CLASS)

    return label_action_name

  def _create_label_action_name_for_editing(self):
    label_action_name_for_editing = editable_label_.EditableLabel()
    label_action_name_for_editing.label.set_ellipsize(Pango.EllipsizeMode.END)
    label_action_name_for_editing.label.set_label(self._action['display_name'].value)
    label_action_name_for_editing.label.set_max_width_chars(self._LABEL_ACTION_NAME_MAX_WIDTH_CHARS)
    label_action_name_for_editing.show_all()
    label_action_name_for_editing.connect('changed', self._on_label_action_name_changed)

    self._label_action_name_for_editing_css_provider = (
      self._create_and_attach_css_provider_to_widget(
        label_action_name_for_editing.label, self._ACTION_NAME_STYLE_CLASS))

    return label_action_name_for_editing

  @staticmethod
  def _create_and_attach_css_provider_to_widget(widget, style_class):
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(f'label.{style_class} {{font-weight: bold;}}'.encode())
    widget.get_style_context().add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    return css_provider

  def _on_label_action_name_changed(self, editable_label):
    self._action['display_name'].set_value(editable_label.label.get_text())
    editable_label.label.set_label(self._action['display_name'].value)

  @staticmethod
  def _on_button_warning_clicked(_button, main_message, short_message, full_message, parent):
    gui_messages_.display_failure_message(main_message, short_message, full_message, parent=parent)

  def _on_button_edit_clicked(self, _button):
    self._action['display_action_settings'].set_value(
      not self._action['display_action_settings'].value)

    self._show_hide_action_settings()

  def _on_button_enabled_clicked(self, _button):
    self._action['enabled'].set_value(not self._action['enabled'].value)
    self._button_enabled.set_image(self._button_enabled_images[self._action['enabled'].value])
    self._update_item_widget_style_based_on_enabled_state()

  def _show_hide_action_settings(self):
    if self._action['display_action_settings'].value:
      self._highlight_button(self._button_edit)

      self._action_settings_widget.show()

      for child in self._hbox_action_name.get_children():
        self._hbox_action_name.remove(child)

      self._hbox_action_name.pack_start(self._label_action_name_for_editing, True, True, 0)
    else:
      for child in self._hbox_action_name.get_children():
        self._hbox_action_name.remove(child)

      self._hbox_action_name.pack_start(self._label_action_name, True, True, 0)

      self._action_settings_widget.hide()

      self._unhighlight_button(self._button_edit)

  @staticmethod
  def _highlight_button(button):
    button.set_relief(Gtk.ReliefStyle.NORMAL)
    button.set_state_flags(Gtk.StateFlags.CHECKED, False)

  @staticmethod
  def _unhighlight_button(button):
    button.unset_state_flags(Gtk.StateFlags.CHECKED)
    button.set_relief(Gtk.ReliefStyle.NONE)

  def _update_item_widget_style_based_on_enabled_state(self):
    if self._action['enabled'].value:
      self._label_action_name.get_style_context().add_class(self._ACTION_NAME_STYLE_CLASS)
      self._label_action_name_for_editing.label.get_style_context().add_class(
        self._ACTION_NAME_STYLE_CLASS)
    else:
      self._label_action_name.get_style_context().remove_class(self._ACTION_NAME_STYLE_CLASS)
      self._label_action_name_for_editing.label.get_style_context().remove_class(
        self._ACTION_NAME_STYLE_CLASS)


class _ActionSettingsWidget(Gtk.Box):

  _LABEL_ACTION_NAME_STYLE_CLASS_NAME = 'action-name'
  
  _GRID_ROW_SPACING = 3
  _GRID_COLUMN_SPACING = 8

  _MORE_OPTIONS_SPACING = 3
  _MORE_OPTIONS_LABEL_TOP_MARGIN = 6
  _MORE_OPTIONS_LABEL_BOTTOM_MARGIN = 3

  _LABEL_ACTION_DESCRIPTION_MAX_WIDTH_CHARS = 50
  
  def __init__(self, action, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.set_orientation(Gtk.Orientation.VERTICAL)

    self._pdb_procedure = pdb[action['function'].value] if action['function'].value else None

    # TODO: Resolve how to handle resetting
    self._button_reset = Gtk.Button(label=_('_Reset'), use_underline=True)

    self._label_action_description = None
    
    if action['description'].value:
      self._label_action_description = self._create_label_description(action['description'].value)
    elif self._pdb_procedure is not None:
      self._label_action_description = self._create_label_description(
        self._pdb_procedure.proc.get_blurb(), self._pdb_procedure.proc.get_help())
    
    self._grid_action_arguments = Gtk.Grid(
      row_spacing=self._GRID_ROW_SPACING,
      column_spacing=self._GRID_COLUMN_SPACING,
    )
    
    self._vbox_more_options = Gtk.Box(
      orientation=Gtk.Orientation.VERTICAL,
      spacing=self._MORE_OPTIONS_SPACING,
      margin_top=self._MORE_OPTIONS_LABEL_BOTTOM_MARGIN,
    )
    self._vbox_more_options.pack_start(
      action['enabled_for_previews'].gui.widget, False, False, 0)
    if 'also_apply_to_parent_folders' in action:
      self._vbox_more_options.pack_start(
        action['also_apply_to_parent_folders'].gui.widget, False, False, 0)
    
    action['more_options_expanded'].gui.widget.add(self._vbox_more_options)
    action['more_options_expanded'].gui.widget.set_margin_top(self._MORE_OPTIONS_LABEL_TOP_MARGIN)

    if self._label_action_description is not None:
      self.pack_start(self._label_action_description, False, False, 0)
    self.pack_start(self._grid_action_arguments, True, True, 0)
    self.pack_start(action['more_options_expanded'].gui.widget, False, False, 0)
    
    self._set_arguments(action, self._pdb_procedure)
    
    self._button_reset.connect('clicked', self._on_button_reset_clicked, action)

  def _create_label_description(self, summary, full_description=None):
    label_description = Gtk.Label(
      label=summary,
      xalign=0.0,
      yalign=0.5,
      ellipsize=Pango.EllipsizeMode.END,
      wrap=True,
      max_width_chars=self._LABEL_ACTION_DESCRIPTION_MAX_WIDTH_CHARS,
    )
    if full_description:
      label_description.set_tooltip_text(full_description)
    
    return label_description
  
  def _set_arguments(self, action, pdb_procedure):
    if pdb_procedure is not None:
      pdb_argument_names_and_blurbs = {
        arg.name: arg.blurb for arg in pdb_procedure.proc.get_arguments()}
    else:
      pdb_argument_names_and_blurbs = {}

    row_index = 0

    for setting in action['arguments']:
      if not setting.gui.get_visible():
        continue
      
      label = Gtk.Label(
        label=setting.display_name,
        xalign=0.0,
        yalign=0.5,
      )

      if pdb_procedure is not None and setting.name in pdb_argument_names_and_blurbs:
        label.set_tooltip_text(pdb_argument_names_and_blurbs[setting.name])
      
      self._grid_action_arguments.attach(label, 0, row_index, 1, 1)
      
      widget_to_attach = setting.gui.widget
      
      if isinstance(setting.gui, pg.setting.SETTING_GUI_TYPES.null):
        widget_to_attach = gui_placeholders_.create_placeholder_widget()
      else:
        if (isinstance(setting, pg.setting.ArraySetting)
            and not setting.element_type.get_allowed_gui_types()):
          widget_to_attach = gui_placeholders_.create_placeholder_widget()
      
      self._grid_action_arguments.attach(widget_to_attach, 1, row_index, 1, 1)

      row_index += 1
  
  @staticmethod
  def _on_button_reset_clicked(button, action):
    action['arguments'].reset()
