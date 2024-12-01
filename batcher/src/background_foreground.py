"""Background and foreground layer insertion and manipulation."""

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp

from src import exceptions

import pygimplib as pg


def insert_background_layer(batcher, tag, item_tree_for_preview, *_args, **_kwargs):
  return _insert_tagged_layer(batcher, tag, item_tree_for_preview, 'after')


def insert_foreground_layer(batcher, tag, item_tree_for_preview, *_args, **_kwargs):
  return _insert_tagged_layer(batcher, tag, item_tree_for_preview, 'before')


def _insert_tagged_layer(batcher, tag, tagged_items_for_preview, insert_mode):
  if batcher.is_preview:
    tagged_items = tagged_items_for_preview
  else:
    tagged_items = batcher.item_tree.iter(with_folders=False, filtered=False)

  processed_tagged_items = [
    item for item in tagged_items
    if tag != Gimp.ColorTag.NONE and item.raw.is_valid() and item.raw.get_color_tag() == tag]
  
  while True:
    if not processed_tagged_items:
      yield
      continue

    image = batcher.current_raw_item.get_image()
    current_parent = batcher.current_raw_item.get_parent()

    position = image.get_item_position(batcher.current_raw_item)
    if insert_mode == 'after':
      position += 1

    _insert_merged_tagged_layer(batcher, image, processed_tagged_items, current_parent, position)

    yield


def _insert_merged_tagged_layer(batcher, image, tagged_items, parent, position):
  first_tagged_layer_position = position
  
  for i, item in enumerate(tagged_items):
    layer_copy = pg.pdbutils.copy_and_paste_layer(
      item.raw, image, parent, first_tagged_layer_position + i, True, True, True)
    layer_copy.set_visible(True)

  if parent is None:
    children = image.get_layers()
  else:
    children = parent.get_children()

  merged_tagged_layer = None

  if len(tagged_items) == 1:
    merged_tagged_layer = children[first_tagged_layer_position]
  else:
    second_to_last_tagged_layer_position = first_tagged_layer_position + len(tagged_items) - 2
    # It should not matter which items we obtain the color tag from as all
    # items have the same color tag.
    merged_color_tag = children[second_to_last_tagged_layer_position].get_color_tag()
    
    for i in range(second_to_last_tagged_layer_position, first_tagged_layer_position - 1, -1):
      merged_tagged_layer = image.merge_down(children[i], Gimp.MergeType.EXPAND_AS_NECESSARY)

    # The merged-down layer does not possess the attributes of the original
    # layers, including the color tag, so we set it explicitly. This ensures
    # that tagged group layers are merged properly in "Merge back-/foreground"
    # procedures.
    merged_tagged_layer.set_color_tag(merged_color_tag)

  return merged_tagged_layer


def merge_background(batcher, merge_type=Gimp.MergeType.EXPAND_AS_NECESSARY, *_args, **_kwargs):
  _merge_tagged_layer(
    batcher,
    merge_type,
    get_background_layer,
    'current_item')


def merge_foreground(batcher, merge_type=Gimp.MergeType.EXPAND_AS_NECESSARY, *_args, **_kwargs):
  _merge_tagged_layer(
    batcher,
    merge_type,
    get_foreground_layer,
    'tagged_layer')


def _merge_tagged_layer(batcher, merge_type, get_tagged_layer_func, layer_to_merge_down_str):
  tagged_layer = get_tagged_layer_func(batcher)
  
  if tagged_layer is not None:
    name = batcher.current_raw_item.get_name()
    visible = batcher.current_raw_item.get_visible()
    orig_color_tag = batcher.current_raw_item.get_color_tag()
    
    if layer_to_merge_down_str == 'current_item':
      layer_to_merge_down = batcher.current_raw_item
    elif layer_to_merge_down_str == 'tagged_layer':
      layer_to_merge_down = tagged_layer
    else:
      raise ValueError('invalid value for "layer_to_merge_down_str"')
    
    batcher.current_raw_item.set_visible(True)
    
    merged_layer = batcher.current_raw_item.get_image().merge_down(layer_to_merge_down, merge_type)

    # Avoid errors if merge failed for some reason.
    if merged_layer is not None:
      merged_layer.set_name(name)

      batcher.current_raw_item = merged_layer
    
      batcher.current_raw_item.set_visible(visible)
      batcher.current_raw_item.set_color_tag(orig_color_tag)


def get_background_layer(batcher):
  return _get_adjacent_layer(
    batcher,
    lambda position, num_layers: position < num_layers - 1,
    1,
    'insert_background',
    _('There are no background layers.'))


def get_foreground_layer(batcher):
  return _get_adjacent_layer(
    batcher,
    lambda position, num_layers: position > 0,
    -1,
    'insert_foreground',
    _('There are no foreground layers.'))


def _get_adjacent_layer(
      batcher,
      position_cond_func,
      adjacent_position_increment,
      insert_tagged_layers_procedure_name,
      skip_message,
):
  image = batcher.current_raw_item.get_image()
  raw_item = batcher.current_raw_item

  if raw_item.get_parent() is None:
    children = image.get_layers()
  else:
    children = raw_item.get_parent().get_children()
  
  adjacent_layer = None
  
  num_layers = len(children)
  
  if num_layers > 1:
    position = image.get_item_position(raw_item)
    if position_cond_func(position, num_layers):
      next_layer = children[position + adjacent_position_increment]
      color_tags = [
        procedure['arguments/color_tag'].value
        for procedure in _get_previous_enabled_procedures(
          batcher, batcher.current_procedure, insert_tagged_layers_procedure_name)]
      
      if next_layer.get_color_tag() in color_tags:
        adjacent_layer = next_layer
  
  if adjacent_layer is not None:
    # This is necessary for some procedures relying on selected layers, e.g.
    # `plug-in-autocrop-layer`.
    image.set_selected_layers([adjacent_layer])
    return adjacent_layer
  else:
    raise exceptions.SkipAction(skip_message)


def _get_previous_enabled_procedures(batcher, current_action, action_orig_name_to_match):
  previous_enabled_procedures = []
  
  for procedure in batcher.procedures:
    if procedure == current_action:
      return previous_enabled_procedures
    
    if procedure['enabled'].value and procedure['orig_name'].value == action_orig_name_to_match:
      previous_enabled_procedures.append(procedure)
  
  return previous_enabled_procedures
