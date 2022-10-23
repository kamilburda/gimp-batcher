# -*- coding: utf-8 -*-

"""Plug-in core - exporting layers as separate images."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *
import future.utils

import collections
import inspect
import os

from gimp import pdb
import gimpenums

from export_layers import pygimplib as pg

from export_layers import builtin_procedures
from export_layers import builtin_constraints
from export_layers import actions
from export_layers import placeholders
from export_layers import renamer


class LayerExporter(object):
  """
  This class exports layers as separate images, with the support for additional
  actions applied on layers (resize, rename, ...).
  
  Attributes:
  
  * `initial_run_mode` - The run mode to use for the first layer exported.
    For subsequent layers, `gimpenums.RUN_WITH_LAST_VALS` is used. If the file
    format in which the layer is exported to cannot handle
    `gimpenums.RUN_WITH_LAST_VALS`, `gimpenums.RUN_INTERACTIVE` is used.
  
  * `image` - GIMP image to export layers from.
  
  * `export_settings` - `setting.Group` instance containing export settings.
    This class treats them as read-only.
  
  * `overwrite_chooser` - `OverwriteChooser` instance that is invoked if a file
    with the same name already exists. If `None` is passed during
    initialization, `pygimplib.overwrite.NoninteractiveOverwriteChooser` is used
    by default.
  
  * `progress_updater` - `ProgressUpdater` instance that indicates the number of
    layers exported. If no progress update is desired, pass `None`.
  
  * `layer_tree` - `LayerTree` instance containing layers to be exported.
    Defaults to `None` if no export has been performed yet.
  
  * `exported_layers` - List of layers that were successfully exported. Does not
    include skipped layers (when files with the same names already exist).
  
  * `export_context_manager` - Context manager that wraps exporting a single
    layer. This can be used to perform GUI updates before and after export.
    Required parameters: current run mode, current image, layer to export,
    output filename of the layer.
  
  * `export_context_manager_args` - Additional arguments passed to
    `export_context_manager`.
  
  * `current_layer_elem` (read-only) - The `itemtree._ItemTreeElement` instance
    being currently exported.
  
  * `invoker` - `pygimplib.invoker.Invoker` instance to
    manage procedures and constraints applied on layers. This property is not
    `None` only during `export()`.
  """
  
  def __init__(
        self,
        initial_run_mode,
        image,
        export_settings,
        overwrite_chooser=None,
        progress_updater=None,
        layer_tree=None,
        export_context_manager=None,
        export_context_manager_args=None):
    
    self.initial_run_mode = initial_run_mode
    self.image = image
    self.export_settings = export_settings
    
    self.overwrite_chooser = (
      overwrite_chooser if overwrite_chooser is not None
      else pg.overwrite.NoninteractiveOverwriteChooser(
        self.export_settings['overwrite_mode'].value))
    
    self.progress_updater = (
      progress_updater if progress_updater is not None
      else pg.progress.ProgressUpdater(None))
    
    self._layer_tree = layer_tree
    
    self.export_context_manager = (
      export_context_manager if export_context_manager is not None
      else pg.utils.EmptyContext)
    
    self.export_context_manager_args = (
      export_context_manager_args if export_context_manager_args is not None else [])
    
    self._default_file_extension = None
    self._file_extension_properties = None
    
    self.current_file_extension = None
    
    self._exported_layers = []
    self._exported_layers_ids = set()
    self._current_layer_elem = None
    
    self._should_stop = False
    
    self._processing_groups = {
      'layer_contents': [
        self._setup, self._cleanup, self._process_layer, self._postprocess_layer],
      'layer_name': [
        self._preprocess_layer_name, self._preprocess_empty_group_name,
        self._process_layer_name],
      '_postprocess_layer_name': [self._postprocess_layer_name],
      'export': [self._make_dirs, self._export],
      'layer_name_for_preview': [self._process_layer_name_for_preview],
    }
    self._default_processing_groups = [
      'layer_contents',
      'layer_name',
      'export',
    ]
    
    self._processing_groups_functions = {}
    for functions in self._processing_groups.values():
      for function in functions:
        self._processing_groups_functions[function.__name__] = function
    
    self._invoker = None
    self._initial_invoker = pg.invoker.Invoker()
    self._NAME_ONLY_ACTION_GROUP = 'name'
  
  @property
  def layer_tree(self):
    return self._layer_tree
  
  @property
  def exported_layers(self):
    return self._exported_layers
  
  @property
  def current_layer_elem(self):
    return self._current_layer_elem
  
  @property
  def tagged_layer_elems(self):
    return self._tagged_layer_elems
  
  @property
  def inserted_tagged_layers(self):
    return self._inserted_tagged_layers
  
  @property
  def tagged_layer_copies(self):
    return self._tagged_layer_copies
  
  @property
  def default_file_extension(self):
    return self._default_file_extension
  
  @property
  def file_extension_properties(self):
    return self._file_extension_properties
  
  @property
  def invoker(self):
    return self._invoker
  
  def export(self, processing_groups=None, layer_tree=None, keep_image_copy=False):
    """
    Export layers as separate images from the specified image.
    
    `processing_groups` is a list of strings that control which parts of the
    export are effective and which are ignored. Multiple groups can be
    specified. The following groups are supported:
    
    * `'layer_contents'` - Perform only actions manipulating the layer
      itself, such as cropping, resizing, etc. This is useful to preview the
      layer(s).
    
    * `'layer_name'` - Perform only actions manipulating layer names
      and layer tree (but not layer contents). This is useful to preview the
      names of the exported layers.
    
    * `'export'` - Perform only actions that export the layer or create
      directories for the layer.
    
    If `processing_groups` is `None` or empty, perform normal export.
    
    If `layer_tree` is not `None`, use an existing instance of
    `itemtree.LayerTree` instead of creating a new one. If the instance had
    constraints set, they will be reset.
    
    A copy of the image and the layers to be exported are created so that the
    original image and its soon-to-be exported layers are left intact. The
    image copy is automatically destroyed after the export. To keep the image
    copy, pass `True` to `keep_image_copy`. In that case, this method returns
    the image copy. If an exception was raised or if no layer was exported, this
    method returns `None` and the image copy will be destroyed.
    """
    self._init_attributes(processing_groups, layer_tree, keep_image_copy)
    self._preprocess_layers()
    
    exception_occurred = False
    
    self._setup()
    try:
      self._export_layers()
    except Exception:
      exception_occurred = True
      raise
    finally:
      self._cleanup(exception_occurred)
    
    if self._keep_image_copy:
      if self._use_another_image_copy:
        return self._another_image_copy
      else:
        return self._image_copy
    else:
      return None
  
  def has_exported_layer(self, layer):
    """
    Return `True` if the specified `gimp.Layer` was exported in the last export,
    `False` otherwise.
    """
    return layer.ID in self._exported_layers_ids
  
  def stop(self):
    self._should_stop = True
  
  def add_procedure(self, *args, **kwargs):
    """
    Add a procedure to be applied during `export()`. The signature is the same
    as for `pygimplib.invoker.Invoker.add()`.
    
    Procedures added by this method are placed before procedures added by
    `actions.add()`.
    
    Unlike `actions.add()`, procedures added by this method do not act as
    settings, i.e. they are merely functions without GUI, are not saved
    persistently and are always enabled.
    """
    return self._initial_invoker.add(*args, **kwargs)
  
  def add_constraint(self, func, *args, **kwargs):
    """
    Add a constraint to be applied during `export()`. The first argument is the
    function to act as a filter (returning `True` or `False`). The rest of the
    signature is the same as for `pygimplib.invoker.Invoker.add()`.
    
    For more information, see `add_procedure()`.
    """
    return self._initial_invoker.add(
      _get_constraint_func(func), *args, **kwargs)
  
  def remove_action(self, *args, **kwargs):
    """
    Remove an action originally scheduled to be applied during `export()`.
    The signature is the same as for `pygimplib.invoker.Invoker.remove()`.
    """
    self._initial_invoker.remove(*args, **kwargs)
  
  def reorder_action(self, *args, **kwargs):
    """
    Reorder an action to be applied during `export()`.
    The signature is the same as for `pygimplib.invoker.Invoker.reorder()`.
    """
    self._initial_invoker.reorder(*args, **kwargs)
  
  def _init_attributes(self, processing_groups, layer_tree, keep_image_copy):
    self._invoker = pg.invoker.Invoker()
    self._add_actions()
    self._add_name_only_actions()
    
    self._enable_disable_processing_groups(processing_groups)
    
    if layer_tree is not None:
      self._layer_tree = layer_tree
    else:
      self._layer_tree = pg.itemtree.LayerTree(
        self.image, name=pg.config.SOURCE_NAME, is_filtered=True)
    
    self._keep_image_copy = keep_image_copy
    
    self._should_stop = False
    
    self._exported_layers = []
    self._exported_layers_ids = set()
    
    self._current_layer_elem = None
    
    self._output_directory = self.export_settings['output_directory'].value
    
    self._image_copy = None
    self._tagged_layer_elems = collections.defaultdict(list)
    self._tagged_layer_copies = collections.defaultdict(pg.utils.return_none_func)
    self._inserted_tagged_layers = collections.defaultdict(pg.utils.return_none_func)
    
    self._use_another_image_copy = False
    self._another_image_copy = None
    
    self.progress_updater.reset()
    
    self._default_file_extension = self.export_settings['file_extension'].value
    self._file_extension_properties = _FileExtensionProperties()
    
    self.current_file_extension = self._default_file_extension
    
    self._current_layer_export_status = ExportStatuses.NOT_EXPORTED_YET
    self._current_overwrite_mode = None
    
    self._layer_name_renamer = renamer.LayerNameRenamer(
      self, self.export_settings['layer_filename_pattern'].value)
  
  def _add_actions(self):
    self._invoker.add(
      builtin_procedures.set_active_layer, [actions.DEFAULT_PROCEDURES_GROUP])
    
    self._invoker.add(
      builtin_procedures.set_active_layer_after_action,
      [actions.DEFAULT_PROCEDURES_GROUP],
      foreach=True)
    
    self._invoker.add(
      self._initial_invoker,
      self._initial_invoker.list_groups(include_empty_groups=True))
    
    for procedure in actions.walk(self.export_settings['procedures']):
      add_action_from_settings(procedure, self._invoker)
    
    for constraint in actions.walk(self.export_settings['constraints']):
      add_action_from_settings(constraint, self._invoker)
  
  def _add_name_only_actions(self):
    for procedure in actions.walk(self.export_settings['procedures']):
      add_action_from_settings(
        procedure, self._invoker,
        [builtin_procedures.NAME_ONLY_TAG], [self._NAME_ONLY_ACTION_GROUP])
    
    for constraint in actions.walk(self.export_settings['constraints']):
      add_action_from_settings(
        constraint, self._invoker,
        [builtin_procedures.NAME_ONLY_TAG], [self._NAME_ONLY_ACTION_GROUP])
  
  def _enable_disable_processing_groups(self, processing_groups):
    for functions in self._processing_groups.values():
      for function in functions:
        setattr(self, function.__name__, self._processing_groups_functions[function.__name__])
    
    if processing_groups is None:
      processing_groups = self._default_processing_groups
    
    if 'layer_name' in processing_groups:
      processing_groups.append('_postprocess_layer_name')
    
    for processing_group, functions in self._processing_groups.items():
      if processing_group not in processing_groups:
        for function in functions:
          setattr(self, function.__name__, pg.utils.empty_func)
  
  def _preprocess_layers(self):
    if self._layer_tree.filter:
      self._layer_tree.reset_filter()
    
    self._reset_parents_in_layer_elems()
    
    self._set_layer_constraints()
    
    self.progress_updater.num_total_tasks = len(self._layer_tree)
    
    if self._keep_image_copy:
      with self._layer_tree.filter['layer_types'].remove_rule_temp(
             builtin_constraints.is_empty_group, False):
        num_layers_and_nonempty_groups = len(self._layer_tree)
        if num_layers_and_nonempty_groups > 1:
          self._use_another_image_copy = True
        elif num_layers_and_nonempty_groups < 1:
          self._keep_image_copy = False
  
  def _reset_parents_in_layer_elems(self):
    for layer_elem in self._layer_tree:
      layer_elem.parents = list(layer_elem.orig_parents)
      layer_elem.children = (
        list(layer_elem.orig_children) if layer_elem.orig_children is not None else None)
  
  def _set_layer_constraints(self):
    self._layer_tree.filter.add_subfilter(
      'layer_types', pg.objectfilter.ObjectFilter(pg.objectfilter.ObjectFilter.MATCH_ANY))
    
    self._invoker.invoke(
      [builtin_constraints.CONSTRAINTS_LAYER_TYPES_GROUP],
      [self],
      additional_args_position=_LAYER_EXPORTER_ARG_POSITION_IN_CONSTRAINTS)
    
    self._init_tagged_layer_elems()
    
    self._invoker.invoke(
      [actions.DEFAULT_CONSTRAINTS_GROUP],
      [self],
      additional_args_position=_LAYER_EXPORTER_ARG_POSITION_IN_CONSTRAINTS)
  
  def _init_tagged_layer_elems(self):
    with self._layer_tree.filter.add_rule_temp(builtin_constraints.has_tags):
      with self._layer_tree.filter['layer_types'].add_rule_temp(
             builtin_constraints.is_nonempty_group):
        for layer_elem in self._layer_tree:
          for tag in layer_elem.tags:
            self._tagged_layer_elems[tag].append(layer_elem)
  
  def _export_layers(self):
    for layer_elem in self._layer_tree:
      if self._should_stop:
        raise ExportLayersCancelError('export stopped by user')
      
      self._current_layer_elem = layer_elem
      
      if layer_elem.item_type in (layer_elem.ITEM, layer_elem.NONEMPTY_GROUP):
        self._process_and_export_item(layer_elem)
      elif layer_elem.item_type == layer_elem.EMPTY_GROUP:
        self._process_empty_group(layer_elem)
      else:
        raise ValueError(
          'invalid/unsupported item type "{}" in {}'.format(
            layer_elem.item_type, layer_elem))
  
  def _process_and_export_item(self, layer_elem):
    layer = layer_elem.item
    self._preprocess_layer_name(layer_elem)
    self._process_layer_name_for_preview(self._image_copy, layer)
    layer_copy = self._process_layer(layer_elem, self._image_copy, layer)
    self._export_layer(layer_elem, self._image_copy, layer_copy)
    self._postprocess_layer(self._image_copy, layer_copy)
    self._postprocess_layer_name(layer_elem)
    
    self.progress_updater.update_tasks()
    
    if self._current_overwrite_mode != pg.overwrite.OverwriteModes.SKIP:
      self._exported_layers.append(layer)
      self._exported_layers_ids.add(layer.ID)
      self._file_extension_properties[layer_elem.get_file_extension()].processed_count += 1
  
  def _process_empty_group(self, layer_elem):
    self._preprocess_empty_group_name(layer_elem)
    
    empty_group_dirpath = layer_elem.get_filepath(self._output_directory)
    self._make_dirs(empty_group_dirpath, self)
    
    self.progress_updater.update_text(
      _('Creating empty directory "{}"').format(empty_group_dirpath))
    self.progress_updater.update_tasks()
  
  def _setup(self):
    pdb.gimp_context_push()
    
    self._image_copy = pg.pdbutils.create_image_from_metadata(self.image)
    pdb.gimp_image_undo_freeze(self._image_copy)
    
    self._invoker.invoke(
      ['after_create_image_copy'], [self._image_copy], additional_args_position=0)
    
    if self._use_another_image_copy:
      self._another_image_copy = pg.pdbutils.create_image_from_metadata(self._image_copy)
      pdb.gimp_image_undo_freeze(self._another_image_copy)
    
    if pg.config.DEBUG_IMAGE_PROCESSING:
      self._display_id = pdb.gimp_display_new(self._image_copy)
  
  def _cleanup(self, exception_occurred=False):
    self._copy_non_modifying_parasites(self._image_copy, self.image)
    
    pdb.gimp_image_undo_thaw(self._image_copy)
    
    if pg.config.DEBUG_IMAGE_PROCESSING:
      pdb.gimp_display_delete(self._display_id)
    
    for tagged_layer_copy in self._tagged_layer_copies.values():
      if tagged_layer_copy is not None:
        pdb.gimp_item_delete(tagged_layer_copy)
    
    if ((not self._keep_image_copy or self._use_another_image_copy)
        or exception_occurred):
      pg.pdbutils.try_delete_image(self._image_copy)
      if self._use_another_image_copy:
        pdb.gimp_image_undo_thaw(self._another_image_copy)
        if exception_occurred:
          pg.pdbutils.try_delete_image(self._another_image_copy)
    
    pdb.gimp_context_pop()
  
  def _process_layer(self, layer_elem, image, layer):
    layer_copy = builtin_procedures.copy_and_insert_layer(image, layer, None, 0)
    self._invoker.invoke(
      ['after_insert_layer'], [image, layer_copy, self], additional_args_position=0)
    
    self._invoker.invoke(
      [actions.DEFAULT_PROCEDURES_GROUP],
      [image, layer_copy, self],
      additional_args_position=0)
    
    layer_copy = self._merge_and_resize_layer(image, layer_copy)
    
    image.active_layer = layer_copy
    
    layer_copy.name = layer.name
    
    self._invoker.invoke(
      ['after_process_layer'], [image, layer_copy, self], additional_args_position=0)
    
    return layer_copy
  
  def _postprocess_layer(self, image, layer):
    if not self._keep_image_copy:
      pdb.gimp_image_remove_layer(image, layer)
    else:
      if self._use_another_image_copy:
        another_layer_copy = pg.pdbutils.copy_and_paste_layer(
          layer, self._another_image_copy, None, len(self._another_image_copy.layers),
          remove_lock_attributes=True)
        
        another_layer_copy.name = layer.name
        
        pdb.gimp_image_remove_layer(image, layer)
  
  def _merge_and_resize_layer(self, image, layer):
    layer = pdb.gimp_image_merge_visible_layers(image, gimpenums.EXPAND_AS_NECESSARY)
    pdb.gimp_layer_resize_to_image_size(layer)
    return layer
  
  def _preprocess_layer_name(self, layer_elem):
    layer_elem.name = self._layer_name_renamer.rename(layer_elem)
    self.current_file_extension = self._default_file_extension
  
  def _preprocess_empty_group_name(self, layer_elem):
    self._layer_tree.validate_name(layer_elem)
    self._layer_tree.uniquify_name(layer_elem)
  
  def _process_layer_name_for_preview(self, image, layer):
    self._invoker.invoke(
      [self._NAME_ONLY_ACTION_GROUP],
      [image, layer, self],
      additional_args_position=0)
  
  def _process_layer_name(self, layer_elem, force_default_file_extension):
    if not force_default_file_extension:
      if self.current_file_extension == self._default_file_extension:
        layer_elem.name += '.' + self._default_file_extension
      else:
        layer_elem.set_file_extension(self.current_file_extension, keep_extra_trailing_periods=True)
    else:
      layer_elem.set_file_extension(
        self._default_file_extension, keep_extra_trailing_periods=True)
    
    self._layer_tree.validate_name(layer_elem)
    self._layer_tree.uniquify_name(
      layer_elem,
      uniquifier_position=self._get_uniquifier_position(
        layer_elem.name, layer_elem.get_file_extension()))
  
  def _postprocess_layer_name(self, layer_elem):
    if layer_elem.item_type == layer_elem.NONEMPTY_GROUP:
      self._layer_tree.reset_name(layer_elem)
  
  def _get_uniquifier_position(self, str_, file_extension):
    return len(str_) - len('.' + file_extension)
  
  def _export_layer(self, layer_elem, image, layer):
    self._process_layer_name(layer_elem, False)
    self._export(layer_elem, image, layer)
    
    if self._current_layer_export_status == ExportStatuses.USE_DEFAULT_FILE_EXTENSION:
      self._process_layer_name(layer_elem, True)
      self._export(layer_elem, image, layer)
  
  def _export(self, layer_elem, image, layer):
    output_filepath = layer_elem.get_filepath(self._output_directory)
    file_extension = layer_elem.get_file_extension()
    
    self.progress_updater.update_text(_('Saving "{}"').format(output_filepath))
    
    self._current_overwrite_mode, output_filepath = pg.overwrite.handle_overwrite(
      output_filepath, self.overwrite_chooser,
      self._get_uniquifier_position(output_filepath, file_extension))
    
    if self._current_overwrite_mode == pg.overwrite.OverwriteModes.CANCEL:
      raise ExportLayersCancelError('cancelled')
    
    if self._current_overwrite_mode != pg.overwrite.OverwriteModes.SKIP:
      self._make_dirs(os.path.dirname(output_filepath), self)
      
      self._export_once_wrapper(
        self._get_export_func(file_extension),
        self._get_run_mode(file_extension),
        image, layer, output_filepath, file_extension)
      if self._current_layer_export_status == ExportStatuses.FORCE_INTERACTIVE:
        self._export_once_wrapper(
          self._get_export_func(file_extension),
          gimpenums.RUN_INTERACTIVE,
          image, layer, output_filepath, file_extension)
  
  def _make_dirs(self, dirpath, layer_exporter):
    try:
      pg.path.make_dirs(dirpath)
    except OSError as e:
      try:
        message = e.args[1]
        if e.filename is not None:
          message += ': "{}"'.format(e.filename)
      except (IndexError, AttributeError):
        message = str(e)
      
      raise InvalidOutputDirectoryError(
        message, layer_exporter.current_layer_elem, layer_exporter.default_file_extension)
  
  def _export_once_wrapper(
        self, export_func, run_mode, image, layer, output_filepath, file_extension):
    with self.export_context_manager(
           run_mode, image, layer, output_filepath, *self.export_context_manager_args):
      self._export_once(export_func, run_mode, image, layer, output_filepath, file_extension)
  
  def _get_run_mode(self, file_extension):
    file_extension_property = self._file_extension_properties[file_extension]
    if file_extension_property.is_valid and file_extension_property.processed_count > 0:
      return gimpenums.RUN_WITH_LAST_VALS
    else:
      return self.initial_run_mode
  
  def _get_export_func(self, file_extension):
    return pg.fileformats.get_save_procedure(file_extension)
  
  def _export_once(self, export_func, run_mode, image, layer, output_filepath, file_extension):
    self._current_layer_export_status = ExportStatuses.NOT_EXPORTED_YET
    
    try:
      export_func(
        run_mode,
        image,
        layer,
        pg.utils.safe_encode_gimp(output_filepath),
        pg.utils.safe_encode_gimp(os.path.basename(output_filepath)))
    except RuntimeError as e:
      # HACK: Examining the exception message seems to be the only way to determine
      # some specific cases of export failure.
      if self._was_export_canceled_by_user(str(e)):
        raise ExportLayersCancelError(str(e))
      elif self._should_export_again_with_interactive_run_mode(str(e), run_mode):
        self._prepare_export_with_interactive_run_mode()
      elif self._should_export_again_with_default_file_extension(file_extension):
        self._prepare_export_with_default_file_extension(file_extension)
      else:
        raise ExportLayersError(str(e), layer, self._default_file_extension)
    else:
      self._current_layer_export_status = ExportStatuses.EXPORT_SUCCESSFUL
  
  def _was_export_canceled_by_user(self, exception_message):
    return any(
      message in exception_message.lower() for message in ['cancelled', 'canceled'])
  
  def _should_export_again_with_interactive_run_mode(
        self, exception_message, current_run_mode):
    return (
      'calling error' in exception_message.lower()
      and current_run_mode in (
        gimpenums.RUN_WITH_LAST_VALS, gimpenums.RUN_NONINTERACTIVE))
  
  def _prepare_export_with_interactive_run_mode(self):
    self._current_layer_export_status = ExportStatuses.FORCE_INTERACTIVE
  
  def _should_export_again_with_default_file_extension(self, file_extension):
    return file_extension != self._default_file_extension
  
  def _prepare_export_with_default_file_extension(self, file_extension):
    self._file_extension_properties[file_extension].is_valid = False
    self._current_layer_export_status = ExportStatuses.USE_DEFAULT_FILE_EXTENSION
  
  @staticmethod
  def _copy_non_modifying_parasites(src_image, dest_image):
    unused_, parasite_names = pdb.gimp_image_get_parasite_list(src_image)
    for parasite_name in parasite_names:
      if dest_image.parasite_find(parasite_name) is None:
        parasite = src_image.parasite_find(parasite_name)
        # Do not attach persistent or undoable parasites to avoid modifying
        # `dest_image`.
        if parasite.flags == 0:
          dest_image.parasite_attach(parasite)


#===============================================================================


_LAYER_EXPORTER_ARG_POSITION_IN_CONSTRAINTS = 1


def add_action_from_settings(action, invoker, tags=None, action_groups=None):
  if action.get_value('is_pdb_procedure', False):
    try:
      function = pdb[pg.utils.safe_encode_gimp(action['function'].value)]
    except KeyError:
      raise InvalidPdbProcedureError(
        'invalid PDB procedure "{}"'.format(action['function'].value))
  else:
    function = action['function'].value
  
  if function is None:
    return
  
  if tags is not None and not any(tag in action.tags for tag in tags):
    return
  
  function_args = tuple(arg_setting.value for arg_setting in action['arguments'])
  function_kwargs = {}
  
  if action.get_value('is_pdb_procedure', False):
    if _has_run_mode_param(function):
      function_kwargs = {b'run_mode': function_args[0]}
      function_args = function_args[1:]
    
    function = _get_action_func_for_pdb_procedure(function)
  
  if 'constraint' not in action.tags:
    function = _get_action_func_with_replaced_placeholders(function)
  
  if 'constraint' in action.tags:
    function = _get_constraint_func(function, subfilter=action['subfilter'].value)
  
  function = _apply_action_only_if_enabled(function, action['enabled'])
  
  if action_groups is None:
    action_groups = action['action_groups'].value
  
  invoker.add(function, action_groups, function_args, function_kwargs)


def _has_run_mode_param(pdb_procedure):
  return pdb_procedure.params and pdb_procedure.params[0][1] == 'run-mode'


def _get_action_func_for_pdb_procedure(pdb_procedure):
  def _pdb_procedure_as_action(image, layer, layer_exporter, *args, **kwargs):
    return pdb_procedure(*args, **kwargs)
  
  return _pdb_procedure_as_action


def _get_action_func_with_replaced_placeholders(function):
  def _action(image, layer, layer_exporter, *args, **kwargs):
    new_args, new_kwargs = placeholders.get_replaced_args_and_kwargs(
      args, kwargs, image, layer, layer_exporter)
    return function(image, layer, layer_exporter, *new_args, **new_kwargs)
  
  return _action


def _apply_action_only_if_enabled(action, setting_enabled):
  def _apply_action(*action_args, **action_kwargs):
    if setting_enabled.value:
      return action(*action_args, **action_kwargs)
    else:
      return False
  
  return _apply_action


def _get_constraint_func(rule_func, subfilter=None):
  def _add_rule_func(*args):
    layer_exporter, rule_func_args = _get_args_for_constraint_func(rule_func, args)
    
    if subfilter is None:
      object_filter = layer_exporter.layer_tree.filter
    else:
      object_filter = layer_exporter.layer_tree.filter[subfilter]
    
    object_filter.add_rule(rule_func, *rule_func_args)
  
  return _add_rule_func


def _get_args_for_constraint_func(rule_func, args):
  try:
    layer_exporter_arg_position = (
      inspect.getargspec(rule_func).args.index('layer_exporter'))
  except ValueError:
    layer_exporter_arg_position = None
  
  if layer_exporter_arg_position is not None:
    layer_exporter = args[layer_exporter_arg_position - 1]
    rule_func_args = args
  else:
    if len(args) > 1:
      layer_exporter_arg_position = (
        _LAYER_EXPORTER_ARG_POSITION_IN_CONSTRAINTS)
    else:
      layer_exporter_arg_position = (
        _LAYER_EXPORTER_ARG_POSITION_IN_CONSTRAINTS - 1)
    
    layer_exporter = args[layer_exporter_arg_position]
    rule_func_args = (
      args[:layer_exporter_arg_position] + args[layer_exporter_arg_position + 1:])
  
  return layer_exporter, rule_func_args


class _FileExtension(object):
  """
  This class defines additional properties for a file extension.
  
  Attributes:
  
  * `is_valid` - If `True`, file extension is valid and can be used in filenames
    for file export procedures.
  
  * `processed_count` - Number of items with the specific file extension that
    have already been exported.
  """
  
  def __init__(self):
    self.is_valid = True
    self.processed_count = 0


class _FileExtensionProperties(object):
  """Mapping of file extensions from `pygimplib.fileformats.file_formats` to
  `_FileExtension` instances.
  
  File extension as a key is always converted to lowercase.
  """
  def __init__(self):
    self._properties = collections.defaultdict(_FileExtension)
    
    for file_format in pg.fileformats.file_formats:
      # This ensures that the file format dialog will be displayed only once per
      # file format if multiple file extensions for the same format are used
      # (e.g. 'jpg', 'jpeg' or 'jpe' for the JPEG format).
      extension_properties = _FileExtension()
      for file_extension in file_format.file_extensions:
        self._properties[file_extension.lower()] = extension_properties
  
  def __getitem__(self, key):
    return self._properties[key.lower()]


@future.utils.python_2_unicode_compatible
class ExportLayersError(Exception):
  
  def __init__(self, message='', layer=None, file_extension=None):
    super().__init__()
    
    self._message = message
    
    try:
      self.layer_name = layer.name
    except AttributeError:
      self.layer_name = None
    
    self.file_extension = file_extension
  
  def __str__(self):
    str_ = self._message
    
    if self.layer_name:
      str_ += '\n' + _('Layer:') + ' ' + self.layer_name
    if self.file_extension:
      str_ += '\n' + _('File extension:') + ' ' + self.file_extension
    
    return str_


class ExportLayersCancelError(ExportLayersError):
  pass


class InvalidOutputDirectoryError(ExportLayersError):
  pass


class InvalidPdbProcedureError(ExportLayersError):
  pass


class ExportStatuses(object):
  EXPORT_STATUSES = (
    NOT_EXPORTED_YET, EXPORT_SUCCESSFUL, FORCE_INTERACTIVE, USE_DEFAULT_FILE_EXTENSION
  ) = (0, 1, 2, 3)
