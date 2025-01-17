"""Built-in plug-in constraints."""

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp

import pygimplib as pg

from src.path import fileext
from src.procedure_groups import *


def is_layer(item, _layer_batcher):
  return item.type == pg.itemtree.TYPE_ITEM


def is_nonempty_group(item, _layer_batcher):
  return item.type == pg.itemtree.TYPE_GROUP and item.raw.get_children()


def has_matching_file_extension(item, _batcher, file_extension):
  return fileext.get_file_extension(item.name).lower() == file_extension.lower()


def has_matching_default_file_extension(item, layer_batcher):
  return fileext.get_file_extension(item.name).lower() == layer_batcher.file_extension.lower()


def is_item_in_items_selected_in_gimp(item, _layer_batcher):
  image = item.raw.get_image()
  return image.is_valid() and item.raw in image.get_selected_layers()


def is_top_level(item, _batcher):
  return item.depth == 0


def is_visible(item, _layer_batcher):
  return item.raw.get_visible()


def has_color_tag(item, _layer_batcher, color_tag, *_args, **_kwargs):
  return item.raw.get_color_tag() == color_tag


def has_color_tags(item, _layer_batcher, color_tags=None):
  item_color_tag = item.raw.get_color_tag()

  if item_color_tag == Gimp.ColorTag.NONE:
    return False
  else:
    if color_tags:
      return any(item_color_tag == tag for tag in color_tags)
    else:
      return item_color_tag != Gimp.ColorTag.NONE


def has_no_color_tag(item, _layer_batcher, color_tag, *_args, **_kwargs):
  return not has_color_tag(item, _layer_batcher, color_tag)


def has_no_color_tags(item, _layer_batcher, color_tags=None):
  return not has_color_tags(item, _layer_batcher, color_tags)


_BUILTIN_CONSTRAINTS_LIST = [
  {
    'name': 'layers',
    'type': 'constraint',
    'function': is_layer,
    'display_name': _('Layers'),
    'additional_tags': [EDIT_LAYERS_GROUP, EXPORT_LAYERS_GROUP],
  },
  {
    'name': 'group_layers',
    'type': 'constraint',
    'function': is_nonempty_group,
    'display_name': _('Group layers'),
    'additional_tags': [EDIT_LAYERS_GROUP, EXPORT_LAYERS_GROUP],
  },
  {
    'name': 'not_background',
    'type': 'constraint',
    'function': has_no_color_tag,
    # FOR TRANSLATORS: Think of "Only items that are not background" when translating this
    'display_name': _('Not background'),
    # This constraint is added/removed automatically alongside `insert_background`.
    'additional_tags': [],
    'arguments': [
      {
        'type': 'enum',
        'name': 'color_tag',
        'enum_type': Gimp.ColorTag,
        'excluded_values': [Gimp.ColorTag.NONE],
        'default_value': Gimp.ColorTag.BLUE,
        'gui_type': None,
      },
      {
        'type': 'bool',
        'name': 'last_enabled_value',
        'default_value': True,
        'gui_type': None,
      },
    ],
  },
  {
    'name': 'not_foreground',
    'type': 'constraint',
    'function': has_no_color_tag,
    # FOR TRANSLATORS: Think of "Only items that are not foreground" when translating this
    'display_name': _('Not foreground'),
    # This constraint is added/removed automatically alongside `insert_foreground`.
    'additional_tags': [],
    'arguments': [
      {
        'type': 'enum',
        'name': 'color_tag',
        'enum_type': Gimp.ColorTag,
        'excluded_values': [Gimp.ColorTag.NONE],
        'default_value': Gimp.ColorTag.GREEN,
        'gui_type': None,
      },
      {
        'type': 'bool',
        'name': 'last_enabled_value',
        'default_value': True,
        'gui_type': None,
      },
    ],
  },
  {
    'name': 'matching_file_extension',
    'type': 'constraint',
    'function': has_matching_default_file_extension,
    # FOR TRANSLATORS: Think of "Only items matching file extension" when translating this
    'display_name': _('Matching file extension'),
    'additional_tags': [EDIT_LAYERS_GROUP, EXPORT_LAYERS_GROUP],
  },
  {
    'name': 'selected_in_gimp',
    'type': 'constraint',
    'function': is_item_in_items_selected_in_gimp,
    # FOR TRANSLATORS: Think of "Only items selected in GIMP" when translating this
    'display_name': _('Selected in GIMP'),
    'additional_tags': [EDIT_LAYERS_GROUP, EXPORT_LAYERS_GROUP],
  },
  {
    'name': 'top_level',
    'type': 'constraint',
    'function': is_top_level,
    # FOR TRANSLATORS: Think of "Only top-level items" when translating this
    'display_name': _('Top-level'),
    'additional_tags': [EDIT_LAYERS_GROUP, EXPORT_LAYERS_GROUP],
  },
  {
    'name': 'visible',
    'type': 'constraint',
    'function': is_visible,
    # FOR TRANSLATORS: Think of "Only visible items" when translating this
    'display_name': _('Visible'),
    'additional_tags': [EDIT_LAYERS_GROUP, EXPORT_LAYERS_GROUP],
  },
  {
    'name': 'with_color_tags',
    'type': 'constraint',
    'function': has_color_tags,
    # FOR TRANSLATORS: Think of "Only items with color tags" when translating this
    'display_name': _('With color tags'),
    'additional_tags': [EDIT_LAYERS_GROUP, EXPORT_LAYERS_GROUP],
    'arguments': [
      {
        'type': 'array',
        'name': 'color_tags',
        'display_name': _('Color tags'),
        'element_type': 'enum',
        'element_enum_type': Gimp.ColorTag,
        'element_excluded_values': [Gimp.ColorTag.NONE],
        'element_default_value': Gimp.ColorTag.BLUE,
        'default_value': (),
      },
    ],
  },
  {
    'name': 'without_color_tags',
    'type': 'constraint',
    'function': has_no_color_tags,
    # FOR TRANSLATORS: Think of "Only items without color tags" when translating this
    'display_name': _('Without color tags'),
    'additional_tags': [EDIT_LAYERS_GROUP, EXPORT_LAYERS_GROUP],
    'arguments': [
      {
        'type': 'array',
        'name': 'color_tags',
        'display_name': _('Color tags'),
        'element_type': 'enum',
        'element_enum_type': Gimp.ColorTag,
        'element_excluded_values': [Gimp.ColorTag.NONE],
        'element_default_value': Gimp.ColorTag.BLUE,
        'default_value': (),
      },
    ],
  },
]

# Translated display names could be displayed out of alphabetical order,
# hence the sorting.
_BUILTIN_CONSTRAINTS_LIST.sort(
  key=lambda item: item.get('menu_path', item.get('display_name', item['name'])))

# Create a separate dictionary for functions since objects cannot be saved
# to a persistent source. Saving them as strings would not be reliable as
# function names and paths may change when refactoring or adding/modifying features.
# The 'function' setting is set to an empty value as the function can be inferred
# via the action's 'orig_name' setting.
BUILTIN_CONSTRAINTS = {}
BUILTIN_CONSTRAINTS_FUNCTIONS = {}

for action_dict in _BUILTIN_CONSTRAINTS_LIST:
  function = action_dict['function']
  action_dict['function'] = ''
  
  BUILTIN_CONSTRAINTS[action_dict['name']] = action_dict
  BUILTIN_CONSTRAINTS_FUNCTIONS[action_dict['name']] = function
