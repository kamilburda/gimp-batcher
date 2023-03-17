# -*- coding: utf-8 -*-

"""Built-in procedure to export a given item as an image."""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import os

import gimpenums

from export_layers import pygimplib as pg

from export_layers import export_errors
from export_layers import uniquifier


def export(exporter):
  item_uniquifier = uniquifier.ItemUniquifier()
  file_extension_properties = _FileExtensionProperties()
  processed_parent_names = set()
  
  while True:
    item = exporter.current_item
    raw_item = exporter.current_raw_item
    image = exporter.current_image
    
    exporter.current_file_extension = exporter.default_file_extension
    
    if exporter.process_names:
      _process_parent_folder_names(item, item_uniquifier, processed_parent_names)
      _process_item_name(exporter, item, item_uniquifier, False)
    
    if exporter.process_export:
      export_status = _export_item(exporter, item, image, raw_item, file_extension_properties)
      
      if export_status == ExportStatuses.USE_DEFAULT_FILE_EXTENSION:
        if exporter.process_names:
          _process_item_name(exporter, item, item_uniquifier, True)
        
        if exporter.process_export:
          _export_item(exporter, item, image, raw_item, file_extension_properties)
      
      if exporter.current_overwrite_mode != pg.overwrite.OverwriteModes.SKIP:
        file_extension_properties[pg.path.get_file_extension(item.name)].processed_count += 1
    
    unused_ = yield


def _process_parent_folder_names(item, item_uniquifier, processed_parent_names):
  for parent in item.parents:
    if parent not in processed_parent_names:
      _validate_name(parent)
      item_uniquifier.uniquify(parent)
      
      processed_parent_names.add(parent)


def _process_item_name(exporter, item, item_uniquifier, force_default_file_extension):
  if not force_default_file_extension:
    if exporter.current_file_extension == exporter.default_file_extension:
      item.name += '.' + exporter.default_file_extension
    else:
      item.name = pg.path.get_filename_with_new_file_extension(
        item.name, exporter.current_file_extension, keep_extra_trailing_periods=True)
  else:
    item.name = pg.path.get_filename_with_new_file_extension(
      item.name, exporter.default_file_extension, keep_extra_trailing_periods=True)
  
  _validate_name(item)
  item_uniquifier.uniquify(
    item,
    position=_get_unique_substring_position(item.name, pg.path.get_file_extension(item.name)))


def _validate_name(item):
  item.name = pg.path.FilenameValidator.validate(item.name)


def _get_unique_substring_position(str_, file_extension):
  return len(str_) - len('.' + file_extension)


def _export_item(exporter, item, image, raw_item, file_extension_properties):
  output_filepath = _get_item_filepath(item, exporter.export_settings['output_directory'].value)
  file_extension = pg.path.get_file_extension(item.name)
  export_status = ExportStatuses.NOT_EXPORTED_YET
  
  exporter.progress_updater.update_text(_('Saving "{}"').format(output_filepath))
  
  exporter.current_overwrite_mode, output_filepath = pg.overwrite.handle_overwrite(
    output_filepath, exporter.overwrite_chooser,
    _get_unique_substring_position(output_filepath, file_extension))
  
  if exporter.current_overwrite_mode == pg.overwrite.OverwriteModes.CANCEL:
    raise export_errors.ExportCancelError('cancelled')
  
  if exporter.current_overwrite_mode != pg.overwrite.OverwriteModes.SKIP:
    _make_dirs(exporter, os.path.dirname(output_filepath))
    
    export_status = _export_item_once_wrapper(
      exporter,
      _get_export_func(file_extension),
      _get_run_mode(exporter, file_extension, file_extension_properties),
      image, raw_item, output_filepath, file_extension, file_extension_properties)
    if export_status == ExportStatuses.FORCE_INTERACTIVE:
      export_status = _export_item_once_wrapper(
        exporter,
        _get_export_func(file_extension),
        gimpenums.RUN_INTERACTIVE,
        image, raw_item, output_filepath, file_extension, file_extension_properties)
  
  return export_status


def _get_item_filepath(item, dirpath):
  """Returns a file path based on the specified directory path and the name of
  the item and its parents.
  
  The file path created has the following format:
    
    <directory path>/<item path components>/<item name>
  
  If the directory path is not an absolute path or is `None`, the
  current working directory is prepended.
  
  Item path components consist of parents' item names, starting with the
  topmost parent.
  """
  if dirpath is None:
    dirpath = ''
  
  path = os.path.abspath(dirpath)
  
  path_components = [parent.name for parent in item.parents]
  if path_components:
    path = os.path.join(path, os.path.join(*path_components))
  
  return os.path.join(path, item.name)


def _make_dirs(exporter, dirpath):
  try:
    pg.path.make_dirs(dirpath)
  except OSError as e:
    try:
      message = e.args[1]
      if e.filename is not None:
        message += ': "{}"'.format(e.filename)
    except (IndexError, AttributeError):
      message = str(e)
    
    raise export_errors.InvalidOutputDirectoryError(
      message, exporter.current_item.name, exporter.default_file_extension)


def _export_item_once_wrapper(
      exporter, export_func, run_mode, image, raw_item, output_filepath, file_extension,
      file_extension_properties):
  with exporter.export_context_manager(
         run_mode, image, raw_item, output_filepath, *exporter.export_context_manager_args):
    export_status = _export_item_once(
      exporter, export_func, run_mode, image, raw_item, output_filepath, file_extension,
      file_extension_properties)
  
  return export_status


def _get_run_mode(exporter, file_extension, file_extension_properties):
  file_extension_property = file_extension_properties[file_extension]
  if file_extension_property.is_valid and file_extension_property.processed_count > 0:
    return gimpenums.RUN_WITH_LAST_VALS
  else:
    return exporter.initial_run_mode


def _get_export_func(file_extension):
  return pg.fileformats.get_save_procedure(file_extension)


def _export_item_once(
      exporter, export_func, run_mode, image, raw_item, output_filepath, file_extension,
      file_extension_properties):
  export_status = ExportStatuses.NOT_EXPORTED_YET
  
  try:
    export_func(
      run_mode,
      image,
      raw_item,
      pg.utils.safe_encode_gimp(output_filepath),
      pg.utils.safe_encode_gimp(os.path.basename(output_filepath)))
  except RuntimeError as e:
    # HACK: Examining the exception message seems to be the only way to determine
    # some specific cases of export failure.
    if _was_export_canceled_by_user(str(e)):
      raise export_errors.ExportCancelError(str(e))
    elif _should_export_again_with_interactive_run_mode(str(e), run_mode):
      export_status = ExportStatuses.FORCE_INTERACTIVE
    elif _should_export_again_with_default_file_extension(exporter, file_extension):
      file_extension_properties[file_extension].is_valid = False
      export_status = ExportStatuses.USE_DEFAULT_FILE_EXTENSION
    else:
      raise export_errors.ExportError(str(e), raw_item.name, exporter.default_file_extension)
  else:
    export_status = ExportStatuses.EXPORT_SUCCESSFUL
  
  return export_status


def _was_export_canceled_by_user(exception_message):
  return any(message in exception_message.lower() for message in ['cancelled', 'canceled'])


def _should_export_again_with_interactive_run_mode(exception_message, current_run_mode):
  return (
    'calling error' in exception_message.lower()
    and current_run_mode in [gimpenums.RUN_WITH_LAST_VALS, gimpenums.RUN_NONINTERACTIVE])


def _should_export_again_with_default_file_extension(exporter, file_extension):
  return file_extension != exporter.default_file_extension


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


class ExportStatuses(object):
  EXPORT_STATUSES = (
    NOT_EXPORTED_YET, EXPORT_SUCCESSFUL, FORCE_INTERACTIVE, USE_DEFAULT_FILE_EXTENSION
  ) = (0, 1, 2, 3)
