"""`setting.Presenter` subclasses for GTK GUI widgets."""

import inspect
import sys

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi
from gi.repository import GLib
from gi.repository import GObject
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from .. import gui as pggui
from .. import utils as pgutils

from . import presenter as presenter_


class GtkPresenter(presenter_.Presenter):
  """Abstract `setting.Presenter` subclass for GTK GUI widgets."""
  
  _ABSTRACT = True
  
  def __init__(self, *args, **kwargs):
    self._event_handler_id = None
    
    super().__init__(*args, **kwargs)
  
  def get_sensitive(self):
    return self._widget.get_sensitive()
  
  def set_sensitive(self, sensitive):
    self._widget.set_sensitive(sensitive)
  
  def get_visible(self):
    return self._widget.get_visible()
  
  def set_visible(self, visible):
    self._widget.set_visible(visible)
  
  def _connect_value_changed_event(self):
    self._event_handler_id = self._widget.connect(
      self._VALUE_CHANGED_SIGNAL, self._on_value_changed)
  
  def _disconnect_value_changed_event(self):
    self._widget.disconnect(self._event_handler_id)
    self._event_handler_id = None


class IntSpinButtonPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.SpinButton` widgets.
  
  Value: Integer value of the spin button.
  """
  
  _VALUE_CHANGED_SIGNAL = 'value-changed'
  
  def _create_widget(self, setting):
    return _create_spin_button(setting)
  
  def _get_value(self):
    return self._widget.get_value_as_int()
  
  def _set_value(self, value):
    self._widget.set_value(value)


class FloatSpinButtonPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.SpinButton` widgets.
  
  Value: Floating point value of the spin button.
  """
  
  _VALUE_CHANGED_SIGNAL = 'value-changed'
  
  def _create_widget(self, setting):
    return _create_spin_button(setting, digits=1)
  
  def _get_value(self):
    return self._widget.get_value()
  
  def _set_value(self, value):
    self._widget.set_value(value)


class CheckButtonPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.CheckButton` widgets.
  
  Value: Checked state of the check button (checked/unchecked).
  """
  
  _VALUE_CHANGED_SIGNAL = 'clicked'
  
  def _create_widget(self, setting):
    return Gtk.CheckButton(label=setting.display_name, use_underline=False)
  
  def _get_value(self):
    return self._widget.get_active()
  
  def _set_value(self, value):
    self._widget.set_active(value)


class CheckButtonNoTextPresenter(CheckButtonPresenter):
  """`setting.Presenter` subclass for `Gtk.CheckButton` widgets without text
  next to the checkbox.
  
  Value: Checked state of the check button (checked/unchecked).
  """
  
  def _create_widget(self, setting):
    return Gtk.CheckButton(label=None, use_underline=False)


class CheckButtonLabelPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.CheckButton` widgets.
  
  Value: Label of the check button.
  """
  
  def _get_value(self):
    label = self._widget.get_label()
    return label if label is not None else ''
  
  def _set_value(self, value):
    self._widget.set_label(value if value is not None else '')


class CheckMenuItemPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.CheckMenuItem` widgets.
  
  Value: Checked state of the menu item (checked/unchecked).
  """
  
  _VALUE_CHANGED_SIGNAL = 'toggled'
  
  def _create_widget(self, setting):
    return Gtk.CheckMenuItem(label=setting.display_name)
  
  def _get_value(self):
    return self._widget.get_active()
  
  def _set_value(self, value):
    self._widget.set_active(value)


class ExpanderPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.Expander` widgets.
  
  Value: ``True`` if the expander is expanded, ``False`` if collapsed.
  """
  
  _VALUE_CHANGED_SIGNAL = 'notify::expanded'
  
  def _create_widget(self, setting):
    return Gtk.Expander(label=setting.display_name, use_underline=True)
  
  def _get_value(self):
    return self._widget.get_expanded()
  
  def _set_value(self, value):
    self._widget.set_expanded(value)


class ComboBoxPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.ComboBox` widgets.

  The combo boxes contain two columns - displayed text and a numeric value
  associated with the text.

  Value: Item selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_widget(self, setting):
    model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_INT)

    for label, value in setting.get_item_display_names_and_values():
      model.append((label if label is not None else '', value))

    combo_box = Gtk.ComboBox(model=model, active=setting.default_value)

    renderer_text = Gtk.CellRendererText()
    combo_box.pack_start(renderer_text, True)
    combo_box.add_attribute(renderer_text, 'text', 0)
    
    return combo_box
  
  def _get_value(self):
    return self._widget.get_active()
  
  def _set_value(self, value):
    self._widget.set_active(value)


class EnumComboBoxPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `GimpUi.EnumComboBox` widgets.

  Value: Item selected in the enum combo box.
  """

  _VALUE_CHANGED_SIGNAL = 'changed'

  def _create_widget(self, setting):
    combo_box = GimpUi.EnumComboBox.new_with_model(GimpUi.EnumStore.new(setting.get_enum_type()))

    # If the default value is not valid, `set_active` returns `False`,
    # but otherwise does not result in errors.
    combo_box.set_active(setting.default_value)

    return combo_box

  def _get_value(self):
    return self._widget.get_active().value

  def _set_value(self, value):
    self._widget.set_active(value)
  

class EntryPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.Entry` widgets.
  
  Value: Text in the entry.
  """
  
  def _create_widget(self, setting):
    return Gtk.Entry()
  
  def _get_value(self):
    return self._widget.get_text()

  def _set_value(self, value):
    self._widget.set_text(value if value is not None else '')
    # Place the cursor at the end of the text entry.
    self._widget.set_position(-1)


class ImageComboBoxPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `GimpUi.ImageComboBox` widgets.
  
  Value: `Gimp.Image` selected in the combo box, or ``None`` if there is no
  image available.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_widget(self, setting):
    return GimpUi.ImageComboBox.new()
  
  def _get_value(self):
    return Gimp.Image.get_by_id(self._widget.get_active().value)
  
  def _set_value(self, value):
    """Sets a `Gimp.Image` instance to be selected in the combo box.
    
    Passing ``None`` has no effect.
    """
    if value is not None:
      self._widget.set_active(value.get_id())


class ItemComboBoxPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `gui.GimpItemComboBox` widgets.
  
  Value: `Gimp.Item` selected in the combo box, or ``None`` if there is no
  item available.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_widget(self, setting):
    return pggui.GimpItemComboBox()
  
  def _get_value(self):
    return Gimp.Item.get_by_id(self._widget.get_active().value)
  
  def _set_value(self, value):
    """Sets a `Gimp.Item` instance to be selected in the combo box.
    
    Passing ``None`` or a GIMP object that is not `Gimp.Item` has no effect.
    """
    if value is not None:
      self._widget.set_active(value.get_id())


class DrawableComboBoxPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `GimpUi.DrawableComboBox` widgets.
  
  Value: `Gimp.Drawable` selected in the combo box, or ``None`` if there is no
  drawable available.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_widget(self, setting):
    return GimpUi.DrawableComboBox.new()
  
  def _get_value(self):
    return Gimp.Drawable.get_by_id(self._widget.get_active().value)
  
  def _set_value(self, value):
    """Sets a `Gimp.Drawable` instance to be selected in the combo box.
    
    Passing ``None`` has no effect.
    """
    if value is not None:
      self._widget.set_active(value.get_id())


class LayerComboBoxPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `GimpUi.LayerComboBox` widgets.
  
  Value: `Gimp.Layer` selected in the combo box, or ``None`` if there is no
  layer available.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_widget(self, setting):
    return GimpUi.LayerComboBox.new()
  
  def _get_value(self):
    return Gimp.Layer.get_by_id(self._widget.get_active().value)
  
  def _set_value(self, value):
    """Sets a `Gimp.Layer` instance to be selected in the combo box.
    
    Passing ``None`` has no effect.
    """
    if value is not None:
      self._widget.set_active(value.get_id())


class ChannelComboBoxPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `GimpUi.ChannelComboBox` widgets.
  
  Value: `Gimp.Channel` selected in the combo box, or ``None`` if there is no
  channel available.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_widget(self, setting):
    return GimpUi.ChannelComboBox.new()
  
  def _get_value(self):
    return Gimp.Channel.get_by_id(self._widget.get_active().value)
  
  def _set_value(self, value):
    """Sets a `Gimp.Channel` instance to be selected in the combo box.
    
    Passing ``None`` has no effect.
    """
    if value is not None:
      self._widget.set_active(value.get_id())


class VectorsComboBoxPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `GimpUi.VectorsComboBox` widgets.
  
  Value: `Gimp.Vectors` selected in the combo box, or ``None`` if there are no
  vectors available.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_widget(self, setting):
    return GimpUi.VectorsComboBox.new()
  
  def _get_value(self):
    return Gimp.Vectors.get_by_id(self._widget.get_active().value)
  
  def _set_value(self, value):
    """Sets a `Gimp.Vectors` instance to be selected in the combo box.
    
    Passing ``None`` has no effect.
    """
    if value is not None:
      self._widget.set_active(value.get_id())


class ColorButtonPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `GimpUi.ColorButton` widgets.
  
  Value: `Gimp.RGB` instance representing color in RGBA.
  """
  
  _VALUE_CHANGED_SIGNAL = 'color-changed'
  
  def _create_widget(self, setting):
    return GimpUi.ColorButton.new(
      setting.display_name, 100, 20, setting.value, GimpUi.ColorAreaType.SMALL_CHECKS)
  
  def _get_value(self):
    return self._widget.get_color()
  
  def _set_value(self, value):
    self._widget.set_color(value)


class ParasiteBoxPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `gui.ParasiteBox` widgets.
  
  Value: `Gimp.Parasite` instance.
  """
  
  _VALUE_CHANGED_SIGNAL = 'parasite-changed'
  
  def _create_widget(self, setting):
    return pggui.ParasiteBox(setting.value)
  
  def _get_value(self):
    return self._widget.get_parasite()
  
  def _set_value(self, value):
    self._widget.set_parasite(value)


class DisplaySpinButtonPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.SpinButton` widgets.
  
  Value: `Gimp.Display` instance, represented by its integer ID in the spin
  button.
  """
  
  _VALUE_CHANGED_SIGNAL = 'value-changed'
  
  def _create_widget(self, setting):
    return Gtk.SpinButton(
      adjustment=Gtk.Adjustment(
        value=setting.value.get_id(),
        lower=0,
        upper=GLib.MAXINT,
        step_increment=1,
        page_increment=10,
      ),
      digits=0,
      numeric=True,
    )
  
  def _get_value(self):
    return Gimp.Display.get_by_id(self._widget.get_value_as_int())
  
  def _set_value(self, value):
    self._widget.set_value(value.get_id())


class ExtendedEntryPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `gui.ExtendedEntry` widgets.
  
  Value: Text in the entry.
  """
  
  def _get_value(self):
    text = self._widget.get_text()
    return text if text is not None else ''
  
  def _set_value(self, value):
    self._widget.assign_text(value if value is not None else '')


class FileExtensionEntryPresenter(ExtendedEntryPresenter):
  """`setting.Presenter` subclass for `gui.FileExtensionEntry` widgets.
  
  Value: Text in the entry.
  """
  
  def _create_widget(self, setting):
    return pggui.FileExtensionEntry()


class FolderChooserWidgetPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.FileChooserWidget` widgets used as
  folder choosers.
  
  Value: Current folder.
  """
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  def _create_widget(self, setting):
    return Gtk.FileChooserWidget(action=Gtk.FileChooserAction.SELECT_FOLDER)
  
  def _get_value(self):
    return self._widget.get_current_folder()
  
  def _set_value(self, dirpath):
    self._widget.set_current_folder(dirpath if dirpath is not None else '')


class FolderChooserButtonPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.FileChooserButton` widgets used as
  folder choosers.
  
  Value: Current folder.
  """

  def _create_widget(self, setting):
    button = Gtk.FileChooserButton(
      title=setting.display_name,
      action=Gtk.FileChooserAction.SELECT_FOLDER,
    )

    if setting.value is not None:
      button.set_filename(setting.value)

    return button
  
  def _get_value(self):
    return self._widget.get_filename()
  
  def _set_value(self, dirpath):
    self._widget.set_filename(dirpath if dirpath is not None else '')


class BrushSelectButtonPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `GimpUi.BrushSelectButton` widgets.
  
  Value: A `Gimp.Brush` instance.
  """
  
  _VALUE_CHANGED_SIGNAL = 'resource-set'
  
  def _create_widget(self, setting):
    return GimpUi.BrushSelectButton.new(setting.display_name, setting.value)
  
  def _get_value(self):
    return self._widget.get_resource()
  
  def _set_value(self, value):
    self._widget.set_resource(value)


class FontSelectButtonPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `GimpUi.FontSelectButton` widgets.
  
  Value: A `Gimp.Font` instance.
  """
  
  _VALUE_CHANGED_SIGNAL = 'resource-set'
  
  def _create_widget(self, setting):
    return GimpUi.FontSelectButton.new(setting.display_name, setting.value)
  
  def _get_value(self):
    return self._widget.get_resource()
  
  def _set_value(self, value):
    self._widget.set_resource(value)


class GradientSelectButtonPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `GimpUi.GradientSelectButton` widgets.
  
  Value: A `Gimp.Gradient` instance.
  """
  
  _VALUE_CHANGED_SIGNAL = 'resource-set'
  
  def _create_widget(self, setting):
    return GimpUi.GradientSelectButton.new(setting.display_name, setting.value)
  
  def _get_value(self):
    return self._widget.get_resource()
  
  def _set_value(self, value):
    self._widget.set_resource(value)


class PaletteSelectButtonPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `GimpUi.PaletteSelectButton` widgets.
  
  Value: A `Gimp.Palette` instance.
  """
  
  _VALUE_CHANGED_SIGNAL = 'resource-set'
  
  def _create_widget(self, setting):
    return GimpUi.PaletteSelectButton.new(setting.display_name, setting.value)
  
  def _get_value(self):
    return self._widget.get_resource()
  
  def _set_value(self, value):
    self._widget.set_resource(value)


class PatternSelectButtonPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `GimpUi.PatternSelectButton` widgets.
  
  Value: String representing a pattern.
  """
  
  _VALUE_CHANGED_SIGNAL = 'resource-set'
  
  def _create_widget(self, setting):
    return GimpUi.PatternSelectButton.new(setting.display_name, setting.value)
  
  def _get_value(self):
    return self._widget.get_resource()
  
  def _set_value(self, value):
    self._widget.set_resource(value)


class ArrayBoxPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `gui.ArrayBox` widgets.
  
  Value: Tuple of values of type ``element_type`` specified in the
  `setting.ArraySetting` instance.
  """
  
  _VALUE_CHANGED_SIGNAL = 'array-box-changed'
  _ITEM_CHANGED_SIGNAL = 'array-box-item-changed'
  
  def __init__(self, *args, **kwargs):
    self._item_changed_event_handler_id = None
    self._array_elements_with_events = set()
    
    super().__init__(*args, **kwargs)
  
  def update_setting_value(self):
    super().update_setting_value()
    
    for array_element in self._setting.get_elements():
      array_element.gui.update_setting_value()
  
  def _connect_value_changed_event(self):
    super()._connect_value_changed_event()
    
    self._item_changed_event_handler_id = self._widget.connect(
      self._ITEM_CHANGED_SIGNAL, self._on_item_changed)
  
  def _disconnect_value_changed_event(self):
    super()._disconnect_value_changed_event()
    
    self._widget.disconnect(self._item_changed_event_handler_id)
    self._item_changed_event_handler_id = None
  
  def _create_widget(self, setting):
    def _add_existing_element(array_element_value, index):
      return self._add_array_element(setting[index], array_box)
    
    def _add_new_element(array_element_value, index):
      array_element = setting.add_element(value=array_element_value)
      return self._add_array_element(array_element, array_box)
    
    def _reorder_element(orig_position, new_position):
      setting.reorder_element(orig_position, new_position)
    
    def _remove_element(position):
      self._array_elements_with_events.remove(setting[position])
      del setting[position]
    
    array_box = pggui.ArrayBox(
      setting.element_default_value, setting.min_size, setting.max_size)
    
    array_box.on_add_item = _add_existing_element
    
    for element_index in range(len(setting)):
      array_box.add_item(setting[element_index].value, element_index)
    
    array_box.on_add_item = _add_new_element
    array_box.on_reorder_item = _reorder_element
    array_box.on_remove_item = _remove_element
    
    return array_box
  
  def _get_value(self):
    return tuple(array_element.value for array_element in self._setting.get_elements())
  
  def _set_value(self, value):
    def _add_existing_element(array_element_value, index):
      return self._add_array_element(self._setting[index], self._widget)
    
    orig_on_add_item = self._widget.on_add_item
    self._widget.on_add_item = _add_existing_element
    
    self._widget.set_values(value)
    
    self._widget.on_add_item = orig_on_add_item
  
  def _on_item_changed(self, *args):
    self._setting_value_synchronizer.apply_gui_value_to_setting(self._get_value())
  
  def _add_array_element(self, array_element, array_box):
    def _on_array_box_item_changed(array_element):
      array_box.emit('array-box-item-changed')
    
    array_element.set_gui()
    
    if array_element not in self._array_elements_with_events:
      array_element.connect_event('value-changed', _on_array_box_item_changed)
      self._array_elements_with_events.add(array_element)
    
    return array_element.gui.widget


class WindowPositionPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.Window` widgets to get/set position.
  
  Value: Current position of the window as a tuple of 2 integers.
  """
  
  def _get_value(self):
    return self._widget.get_position()
  
  def _set_value(self, value):
    """Sets a new position of the window (i.e. moves the window).
    
    The window is not moved if ``value`` is ``None`` or empty.
    """
    if value:
      self._widget.move(*value)


class WindowSizePresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.Window` widgets to get/set position.
  
  Value: Current size of the window as a tuple of 2 integers.
  """
  
  def _get_value(self):
    return self._widget.get_size()
  
  def _set_value(self, value):
    """Sets a new size of the window.
    
    The window is not resized if ``value`` is ``None`` or empty.
    """
    if value:
      self._widget.resize(*value)


class PanedPositionPresenter(GtkPresenter):
  """`setting.Presenter` subclass for `Gtk.Paned` widgets.
  
  Value: Position of the divider between the two panes.
  """
  
  def _get_value(self):
    return self._widget.get_position()
  
  def _set_value(self, value):
    self._widget.set_position(value)


def _create_spin_button(setting, digits=0):
  if hasattr(setting, 'min_value') and setting.min_value is not None:
    min_value = setting.min_value
  else:
    min_value = GLib.MININT
  
  if hasattr(setting, 'max_value') and setting.max_value is not None:
    max_value = setting.max_value
  else:
    max_value = GLib.MAXINT
  
  return Gtk.SpinButton(
    adjustment=Gtk.Adjustment(
      value=setting.value,
      lower=min_value,
      upper=max_value,
      step_increment=1,
      page_increment=10,
    ),
    digits=digits,
    numeric=True,
  )


__all__ = [
  'GtkPresenter',
]

for name, class_ in inspect.getmembers(sys.modules[__name__], inspect.isclass):
  if issubclass(class_, GtkPresenter) and class_ is not GtkPresenter:
    __all__.append(name)
