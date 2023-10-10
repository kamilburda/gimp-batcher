"""Widget for placeholder GIMP objects (images, layers) such as "Current layer".

During processing, these placeholders are replaced with real objects.
"""

import gi
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi

import pygimplib as pg


class GimpObjectPlaceholdersComboBoxPresenter(pg.setting.GtkPresenter):
  """
  This class is a `setting.presenter.Presenter` subclass for
  `GimpUi.IntComboBox` elements used for `placeholders.PlaceholderSetting`.
  
  Value: `placeholders.PlaceholderSetting` instance selected in the combo box.
  """
  
  _VALUE_CHANGED_SIGNAL = 'changed'
  
  def _create_gui_element(self, setting):
    placeholder_names_and_values = []
    
    for index, placeholder in enumerate(setting.get_allowed_placeholders()):
      placeholder_names_and_values.extend(
        (pg.utils.safe_encode_gtk(placeholder.display_name), index))
    
    return gimpui.IntComboBox(tuple(placeholder_names_and_values))
  
  def _get_value(self):
    return self._setting.get_allowed_placeholder_names()[self._element.get_active()]
  
  def _set_value(self, value):
    self._element.set_active(self._setting.get_allowed_placeholder_names().index(value))
