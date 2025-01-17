"""Managing file formats supported by GIMP and some third-party plug-ins.

A list of file format wrappers is provided that contains at least a name and a
list of file extensions. The list can be used for:
* checking that a file format is supported,
* obtaining file format options (arguments).
"""

import pygimplib as pg
from pygimplib import pdb

from src import settings_from_pdb as settings_from_pdb_


def fill_file_format_options(file_format_options, file_format, import_or_export):
  processed_file_format = FILE_FORMAT_ALIASES.get(file_format, file_format)

  if (processed_file_format is None
      or processed_file_format in file_format_options
      or processed_file_format not in FILE_FORMATS_DICT):
    return

  if import_or_export == 'import':
    pdb_proc_name = FILE_FORMATS_DICT[processed_file_format].import_procedure_name
    common_arguments = _COMMON_PDB_ARGUMENTS_FOR_FILE_LOAD
  elif import_or_export == 'export':
    pdb_proc_name = FILE_FORMATS_DICT[processed_file_format].export_procedure_name
    common_arguments = _COMMON_PDB_ARGUMENTS_FOR_FILE_EXPORT
  else:
    raise ValueError('invalid value for import_or_export; must be either "import" or "export"')

  if pdb_proc_name is None or pdb_proc_name not in pdb:
    return

  _pdb_proc, _pdb_proc_name, file_format_options_list = (
    settings_from_pdb_.get_setting_data_from_pdb_procedure(pdb_proc_name))

  processed_file_format_options_list = _remove_common_file_format_options(
    file_format_options_list, common_arguments)

  options_settings = create_file_format_options_settings(
    processed_file_format_options_list)

  file_format_options[processed_file_format] = options_settings


def _remove_common_file_format_options(file_format_options_list, common_arguments):
  return [
    option_dict for index, option_dict in enumerate(file_format_options_list)
    if not (
      index in common_arguments
      and common_arguments[index] == option_dict.get('name', None))
  ]


def create_file_format_options_settings(file_format_options_list):
  group = pg.setting.Group('file_format_options')

  processed_file_format_options_list = []
  file_format_options_values = {}

  for file_format_options in file_format_options_list:
    if 'value' in file_format_options:
      # The 'value' key must not be present when creating settings in a group
      # from a dictionary.
      file_format_options_values[file_format_options['name']] = file_format_options.pop('value')

    processed_file_format_options_list.append(file_format_options)

  group.add(processed_file_format_options_list)

  for setting_name, value in file_format_options_values.items():
    group[setting_name].set_value(value)

  return group


def fill_and_get_file_format_options_as_kwargs(
      file_format_options, file_format, import_or_export):
  fill_file_format_options(file_format_options, file_format, import_or_export)

  if file_format in file_format_options:
    return {
      setting.name.replace('-', '_'): setting.value_for_pdb
      for setting in file_format_options[file_format]
    }
  else:
    return None


def file_format_procedure_exists(file_format, import_or_export):
  if file_format not in FILE_FORMATS_DICT:
    return False

  if import_or_export == 'import':
    pdb_proc_name = FILE_FORMATS_DICT[file_format].import_procedure_name
  elif import_or_export == 'export':
    pdb_proc_name = FILE_FORMATS_DICT[file_format].export_procedure_name
  else:
    raise ValueError('invalid value for import_or_export; must be either "import" or "export"')

  return pdb_proc_name in pdb


class _FileFormat:
  
  def __init__(
        self,
        file_extensions,
        import_procedure_name=None,
        import_func=None,
        export_procedure_name=None,
        export_func=None,
        version_check_func=None,
        description=None,
        **kwargs):
    self.file_extensions = file_extensions
    
    self.import_procedure_name = import_procedure_name
    self._import_func = import_func

    self.export_procedure_name = export_procedure_name
    self._export_func = export_func
    
    self.version_check_func = version_check_func if version_check_func is not None else lambda: True

    self._description = description
    
    for name, value in kwargs.items():
      setattr(self, name, value)

  def get_description(self, import_or_export, max_char_length_for_inferred_description=35):
    """Returns the description of the file format.

    If passing ``description=None`` to `__init__()` and ``import_or_export``
    is equal to ``'import'`` or ``'export'``, the description is inferred
    from the procedure whose name is `import_procedure_name` or
    `export_procedure_name`, respectively. If the load/export procedure does
    not exist, the string ``'<first file extension in uppercase> image'`` is
    returned. The string is also returned if the procedure exists and the label
    has more than ``max_char_length_for_inferred_description`` characters.

    If passing a string to the ``description`` parameter in `__init__()`,
    then that description is returned.
    """
    if self._description is not None:
      return self._description
    else:
      if import_or_export not in ['import', 'export']:
        raise ValueError('invalid value for import_or_export; must be either "import" or "export"')

      menu_label = None

      if import_or_export == 'import' and self.import_procedure_name in pdb:
        menu_label = pdb[self.import_procedure_name].menu_label

      if import_or_export == 'export' and self.export_procedure_name in pdb:
        menu_label = pdb[self.export_procedure_name].menu_label

      if menu_label and len(menu_label) <= max_char_length_for_inferred_description:
        return menu_label
      else:
        return _('{} image').format(self.file_extensions[0].upper())

  def is_import_installed(self):
    return self._is_import_proc_builtin() or self.import_procedure_name in pdb

  def _is_import_proc_builtin(self):
    return self.import_procedure_name is None

  def is_export_installed(self):
    return self._is_export_proc_builtin() or self.export_procedure_name in pdb

  def _is_export_proc_builtin(self):
    return self.export_procedure_name is None

  def get_import_func(self):
    if self._import_func is None:
      return getattr(pdb, self.import_procedure_name)
    else:
      return self._import_func

  def get_export_func(self):
    if self._export_func is None:
      return getattr(pdb, self.export_procedure_name)
    else:
      return self._export_func


def _create_file_formats(file_formats_params):
  return [_FileFormat(**params) for params in file_formats_params]


def _create_file_formats_dict(file_formats):
  file_formats_dict = {}

  for file_format in file_formats:
    for file_extension in file_format.file_extensions:
      if file_extension not in file_formats_dict and file_format.version_check_func():
        file_formats_dict[file_extension] = file_format

  return file_formats_dict


def _create_file_format_aliases(file_formats):
  file_format_aliases = {}

  for file_format in file_formats:
    for file_extension in file_format.file_extensions:
      if file_extension not in file_format_aliases:
        file_format_aliases[file_extension] = file_format.file_extensions[0]

  return file_format_aliases


def _gimp_xcf_save_wrapper(options=None, **kwargs):
  pdb.gimp_xcf_save(**kwargs)


FILE_FORMATS = _create_file_formats([
  {'file_extensions': ['txt', 'ansi', 'text'],
   'export_procedure_name': 'file-aa-export'},
  {'file_extensions': ['ani'],
   'export_procedure_name': 'file-ani-export'},
  {'file_extensions': ['bmp'],
   'export_procedure_name': 'file-bmp-export'},
  {'file_extensions': ['xcf.bz2', 'xcfbz2'],
   'export_procedure_name': 'file-bz2-export'},
  {'file_extensions': ['cel'],
   'export_procedure_name': 'file-cel-export'},
  {'file_extensions': ['xhtml'],
   'export_procedure_name': 'file-colorxhtml-export'},
  {'file_extensions': ['c'],
   'export_procedure_name': 'file-csource-export'},
  {'file_extensions': ['cur'],
   'export_procedure_name': 'file-cur-export'},
  {'file_extensions': ['dds'],
   'export_procedure_name': 'file-dds-export'},
  {'file_extensions': ['dicom', 'dcm'],
   'export_procedure_name': 'file-dicom-export'},
  {'file_extensions': ['eps'],
   'export_procedure_name': 'file-eps-export'},
  {'file_extensions': ['exr'],
   'export_procedure_name': 'file-exr-export'},
  {'file_extensions': ['ff'],
   'export_procedure_name': 'file-farbfeld-export'},
  {'file_extensions': ['fli', 'flc'],
   'export_procedure_name': 'file-fli-export'},
  {'file_extensions': ['gbr'],
   'export_procedure_name': 'file-gbr-export'},
  {'file_extensions': ['gif'],
   'export_procedure_name': 'file-gif-export'},
  {'file_extensions': ['xcf.gz', 'xcfgz'],
   'export_procedure_name': 'file-gz-export'},
  {'file_extensions': ['h'],
   'export_procedure_name': 'file-header-export'},
  {'file_extensions': ['fit', 'fits'],
   'export_procedure_name': 'file-fits-export'},
  {'file_extensions': ['gih'],
   'export_procedure_name': 'file-gih-export'},
  {'file_extensions': ['avif'],
   'export_procedure_name': 'file-heif-av1-export'},
  {'file_extensions': ['heif', 'heic'],
   'export_procedure_name': 'file-heif-export'},
  {'file_extensions': ['html', 'htm'],
   'export_procedure_name': 'file-html-table-export'},
  {'file_extensions': ['icns'],
   'export_procedure_name': 'file-icns-export'},
  {'file_extensions': ['ico'],
   'export_procedure_name': 'file-ico-export'},
  {'file_extensions': ['jpg', 'jpeg', 'jpe'],
   'export_procedure_name': 'file-jpeg-export'},
  {'file_extensions': ['jxl'],
   'export_procedure_name': 'file-jpegxl-export'},
  {'file_extensions': ['mng'],
   'export_procedure_name': 'file-mng-export'},
  {'file_extensions': ['ora'],
   'export_procedure_name': 'file-openraster-export'},
  {'file_extensions': ['pam'],
   'export_procedure_name': 'file-pam-export'},
  {'file_extensions': ['pat'],
   'export_procedure_name': 'file-pat-export'},
  {'file_extensions': ['pbm'],
   'export_procedure_name': 'file-pbm-export'},
  {'file_extensions': ['pcx', 'pcc'],
   'export_procedure_name': 'file-pcx-export'},
  {'file_extensions': ['pdf'],
   'export_procedure_name': 'file-pdf-export'},
  {'file_extensions': ['pfm'],
   'export_procedure_name': 'file-pfm-export'},
  {'file_extensions': ['pgm'],
   'export_procedure_name': 'file-pgm-export'},
  {'file_extensions': ['pix', 'matte', 'mask', 'alpha', 'als'],
   'export_procedure_name': 'file-pix-export'},
  {'file_extensions': ['png'],
   'export_procedure_name': 'file-png-export'},
  {'file_extensions': ['pnm'],
   'export_procedure_name': 'file-pnm-export'},
  {'file_extensions': ['ppm'],
   'export_procedure_name': 'file-ppm-export'},
  {'file_extensions': ['ps'],
   'export_procedure_name': 'file-ps-export'},
  {'file_extensions': ['psd'],
   'export_procedure_name': 'file-psd-export'},
  {'file_extensions': ['qoi'],
   'export_procedure_name': 'file-qoi-export'},
  {'file_extensions': ['raw', 'data'],
   'export_procedure_name': 'file-raw-export'},
  {'file_extensions': ['hdr'],
   'export_procedure_name': 'file-export-rgbe'},
  {'file_extensions': ['sgi', 'rgb', 'rgba', 'bw', 'icon'],
   'export_procedure_name': 'file-sgi-export'},
  {'file_extensions': ['im1', 'im8', 'im24', 'im32', 'rs', 'ras', 'sun'],
   'export_procedure_name': 'file-sunras-export'},
  {'file_extensions': ['tga'],
   'export_procedure_name': 'file-tga-export'},
  {'file_extensions': ['tif', 'tiff'],
   'export_procedure_name': 'file-tiff-export'},
  {'file_extensions': ['webp'],
   'export_procedure_name': 'file-webp-export'},
  {'file_extensions': ['xbm', 'bitmap'],
   'export_procedure_name': 'file-xbm-export'},
  {'file_extensions': ['xcf'],
   'export_procedure_name': 'gimp-xcf-save',
   'export_func': _gimp_xcf_save_wrapper},
  {'file_extensions': ['xmc'],
   'export_procedure_name': 'file-xmc-export'},
  {'file_extensions': ['xpm'],
   'export_procedure_name': 'file-xpm-export'},
  {'file_extensions': ['xwd'],
   'export_procedure_name': 'file-xwd-export'},
  {'file_extensions': ['xcf.xz', 'xcfxz'],
   'export_procedure_name': 'file-xz-export'},
])
"""List of `_FileFormat` instances representing file import and export
procedures.
"""

FILE_FORMATS_DICT = _create_file_formats_dict(FILE_FORMATS)
"""Dictionary of (file extension, `_FileFormat` instance) pairs representing
file import and export procedures.

Only `_FileFormat` instances compatible with the version of the currently 
running GIMP instance are included.
"""

FILE_FORMAT_ALIASES = _create_file_format_aliases(FILE_FORMATS)

# HACK: Is there a better way to detect common arguments for load/export procedures?
_COMMON_PDB_ARGUMENTS_FOR_FILE_LOAD = {
  0: 'run-mode',
  1: 'file',
}

_COMMON_PDB_ARGUMENTS_FOR_FILE_EXPORT = {
  0: 'run-mode',
  1: 'image',
  2: 'file',
  3: 'options',
}
