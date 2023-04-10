# -*- coding: utf-8 -*-

"""Batch-processing layers and exporting layers as separate images."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import inspect

import gimp
from gimp import pdb

from export_layers import pygimplib as pg

from export_layers import actions
from export_layers import builtin_procedures
from export_layers import exceptions
from export_layers import export as export_
from export_layers import placeholders


_BATCHER_ARG_POSITION_IN_PROCEDURES = 0
_BATCHER_ARG_POSITION_IN_CONSTRAINTS = 0

_NAME_ONLY_ACTION_GROUP = 'name'


class Batcher(object):
  """Class for batch-processing layers in the specified image with a sequence of
  actions (resize, rename, export, ...).
  """
  
  def __init__(
        self,
        initial_run_mode,
        input_image,
        procedures,
        constraints,
        edit_mode=False,
        output_directory=gimp.user_directory(1),   # `Documents` directory
        layer_filename_pattern='',
        file_extension='png',
        overwrite_mode=pg.overwrite.OverwriteModes.SKIP,
        overwrite_chooser=None,
        progress_updater=None,
        item_tree=None,
        is_preview=False,
        process_contents=True,
        process_names=True,
        process_export=True,
        export_context_manager=None,
        export_context_manager_args=None,
        export_context_manager_kwargs=None):
    self._init_attributes(
      initial_run_mode=initial_run_mode,
      input_image=input_image,
      edit_mode=edit_mode,
      procedures=procedures,
      constraints=constraints,
      output_directory=output_directory,
      layer_filename_pattern=layer_filename_pattern,
      file_extension=file_extension,
      overwrite_mode=overwrite_mode,
      overwrite_chooser=overwrite_chooser,
      progress_updater=progress_updater,
      item_tree=item_tree,
      is_preview=is_preview,
      process_contents=process_contents,
      process_names=process_names,
      process_export=process_export,
      export_context_manager=export_context_manager,
      export_context_manager_args=export_context_manager_args,
      export_context_manager_kwargs=export_context_manager_kwargs,
    )
    
    self._current_item = None
    self._current_raw_item = None
    self._current_image = None
    
    self._orig_active_layer = None
    
    self._exported_raw_items = []
    
    self._should_stop = False
    
    self._invoker = None
    self._initial_invoker = pg.invoker.Invoker()
  
  @property
  def initial_run_mode(self):
    """The run mode to use for the first layer.
    
    For subsequent layers, `gimpenums.RUN_WITH_LAST_VALS` is used.
    This usually has effect when exporting layers - if `initial_run_mode` is
    `gimpenums.RUN_INTERACTIVE`, a native file format GUI is displayed for the
    first layer and the same settings are then applied to subsequent layers.
    If the file format in which the layer is exported to cannot handle
    `gimpenums.RUN_WITH_LAST_VALS`, `gimpenums.RUN_INTERACTIVE` is forced.
    """
    return self._initial_run_mode
  
  @property
  def input_image(self):
    """Input `gimp.Image` to process layers for."""
    return self._input_image
  
  @property
  def edit_mode(self):
    """If `True`, batch-edit layers directly in `input_image`. If `False`,
    batch-process and export layers.
    """
    return self._edit_mode
  
  @property
  def procedures(self):
    """`setting.Group` instance containing procedures."""
    return self._procedures
  
  @property
  def constraints(self):
    """`setting.Group` instance containing constraints.."""
    return self._constraints
  
  @property
  def output_directory(self):
    """Output directory path to save exported layers to."""
    return self._output_directory
  
  @property
  def layer_filename_pattern(self):
    """Filename pattern for layers to be exported."""
    return self._layer_filename_pattern
  
  @property
  def file_extension(self):
    """Filename extension for layers to be exported."""
    return self._file_extension
  
  @property
  def overwrite_mode(self):
    """One of the `pygimplib.overwrite.OverwriteModes` values indicating how to
    handle files with the same name."""
    return self._overwrite_mode
  
  @property
  def overwrite_chooser(self):
    """`pygimplib.overwrite.OverwriteChooser` instance that is invoked during
    export if a file with the same name already exists.
    
    If `None`, then `pygimplib.overwrite.NoninteractiveOverwriteChooser` is
    used.
    """
    return self._overwrite_chooser
  
  @property
  def progress_updater(self):
    """`pygimplib.progres.ProgressUpdater` instance indicating the number of
    layers processed so far.
    
    If no progress update is desired, pass `None`.
    """
    return self._progress_updater
  
  @property
  def item_tree(self):
    """`pygimplib.itemtree.ItemTree` instance containing layers to be processed.
    
    If `None` (the default), an item tree is automatically created at the start
    of processing. If `item_tree` has filters (constraints) set, they will be
    reset on each call to `run()`.
    """
    return self._item_tree
  
  @property
  def is_preview(self):
    """If `True`, only procedures and constraints that are marked as
    "enabled for previews" will be applied for previews. If `False`, this
    property has no effect (and effectively allows performing real processing).
    """
    return self._is_preview
  
  @property
  def process_contents(self):
    """If `True`, invoke procedures on layers.
    
    Setting this to `False` is useful if you require only layer names to be
    processed.
    """
    return self._process_contents
  
  @property
  def process_names(self):
    """If `True`, process layer names before export to be suitable to save to
    disk (in particular to remove characters invalid for a file system).
    
    If `is_preview` is `True` and `process_names` is `True`, also invoke
    built-in procedures modifying item names only (e.g. renaming layers).
    """
    return self._process_names
  
  @property
  def process_export(self):
    """If `True`, perform export of layers.
    
    Setting this to `False` is useful to preview the processed contents of a
    layer without saving it to a file.
    """
    return self._process_export
  
  @property
  def export_context_manager(self):
    """Context manager that wraps exporting a single layer.
    
    This can be used to perform GUI updates before and after export.
    Required parameters: current run mode, current image, layer to export,
    output filename of the layer.
    """
    return self._export_context_manager
  
  @property
  def export_context_manager_args(self):
    """Additional positional arguments passed to `export_context_manager`."""
    return self._export_context_manager_args
  
  @property
  def export_context_manager_kwargs(self):
    """Additional keyword arguments passed to `export_context_manager`."""
    return self._export_context_manager_kwargs
  
  @property
  def current_item(self):
    """A `pygimplib.itemtree.Item` instance currently being processed."""
    return self._current_item
  
  @property
  def current_raw_item(self):
    """Raw item (`gimp.Layer`) currently being processed."""
    return self._current_raw_item
  
  @current_raw_item.setter
  def current_raw_item(self, value):
    self._current_raw_item = value
  
  @property
  def current_image(self):
    """The current `gimp.Image` containing layer(s) being processed.
    
    If `edit_mode` is `True`, this is equivalent to `input_image`.
    
    If `edit_mode` is `False`, this is a copy of `input_image` to avoid
    modifying original layers.
    """
    return self._current_image
  
  @property
  def exported_raw_items(self):
    """List of layers that were successfully exported.
    
    Does not include layers skipped by the user (when files with the same names
    already exist).
    """
    return list(self._exported_raw_items)
  
  @property
  def invoker(self):
    """`pygimplib.invoker.Invoker` instance to manage procedures and constraints
    applied on layers.
    
    This property is reset on each call of `run()`.
    """
    return self._invoker
  
  def run(self, keep_image_copy=False, **kwargs):
    """Batch-processes and exports layers as separate images.
    
    A copy of the image and the layers to be processed are created so that the
    original image and its soon-to-be processed layers are left intact. The
    image copy is automatically destroyed once processing is done. To keep the
    image copy, pass `True` to `keep_image_copy`. In that case, this method
    returns the image copy. If an exception was raised or if no layer was
    exported, this method returns `None` and the image copy will be destroyed.
    
    `**kwargs` can contain arguments that can be passed to `Batcher.__init__()`.
    Arguments in `**kwargs` overwrite the corresponding `Batcher` properties.
    See the properties for details.
    """
    self._init_attributes(**kwargs)
    self._prepare_for_processing(self._item_tree, keep_image_copy)
    
    exception_occurred = False
    
    if self._process_contents:
      self._setup_contents()
    try:
      self._process_items()
    except Exception:
      exception_occurred = True
      raise
    finally:
      if self._process_contents:
        self._cleanup_contents(exception_occurred)
    
    if self._process_contents and self._keep_image_copy:
      return self._image_copy
    else:
      return None
  
  def stop(self):
    """Terminates batch processing prematurely.
    
    The termination occurs after the current item is processed completely.
    """
    self._should_stop = True
  
  def add_procedure(self, *args, **kwargs):
    """Adds a procedure to be applied during `run()`.
    
    The signature is the same as for `pygimplib.invoker.Invoker.add()`.
    
    Procedures added by this method are placed before procedures added by
    `actions.add()`.
    
    Procedures are added immediately before the start of processing. Thus,
    calling this method during processing will have no effect.
    
    Unlike `actions.add()`, procedures added by this method do not act as
    settings, i.e. they are merely functions without GUI, are not saved
    persistently and are always enabled.
    
    This class recognizes several action groups that are invoked at certain
    places when `run()` is called:
    * `'before_process_items'` - invoked before starting processing the first
      item. Only one argument is accepted - instance of this class.
    * `'before_process_items_contents'` - same as `'before_process_items'`, but
      applied only if `process_contents` is `True`.
    * `'after_process_items'` - invoked after finishing processing the last
      item. Only one argument is accepted - instance of this class.
    * `'after_process_items_contents'` - same as `'after_process_items'`, but
      applied only if `process_contents` is `True`.
    * `'before_process_item'` - invoked immediately before applying procedures
      on the layer.
      Three arguments are accepted:
        * instance of this class
        * the current `pygimplib.itemtree.Item` to be processed
        * the current GIMP item to be processed
    * `'before_process_item_contents'` - same as `'before_process_item'`, but
      applied only if `process_contents` is `True`.
    * `'after_process_item'` - invoked immediately after all procedures have
      been applied to the layer.
      Three arguments are accepted:
        * instance of this class
        * the current `pygimplib.itemtree.Item` that has been processed
        * the current GIMP item that has been processed
    * `'after_process_item_contents'` - same as `'after_process_item'`, but
      applied only if `process_contents` is `True`.
    * `'cleanup_contents'` - invoked after processing is finished and cleanup is
      commenced (e.g. removing temporary internal images). Use this if you
      create temporary images or items of your own. While you may also achieve
      the same effect with `'after_process_items_contents'`, using
      `'cleanup_contents'` is safer as it is also invoked when an exception is
      raised. Only one argument is accepted - instance of this class.
    """
    return self._initial_invoker.add(*args, **kwargs)
  
  def add_constraint(self, func, *args, **kwargs):
    """Adds a constraint to be applied during `run()`.
    
    The first argument is the function to act as a filter (returning `True` or
    `False`). The rest of the signature is the same as for
    `pygimplib.invoker.Invoker.add()`.
    
    For more information, see `add_procedure()`.
    """
    return self._initial_invoker.add(self._get_constraint_func(func), *args, **kwargs)
  
  def remove_action(self, *args, **kwargs):
    """Removes an action originally scheduled to be applied during `run()`.
    
    The signature is the same as for `pygimplib.invoker.Invoker.remove()`.
    """
    self._initial_invoker.remove(*args, **kwargs)
  
  def reorder_action(self, *args, **kwargs):
    """Reorders an action to be applied during `run()`.
    
    The signature is the same as for `pygimplib.invoker.Invoker.reorder()`.
    """
    self._initial_invoker.reorder(*args, **kwargs)
  
  def _add_action_from_settings(self, action, tags=None, action_groups=None):
    """Adds an action and wraps/processes the action's function according to the
    action's settings.
    
    For PDB procedures, the function name is converted to a proper function
    object. For constraints, the function is wrapped to act as a proper filter
    rule for `item_tree.filter`. Any placeholder objects (e.g. "current image")
    as function arguments are replaced with real objects during processing of
    each item.
    
    If `tags` is not `None`, the action will not be added if it does not contain
    any of the specified tags.
    
    If `action_groups` is not `None`, the action will be added to the specified
    action groups instead of the groups defined in `action['action_groups']`.
    """
    if action.get_value('is_pdb_procedure', False):
      try:
        function = pdb[pg.utils.safe_encode_gimp(action['function'].value)]
      except KeyError:
        raise exceptions.InvalidPdbProcedureError(
          'invalid PDB procedure "{}"'.format(action['function'].value))
    else:
      function = action['function'].value
    
    if function is None:
      return
    
    if tags is not None and not any(tag in action.tags for tag in tags):
      return
    
    orig_function = function
    function_args = tuple(arg_setting.value for arg_setting in action['arguments'])
    function_kwargs = {}
    
    if action.get_value('is_pdb_procedure', False):
      if self._has_run_mode_param(function):
        function_kwargs = {b'run_mode': function_args[0]}
        function_args = function_args[1:]
      
      function = self._get_action_func_for_pdb_procedure(function)
    
    function = self._get_action_func_with_replaced_placeholders(function)
    
    if 'constraint' in action.tags:
      function = self._get_constraint_func(
        function, orig_function, action['orig_name'].value, action['subfilter'].value)
    
    function = self._apply_action_only_if_enabled(function, action)
    
    if action_groups is None:
      action_groups = action['action_groups'].value
    
    self._invoker.add(function, action_groups, function_args, function_kwargs)
  
  def _has_run_mode_param(self, pdb_procedure):
    return pdb_procedure.params and pdb_procedure.params[0][1] == 'run-mode'
  
  def _get_action_func_for_pdb_procedure(self, pdb_procedure):
    def _pdb_procedure_as_action(batcher, *args, **kwargs):
      return pdb_procedure(*args, **kwargs)
    
    return _pdb_procedure_as_action
  
  def _get_action_func_with_replaced_placeholders(self, function):
    def _action(*args, **kwargs):
      new_args, new_kwargs = placeholders.get_replaced_args_and_kwargs(args, kwargs, self)
      return function(*new_args, **new_kwargs)
    
    return _action
  
  def _apply_action_only_if_enabled(self, function, action):
    if self._is_preview:
      def _apply_action_in_preview(*action_args, **action_kwargs):
        if action['enabled'].value and action['enabled_for_previews'].value:
          return function(*action_args, **action_kwargs)
        else:
          return False
      
      return _apply_action_in_preview
    else:
      def _apply_action(*action_args, **action_kwargs):
        if action['enabled'].value:
          return function(*action_args, **action_kwargs)
        else:
          return False
      
      return _apply_action
  
  def _get_constraint_func(self, func, orig_func=None, name='', subfilter=None):
    def _add_func(*args, **kwargs):
      func_args = self._get_args_for_constraint_func(
        orig_func if orig_func is not None else func, args)
      
      if subfilter is None:
        object_filter = self._item_tree.filter
      else:
        subfilter_ids = self._item_tree.filter.find(name=subfilter)
        if subfilter_ids:
          object_filter = self._item_tree.filter[subfilter_ids[0]]
        else:
          object_filter = self._item_tree.filter.add(pg.objectfilter.ObjectFilter(name=subfilter))
      
      object_filter.add(func, func_args, kwargs, name=name)
    
    return _add_func
  
  def _get_args_for_constraint_func(self, func, args):
    try:
      batcher_arg_position = inspect.getargspec(func).args.index('batcher')
    except ValueError:
      batcher_arg_position = None
    
    if batcher_arg_position is not None:
      func_args = args
    else:
      if len(args) > 1:
        batcher_arg_position = _BATCHER_ARG_POSITION_IN_CONSTRAINTS
      else:
        batcher_arg_position = 0
      
      func_args = args[:batcher_arg_position] + args[batcher_arg_position + 1:]
    
    return func_args
  
  def _init_attributes(self, **kwargs):
    init_argspec_names = set(inspect.getargspec(self.__init__).args)
    init_argspec_names.discard('self')
    
    for name, value in kwargs.items():
      if name in init_argspec_names:
        setattr(self, '_' + name, value)
      else:
        raise ValueError(
          'invalid keyword argument "{}" encountered; must be one of {}'.format(
            name, list(init_argspec_names)))
    
    if self._overwrite_chooser is None:
      self._overwrite_chooser = pg.overwrite.NoninteractiveOverwriteChooser(
        self._overwrite_mode)
    
    if self._progress_updater is None:
      self._progress_updater = pg.progress.ProgressUpdater(None)
    
    if self._export_context_manager is None:
      self._export_context_manager = pg.utils.EmptyContext
    
    if self._export_context_manager_args is None:
      self._export_context_manager_args = ()
    
    if self._export_context_manager_kwargs is None:
      self._export_context_manager_kwargs = {}
  
  def _prepare_for_processing(self, item_tree, keep_image_copy):
    if item_tree is not None:
      self._item_tree = item_tree
    else:
      self._item_tree = pg.itemtree.LayerTree(self._input_image, name=pg.config.SOURCE_NAME)
    
    if self._item_tree.filter:
      self._item_tree.reset_filter()
    
    self._keep_image_copy = keep_image_copy
    
    self._current_item = None
    self._current_raw_item = None
    self._current_image = self._input_image
    
    self._image_copy = None
    self._orig_active_layer = None
    
    self._should_stop = False
    
    self._exported_raw_items = []
    
    self._invoker = pg.invoker.Invoker()
    self._add_actions()
    self._add_name_only_actions()
    
    self._set_constraints()
    
    self._progress_updater.reset()
    self._progress_updater.num_total_tasks = len(self._item_tree)
  
  def _add_actions(self):
    self._invoker.add(
      builtin_procedures.set_active_and_current_layer, [actions.DEFAULT_PROCEDURES_GROUP])
    
    self._invoker.add(
      builtin_procedures.set_active_and_current_layer_after_action,
      [actions.DEFAULT_PROCEDURES_GROUP],
      foreach=True)
    
    if self._edit_mode:
      self._invoker.add(
        builtin_procedures.remove_locks_before_action_restore_locks_after_action,
        [actions.DEFAULT_PROCEDURES_GROUP],
        foreach=True)
    
    self._invoker.add(
      self._initial_invoker,
      self._initial_invoker.list_groups(include_empty_groups=True))
    
    self._add_default_rename_procedure([actions.DEFAULT_PROCEDURES_GROUP])
    
    for procedure in actions.walk(self._procedures):
      self._add_action_from_settings(procedure)
    
    self._add_default_export_procedure([actions.DEFAULT_PROCEDURES_GROUP])
    
    for constraint in actions.walk(self._constraints):
      self._add_action_from_settings(constraint)
  
  def _add_name_only_actions(self):
    self._add_default_rename_procedure([_NAME_ONLY_ACTION_GROUP])
    
    for procedure in actions.walk(self._procedures):
      self._add_action_from_settings(
        procedure, [builtin_procedures.NAME_ONLY_TAG], [_NAME_ONLY_ACTION_GROUP])
    
    self._add_default_export_procedure([_NAME_ONLY_ACTION_GROUP])
    
    for constraint in actions.walk(self._constraints):
      self._add_action_from_settings(
        constraint, [builtin_procedures.NAME_ONLY_TAG], [_NAME_ONLY_ACTION_GROUP])
  
  def _add_default_rename_procedure(self, action_groups):
    if (not self._edit_mode
        and not any(
          procedure['orig_name'].value == 'rename' and procedure['enabled'].value
          for procedure in actions.walk(self._procedures))):
      self._invoker.add(
        builtin_procedures.rename_layer,
        groups=action_groups,
        args=[self._layer_filename_pattern])
  
  def _add_default_export_procedure(self, action_groups):
    if (not self._edit_mode
        and not any(
          procedure['orig_name'].value == 'export' and procedure['enabled'].value
          for procedure in actions.walk(self._procedures))):
      self._invoker.add(
        export_.export,
        groups=action_groups,
        args=[self._file_extension, export_.ExportModes.EACH_LAYER])
  
  def _set_constraints(self):
    self._invoker.invoke(
      [actions.DEFAULT_CONSTRAINTS_GROUP],
      [self],
      additional_args_position=_BATCHER_ARG_POSITION_IN_CONSTRAINTS)
  
  def _setup_contents(self):
    pdb.gimp_context_push()
    
    if not self._edit_mode or self._is_preview:
      self._image_copy = pg.pdbutils.create_image_from_metadata(self._input_image)
      self._current_image = self._image_copy
      
      pdb.gimp_image_undo_freeze(self._current_image)
      
      if pg.config.DEBUG_IMAGE_PROCESSING:
        self._display_id = pdb.gimp_display_new(self._current_image)
    else:
      self._current_image = self._input_image
      pdb.gimp_image_undo_group_start(self._current_image)
    
    self._orig_active_layer = self._current_image.active_layer
  
  def _cleanup_contents(self, exception_occurred=False):
    self._invoker.invoke(
      ['cleanup_contents'],
      [self],
      additional_args_position=_BATCHER_ARG_POSITION_IN_PROCEDURES)
    
    if not self._edit_mode or self._is_preview:
      self._copy_non_modifying_parasites(self._current_image, self._input_image)
      
      pdb.gimp_image_undo_thaw(self._current_image)
      
      if pg.config.DEBUG_IMAGE_PROCESSING:
        pdb.gimp_display_delete(self._display_id)
      
      if not self._keep_image_copy or exception_occurred:
        pg.pdbutils.try_delete_image(self._current_image)
    else:
      if pdb.gimp_item_is_valid(self._orig_active_layer):
        self._current_image.active_layer = self._orig_active_layer
      pdb.gimp_image_undo_group_end(self._current_image)
      pdb.gimp_displays_flush()
    
    pdb.gimp_context_pop()
    
    self._current_item = None
    self._current_raw_item = None
    self._current_image = None
  
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
  
  def _process_items(self):
    self._invoker.invoke(
      ['before_process_items'],
      [self],
      additional_args_position=_BATCHER_ARG_POSITION_IN_PROCEDURES)
    
    if self._process_contents:
      self._invoker.invoke(
        ['before_process_items_contents'],
        [self],
        additional_args_position=_BATCHER_ARG_POSITION_IN_PROCEDURES)
    
    for item in self._item_tree:
      if self._should_stop:
        raise exceptions.BatcherCancelError('stopped by user')
      
      if self._edit_mode:
        self._progress_updater.update_text(_('Processing "{}"').format(item.orig_name))
      
      self._process_item(item)
    
    if self._process_contents:
      self._invoker.invoke(
        ['after_process_items_contents'],
        [self],
        additional_args_position=_BATCHER_ARG_POSITION_IN_PROCEDURES)
    
    self._invoker.invoke(
      ['after_process_items'],
      [self],
      additional_args_position=_BATCHER_ARG_POSITION_IN_PROCEDURES)
  
  def _process_item(self, item):
    self._current_item = item
    self._current_raw_item = item.raw
    
    if self._is_preview and self._process_names:
      self._process_item_with_name_only_actions()
    
    if self._process_contents:
      self._process_item_with_actions(item, self._current_raw_item)
      self._refresh_current_image(self._current_raw_item)
    
    self._progress_updater.update_tasks()
  
  def _process_item_with_name_only_actions(self):
    self._invoker.invoke(
      ['before_process_item'],
      [self, self._current_item, self._current_raw_item],
      additional_args_position=_BATCHER_ARG_POSITION_IN_PROCEDURES)
    
    self._invoker.invoke(
      [_NAME_ONLY_ACTION_GROUP],
      [self],
      additional_args_position=_BATCHER_ARG_POSITION_IN_PROCEDURES)
    
    self._invoker.invoke(
      ['after_process_item'],
      [self, self._current_item, self._current_raw_item],
      additional_args_position=_BATCHER_ARG_POSITION_IN_PROCEDURES)
  
  def _process_item_with_actions(self, item, raw_item):
    if not self._edit_mode or self._is_preview:
      raw_item_copy = pg.pdbutils.copy_and_paste_layer(
        raw_item, self._current_image, None, len(self._current_image.layers), True, True)
      
      self._current_raw_item = raw_item_copy
      self._current_raw_item.name = raw_item.name
    
    self._invoker.invoke(
      ['before_process_item'],
      [self, self._current_item, self._current_raw_item],
      additional_args_position=_BATCHER_ARG_POSITION_IN_PROCEDURES)
    
    if self._process_contents:
      self._invoker.invoke(
        ['before_process_item_contents'],
        [self, self._current_item, self._current_raw_item],
        additional_args_position=_BATCHER_ARG_POSITION_IN_PROCEDURES)
    
    self._invoker.invoke(
      [actions.DEFAULT_PROCEDURES_GROUP],
      [self],
      additional_args_position=_BATCHER_ARG_POSITION_IN_PROCEDURES)
    
    if self._process_contents:
      self._invoker.invoke(
        ['after_process_item_contents'],
        [self, self._current_item, self._current_raw_item],
        additional_args_position=_BATCHER_ARG_POSITION_IN_PROCEDURES)
    
    self._invoker.invoke(
      ['after_process_item'],
      [self, self._current_item, self._current_raw_item],
      additional_args_position=_BATCHER_ARG_POSITION_IN_PROCEDURES)
  
  def _refresh_current_image(self, raw_item):
    if not self._edit_mode and not self._keep_image_copy:
      for layer in self._current_image.layers:
        pdb.gimp_image_remove_layer(self._current_image, layer)
