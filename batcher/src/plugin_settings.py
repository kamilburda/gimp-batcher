"""Plug-in settings."""

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp

import pygimplib as pg

from src import actions as actions_
from src import builtin_constraints
from src import builtin_procedures
from src import export as export_
# Despite being unused, `setting_classes` must be imported so that the
# setting and GUI classes defined there are properly registered (via respective
# metaclasses in `pg.setting.meta`).
# noinspection PyUnresolvedReferences
from src import setting_classes
from src import utils


def create_settings_for_convert():
  settings = pg.setting.create_groups({
    'name': 'all_settings',
    'groups': [
      {
        'name': 'main',
      }
    ]
  })

  settings['main'].add([
    {
      'type': 'enum',
      'name': 'run_mode',
      'enum_type': Gimp.RunMode,
      'default_value': Gimp.RunMode.NONINTERACTIVE,
      'display_name': _('Run mode'),
      'description': _('The run mode'),
      'gui_type': None,
      'tags': ['ignore_reset', 'ignore_load', 'ignore_save'],
    },
    {
      'type': 'array',
      'name': 'inputs',
      'element_type': 'string',
      'default_value': (),
      'display_name': _('Input files and folders (non-interactive run mode only)'),
      'tags': ['ignore_reset', 'ignore_load', 'ignore_save'],
    },
    {
      'type': 'file_extension',
      'name': 'file_extension',
      'default_value': 'png',
      'display_name': _('File extension'),
      'adjust_value': True,
      'auto_update_gui_to_setting': False,
      'gui_type': None,
    },
    {
      'type': 'dirpath',
      'name': 'output_directory',
      'default_value': pg.utils.get_pictures_directory(),
      'display_name': _('Output folder'),
      'gui_type': 'folder_chooser_button',
    },
    {
      'type': 'name_pattern',
      'name': 'name_pattern',
      'default_value': '[image name]',
      'display_name': _('Image filename pattern'),
      'description': _('Image filename pattern (empty string = image name)'),
      'gui_type': None,
    },
    {
      'type': 'choice',
      'name': 'overwrite_mode',
      'default_value': 'rename_new',
      'items': utils.semi_deep_copy(builtin_procedures.INTERACTIVE_OVERWRITE_MODES_LIST),
      'display_name': _('How to handle conflicting files (non-interactive run mode only)'),
      'gui_type': None,
    },
    {
      'type': 'file',
      'name': 'settings_file',
      'default_value': None,
      'display_name': _('File with saved settings'),
      'description': _('File with saved settings (optional)'),
      'gui_type': None,
      'tags': ['ignore_reset', 'ignore_load', 'ignore_save'],
    },
    {
      'type': 'image_file_tree_items',
      'name': 'selected_items',
      'display_name': _('Selected files and folders'),
      'pdb_type': None,
      'gui_type': None,
    },
    {
      'type': 'string',
      'name': 'plugin_version',
      'default_value': pg.config.PLUGIN_VERSION,
      'pdb_type': None,
      'gui_type': None,
    },
  ])

  gui_settings = _create_gui_settings('image_file_tree_items')
  gui_settings.add([_create_auto_close_setting_dict(False)])

  size_gui_settings = pg.setting.Group(name='size')

  size_gui_settings.add([
    {
      'type': 'tuple',
      'name': 'dialog_position',
      'default_value': (),
    },
    {
      'type': 'tuple',
      'name': 'dialog_size',
      'default_value': (570, 500),
    },
    {
      'type': 'integer',
      'name': 'paned_outside_previews_position',
      'default_value': 300,
      'gui_type': None,
    },
    {
      'type': 'integer',
      'name': 'paned_between_previews_position',
      'default_value': 220,
      'gui_type': None,
    },
  ])

  gui_settings.add([size_gui_settings])

  settings.add([gui_settings])

  settings['main'].add([
    actions_.create(
      name='procedures'),
  ])

  settings['main'].add([
    actions_.create(
      name='constraints'),
  ])

  return settings


def create_settings_for_export_layers():
  settings = pg.setting.create_groups({
    'name': 'all_settings',
    'groups': [
      {
        'name': 'main',
      }
    ]
  })
  
  settings['main'].add([
    {
      'type': 'file_extension',
      'name': 'file_extension',
      'default_value': 'png',
      'display_name': _('File extension'),
      'adjust_value': True,
      'auto_update_gui_to_setting': False,
      'gui_type': None,
    },
    {
      'type': 'dirpath',
      'name': 'output_directory',
      'default_value': pg.utils.get_pictures_directory(),
      'display_name': _('Output folder'),
      'gui_type': 'folder_chooser_button',
    },
    {
      'type': 'name_pattern',
      'name': 'name_pattern',
      'default_value': '[layer name]',
      'display_name': _('Layer filename pattern'),
      'description': _('Layer filename pattern (empty string = layer name)'),
      'gui_type': None,
    },
    {
      'type': 'choice',
      'name': 'overwrite_mode',
      'default_value': 'rename_new',
      'items': utils.semi_deep_copy(builtin_procedures.INTERACTIVE_OVERWRITE_MODES_LIST),
      'display_name': _('How to handle conflicting files (non-interactive run mode only)'),
      'gui_type': None,
    },
    {
      'type': 'file',
      'name': 'settings_file',
      'default_value': None,
      'display_name': _('File with saved settings'),
      'description': _('File with saved settings (optional)'),
      'gui_type': None,
      'tags': ['ignore_reset', 'ignore_load', 'ignore_save'],
    },
    {
      'type': 'gimp_item_tree_items',
      'name': 'selected_items',
      'display_name': _('Selected layers'),
      'pdb_type': None,
      'gui_type': None,
    },
    {
      'type': 'tagged_items',
      'name': 'tagged_items',
      'default_value': [],
      'pdb_type': None,
      'gui_type': None,
      'tags': ['ignore_reset', 'ignore_load', 'ignore_save'],
    },
    {
      'type': 'string',
      'name': 'plugin_version',
      'default_value': pg.config.PLUGIN_VERSION,
      'pdb_type': None,
      'gui_type': None,
    },
  ])

  export_settings = pg.setting.Group(
    name='export',
    setting_attributes={
      'pdb_type': None,
    },
  )

  export_arguments = utils.semi_deep_copy(
    builtin_procedures.BUILTIN_PROCEDURES['export_for_export_layers']['arguments'])
  # Remove settings already present in the main settings.
  export_arguments = export_arguments[2:]

  export_settings.add(export_arguments)

  settings['main'].add([export_settings])

  gui_settings = _create_gui_settings('gimp_item_tree_items')
  gui_settings.add([
    _create_auto_close_setting_dict(True),
    _create_show_quick_settings_setting_dict(),
    _create_images_and_directories_setting_dict(),
  ])

  size_gui_settings = pg.setting.Group(name='size')

  size_gui_settings.add([
    {
      'type': 'tuple',
      'name': 'dialog_position',
      'default_value': (),
    },
    {
      'type': 'tuple',
      'name': 'dialog_size',
      'default_value': (640, 540),
    },
    {
      'type': 'integer',
      'name': 'paned_outside_previews_position',
      'default_value': 330,
      'gui_type': None,
    },
    {
      'type': 'integer',
      'name': 'paned_between_previews_position',
      'default_value': 225,
      'gui_type': None,
    },
  ])

  gui_settings.add([size_gui_settings])

  settings.add([gui_settings])

  settings['main'].add([
    actions_.create(
      name='procedures',
      initial_actions=[builtin_procedures.BUILTIN_PROCEDURES['use_layer_size']]),
  ])

  visible_constraint_dict = utils.semi_deep_copy(builtin_constraints.BUILTIN_CONSTRAINTS['visible'])
  visible_constraint_dict['enabled'] = False
  
  settings['main'].add([
    actions_.create(
      name='constraints',
      initial_actions=[
        builtin_constraints.BUILTIN_CONSTRAINTS['layers'],
        visible_constraint_dict]),
  ])

  _set_sensitive_for_image_name_pattern_in_export_for_default_export_procedure(settings['main'])

  _set_file_extension_options_for_default_export_procedure(settings['main'])

  settings['main/procedures'].connect_event('after-add-action', _on_after_add_export_procedure)
  settings['main/procedures'].connect_event('after-add-action', _on_after_add_scale_procedure)

  settings['main/procedures'].connect_event(
    'after-add-action',
    _on_after_add_insert_background_foreground,
    settings['main/tagged_items'],
  )
  
  return settings


def create_settings_for_edit_layers():
  settings = pg.setting.create_groups({
    'name': 'all_settings',
    'groups': [
      {
        'name': 'main',
      }
    ]
  })

  settings['main'].add([
    {
      'type': 'file',
      'name': 'settings_file',
      'default_value': None,
      'display_name': _('File with saved settings'),
      'description': _('File with saved settings (optional)'),
      'gui_type': None,
      'tags': ['ignore_reset', 'ignore_load', 'ignore_save'],
    },
    {
      'type': 'gimp_item_tree_items',
      'name': 'selected_items',
      'display_name': _('Selected layers'),
      'pdb_type': None,
      'gui_type': None,
    },
    {
      'type': 'tagged_items',
      'name': 'tagged_items',
      'default_value': [],
      'pdb_type': None,
      'gui_type': None,
      'tags': ['ignore_reset', 'ignore_load', 'ignore_save'],
    },
    {
      'type': 'string',
      'name': 'plugin_version',
      'default_value': pg.config.PLUGIN_VERSION,
      'pdb_type': None,
      'gui_type': None,
    },
  ])

  gui_settings = _create_gui_settings('gimp_item_tree_items')
  gui_settings.add([_create_auto_close_setting_dict(False)])

  size_gui_settings = pg.setting.Group(name='size')

  size_gui_settings.add([
    {
      'type': 'tuple',
      'name': 'dialog_position',
      'default_value': (),
    },
    {
      'type': 'tuple',
      'name': 'dialog_size',
      'default_value': (570, 500),
    },
    {
      'type': 'integer',
      'name': 'paned_outside_previews_position',
      'default_value': 300,
      'gui_type': None,
    },
    {
      'type': 'integer',
      'name': 'paned_between_previews_position',
      'default_value': 220,
      'gui_type': None,
    },
  ])

  gui_settings.add([size_gui_settings])

  settings.add([gui_settings])

  rename_procedure_dict = utils.semi_deep_copy(
    builtin_procedures.BUILTIN_PROCEDURES['rename_for_edit_layers'])
  rename_procedure_dict['enabled'] = False
  rename_procedure_dict['display_options_on_create'] = False
  rename_procedure_dict['arguments'][0]['default_value'] = 'image[001]'

  settings['main'].add([
    actions_.create(
      name='procedures',
      initial_actions=[rename_procedure_dict]),
  ])

  visible_constraint_dict = utils.semi_deep_copy(builtin_constraints.BUILTIN_CONSTRAINTS['visible'])
  visible_constraint_dict['enabled'] = False

  settings['main'].add([
    actions_.create(
      name='constraints',
      initial_actions=[
        builtin_constraints.BUILTIN_CONSTRAINTS['layers'],
        visible_constraint_dict]),
  ])

  settings['main/procedures'].connect_event('after-add-action', _on_after_add_export_procedure)
  settings['main/procedures'].connect_event('after-add-action', _on_after_add_scale_procedure)

  settings['main/procedures'].connect_event(
    'after-add-action',
    _on_after_add_insert_background_foreground,
    settings['main/tagged_items'],
  )

  return settings


def _create_gui_settings(item_tree_items_setting_type):
  gui_settings = pg.setting.Group(name='gui')

  procedure_browser_settings = pg.setting.Group(name='procedure_browser')

  procedure_browser_settings.add([
    {
      'type': 'integer',
      'name': 'paned_position',
      'default_value': 325,
      'gui_type': None,
    },
    {
      'type': 'tuple',
      'name': 'dialog_position',
      'default_value': (),
    },
    {
      'type': 'tuple',
      'name': 'dialog_size',
      'default_value': (800, 450),
    },
  ])

  gui_settings.add([
    {
      'type': 'bool',
      'name': 'name_preview_sensitive',
      'default_value': True,
      'gui_type': None,
    },
    {
      'type': 'bool',
      'name': 'image_preview_sensitive',
      'default_value': True,
      'gui_type': None,
    },
    {
      'type': 'bool',
      'name': 'image_preview_automatic_update',
      'default_value': True,
      'gui_type': None,
    },
    {
      'type': 'bool',
      'name': 'image_preview_automatic_update_if_below_maximum_duration',
      'default_value': True,
      'gui_type': None,
    },
    {
      'type': item_tree_items_setting_type,
      'name': 'name_preview_items_collapsed_state',
    },
    {
      'type': item_tree_items_setting_type,
      'name': 'image_preview_displayed_items',
    },
    procedure_browser_settings,
  ])

  return gui_settings


def _create_auto_close_setting_dict(default_value):
  return {
    'type': 'bool',
    'name': 'auto_close',
    'default_value': default_value,
    'display_name': _('Close when Done'),
    'gui_type': 'check_menu_item',
  }


def _create_show_quick_settings_setting_dict():
  return {
    'type': 'bool',
    'name': 'show_quick_settings',
    'default_value': True,
    'gui_type': None,
  }


def _create_images_and_directories_setting_dict():
  return {
    'type': 'images_and_directories',
    'name': 'images_and_directories',
  }


def _set_sensitive_for_image_name_pattern_in_export_for_default_export_procedure(main_settings):
  _set_sensitive_for_image_name_pattern_in_export(
    main_settings['export/export_mode'],
    main_settings['export/single_image_name_pattern'])

  main_settings['export/export_mode'].connect_event(
    'value-changed',
    _set_sensitive_for_image_name_pattern_in_export,
    main_settings['export/single_image_name_pattern'])


def _set_file_extension_options_for_default_export_procedure(main_settings):
  _show_hide_file_format_export_options(
    main_settings['export/file_format_mode'],
    main_settings['export/file_format_export_options'])

  main_settings['export/file_format_mode'].connect_event(
    'value-changed',
    _show_hide_file_format_export_options,
    main_settings['export/file_format_export_options'])

  pg.notifier.connect(
    'start-procedure',
    lambda _notifier: _set_file_format_export_options(
      main_settings['file_extension'],
      main_settings['export/file_format_export_options']))

  main_settings['file_extension'].connect_event(
    'value-changed',
    _set_file_format_export_options,
    main_settings['export/file_format_export_options'])

  # This is needed in case settings are reset, since the file extension is
  # reset first and the options, after resetting, would contain values for
  # the default file extension, which could be different.
  main_settings['export/file_format_export_options'].connect_event(
    'after-reset',
    _set_file_format_export_options_from_extension,
    main_settings['file_extension'])


def _on_after_add_export_procedure(_procedures, procedure, _orig_procedure_dict):
  if procedure['orig_name'].value.startswith('export_for_'):
    _set_sensitive_for_image_name_pattern_in_export(
      procedure['arguments/export_mode'],
      procedure['arguments/single_image_name_pattern'])
    
    procedure['arguments/export_mode'].connect_event(
      'value-changed',
      _set_sensitive_for_image_name_pattern_in_export,
      procedure['arguments/single_image_name_pattern'])

    _show_hide_file_format_export_options(
      procedure['arguments/file_format_mode'],
      procedure['arguments/file_format_export_options'])

    procedure['arguments/file_format_mode'].connect_event(
      'value-changed',
      _show_hide_file_format_export_options,
      procedure['arguments/file_format_export_options'])

    _set_file_format_export_options(
      procedure['arguments/file_extension'],
      procedure['arguments/file_format_export_options'])

    procedure['arguments/file_extension'].connect_event(
      'value-changed',
      _set_file_format_export_options,
      procedure['arguments/file_format_export_options'])

    # This is needed in case settings are reset, since the file extension is
    # reset first and the options, after resetting, would contain values for
    # the default file extension, which could be different.
    procedure['arguments/file_format_export_options'].connect_event(
      'after-reset',
      _set_file_format_export_options_from_extension,
      procedure['arguments/file_extension'])


def _set_sensitive_for_image_name_pattern_in_export(
      export_mode_setting, single_image_name_pattern_setting):
  if export_mode_setting.value == export_.ExportModes.SINGLE_IMAGE:
    single_image_name_pattern_setting.gui.set_sensitive(True)
  else:
    single_image_name_pattern_setting.gui.set_sensitive(False)


def _set_file_format_export_options(file_extension_setting, file_format_export_options_setting):
  file_format_export_options_setting.set_active_file_format(file_extension_setting.value)


def _set_file_format_export_options_from_extension(
      file_format_export_options_setting, file_extension_setting):
  file_format_export_options_setting.set_active_file_format(file_extension_setting.value)


def _show_hide_file_format_export_options(
      file_format_mode_setting, file_format_export_options_setting):
  file_format_export_options_setting.gui.set_visible(
    file_format_mode_setting.value == 'use_explicit_values')


def _on_after_add_scale_procedure(_procedures, procedure, _orig_procedure_dict):
  if procedure['orig_name'].value == 'scale':
    _set_sensitive_for_keep_aspect_ratio(
      procedure['arguments/scale_to_fit'],
      procedure['arguments/keep_aspect_ratio'],
    )

    procedure['arguments/scale_to_fit'].connect_event(
      'value-changed',
      _set_sensitive_for_keep_aspect_ratio,
      procedure['arguments/keep_aspect_ratio'])

    _set_sensitive_for_scale_to_fit_and_dimension_to_ignore(
      procedure['arguments/keep_aspect_ratio'],
      procedure['arguments/scale_to_fit'],
      procedure['arguments/dimension_to_keep'],
    )

    procedure['arguments/keep_aspect_ratio'].connect_event(
      'value-changed',
      _set_sensitive_for_scale_to_fit_and_dimension_to_ignore,
      procedure['arguments/scale_to_fit'],
      procedure['arguments/dimension_to_keep'])

    _set_sensitive_for_dimension_to_ignore(
      procedure['arguments/dimension_to_keep'],
      procedure['arguments/new_width'],
      procedure['arguments/width_unit'],
      procedure['arguments/new_height'],
      procedure['arguments/height_unit'])

    procedure['arguments/dimension_to_keep'].connect_event(
      'value-changed',
      _set_sensitive_for_dimension_to_ignore,
      procedure['arguments/new_width'],
      procedure['arguments/width_unit'],
      procedure['arguments/new_height'],
      procedure['arguments/height_unit'])

    procedure['arguments/dimension_to_keep'].connect_event(
      'gui-sensitive-changed',
      _set_sensitive_for_dimension_to_ignore,
      procedure['arguments/new_width'],
      procedure['arguments/width_unit'],
      procedure['arguments/new_height'],
      procedure['arguments/height_unit'])


def _set_sensitive_for_keep_aspect_ratio(scale_to_fit_setting, keep_aspect_ratio_setting):
  keep_aspect_ratio_setting.gui.set_sensitive(not scale_to_fit_setting.value)


def _set_sensitive_for_scale_to_fit_and_dimension_to_ignore(
      keep_aspect_ratio_setting, scale_to_fit_setting, dimension_to_keep_setting):
  scale_to_fit_setting.gui.set_sensitive(not keep_aspect_ratio_setting.value)
  dimension_to_keep_setting.gui.set_sensitive(keep_aspect_ratio_setting.value)


def _set_sensitive_for_dimension_to_ignore(
      dimension_to_keep_setting,
      new_width_setting,
      width_unit_setting,
      new_height_setting,
      height_unit_setting,
):
  is_sensitive = dimension_to_keep_setting.gui.get_sensitive()
  is_width = dimension_to_keep_setting.value == builtin_procedures.WIDTH
  is_height = dimension_to_keep_setting.value == builtin_procedures.HEIGHT

  new_width_setting.gui.set_sensitive(is_width or not is_sensitive)
  width_unit_setting.gui.set_sensitive(is_width or not is_sensitive)
  new_height_setting.gui.set_sensitive(is_height or not is_sensitive)
  height_unit_setting.gui.set_sensitive(is_height or not is_sensitive)


def _on_after_add_insert_background_foreground(
      _procedures,
      procedure,
      _orig_procedure_dict,
      tagged_items_setting,
):
  if procedure['orig_name'].value in ['insert_background', 'insert_foreground']:
    procedure['arguments/tagged_items'].gui.set_visible(False)
    _sync_tagged_items_with_procedure(tagged_items_setting, procedure)


def _sync_tagged_items_with_procedure(tagged_items_setting, procedure):

  def _on_tagged_items_changed(tagged_items_setting_, procedure_):
    procedure_['arguments/tagged_items'].set_value(tagged_items_setting_.value)

  _on_tagged_items_changed(tagged_items_setting, procedure)

  tagged_items_setting.connect_event('value-changed', _on_tagged_items_changed, procedure)
