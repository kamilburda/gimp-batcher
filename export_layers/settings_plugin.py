# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2018 khalim19 <khalim19@gmail.com>
#
# Export Layers is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Export Layers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Export Layers.  If not, see <https://www.gnu.org/licenses/>.

"""
This module defines the plug-in settings.
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import collections
import os

import gimp
import gimpenums

from export_layers import builtin_constraints
from export_layers import builtin_operations

from export_layers import pygimplib
from export_layers.pygimplib import pgoverwrite
from export_layers.pygimplib import pgpath
from export_layers.pygimplib import pgsetting
from export_layers.pygimplib import pgsettinggroup


def create_settings():
  settings = pgsettinggroup.create_groups({
    "name": "all_settings",
    "groups": [
      {
        # These settings require special handling in the code, hence their separation
        # from the other settings.
        "name": "special",
        "tags": ["ignore_reset", "ignore_load", "ignore_save"],
      },
      {
        "name": "main",
        "setting_attributes": {
          "setting_sources": [
            pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT]},
        "groups": [
          {
            "name": "operations",
            "setting_attributes": {
              "pdb_type": None,
              "setting_sources": [
                pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT]
            }
          },
          {
            "name": "constraints",
            "setting_attributes": {
              "pdb_type": None,
              "setting_sources": [
                pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT]
            },
            "groups": [
              {
                "name": "include",
                "display_name": _("Include"),
                "setting_attributes": {
                  "pdb_type": None,
                  "setting_sources": [
                    pygimplib.config.SOURCE_SESSION, pygimplib.config.SOURCE_PERSISTENT]
                }
              }
            ]
          }
        ]
      }
    ]
  })
  
  settings["special"].add([
    {
      "type": pgsetting.SettingTypes.enumerated,
      "name": "run_mode",
      "default_value": "non_interactive",
      "items": [
        ("interactive", "RUN-INTERACTIVE", gimpenums.RUN_INTERACTIVE),
        ("non_interactive", "RUN-NONINTERACTIVE", gimpenums.RUN_NONINTERACTIVE),
        ("run_with_last_vals", "RUN-WITH-LAST-VALS", gimpenums.RUN_WITH_LAST_VALS)],
      "display_name": _("The run mode")
    },
    {
      "type": pgsetting.SettingTypes.image,
      "name": "image",
      "default_value": None,
      "display_name": _("Image")
    },
    {
      "type": pgsetting.SettingTypes.boolean,
      "name": "first_plugin_run",
      "default_value": True,
      "pdb_type": None,
      "setting_sources": [pygimplib.config.SOURCE_SESSION]
    },
  ])
  
  settings["main"].add([
    {
      "type": pgsetting.SettingTypes.file_extension,
      "name": "file_extension",
      "default_value": "png",
      "display_name": "File extension"
    },
    {
      "type": pgsetting.SettingTypes.string,
      "name": "output_directory",
      "default_value": gimp.user_directory(1),   # `Documents` directory
      "display_name": _("Output directory"),
      "gui_type": None,
      "tags": ["ignore_reset"]
    },
    {
      "type": pgsetting.SettingTypes.boolean,
      "name": "layer_groups_as_folders",
      "default_value": False,
      "display_name": _("Treat layer groups as folders")
    },
    {
      "type": pgsetting.SettingTypes.boolean,
      "name": "use_image_size",
      "default_value": False,
      "display_name": _("Use image size")
    },
    {
      "type": pgsetting.SettingTypes.boolean,
      "name": "only_visible_layers",
      "default_value": False,
      "display_name": _("Only visible layers")
    },
    {
      "type": pgsetting.SettingTypes.string,
      "name": "layer_filename_pattern",
      "default_value": "[layer name]",
      "display_name": _("Layer filename pattern"),
      "description": _("Layer filename pattern (empty string = layer name)"),
      "gui_type": None
    },
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "selected_layers",
      # key: image ID; value: set of selected layer IDs
      "default_value": collections.defaultdict(set),
      "display_name": _("Selected layers"),
      "pdb_type": None,
      "setting_sources": [pygimplib.config.SOURCE_SESSION]
    },
    {
      "type": pgsetting.SettingTypes.generic,
      "name": "selected_layers_persistent",
      # key: image file path; value: set of selected layer names
      "default_value": collections.defaultdict(set),
      "display_name": _("Selected layers"),
      "pdb_type": None,
      "setting_sources": [pygimplib.config.SOURCE_PERSISTENT]
    },
    {
      "type": pgsetting.SettingTypes.enumerated,
      "name": "overwrite_mode",
      "default_value": "rename_new",
      "items": [
        ("replace", _("_Replace"), pgoverwrite.OverwriteModes.REPLACE),
        ("skip", _("_Skip"), pgoverwrite.OverwriteModes.SKIP),
        ("rename_new", _("Rename _new file"), pgoverwrite.OverwriteModes.RENAME_NEW),
        ("rename_existing", _("Rename _existing file"),
         pgoverwrite.OverwriteModes.RENAME_EXISTING)],
      "display_name": _("Overwrite mode (non-interactive run mode only)")
    },
  ])
  
  settings["main/operations"].add([
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "insert_background_layers",
      "default_value": [builtin_operations.insert_background_layer, ["background"]],
      "enabled": False,
      "display_name": _("Insert background layers")
    },
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "insert_foreground_layers",
      "default_value": [builtin_operations.insert_background_layer, ["foreground"]],
      "enabled": False,
      "display_name": _("Insert foreground layers")
    },
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "inherit_transparency_from_layer_groups",
      "default_value": [builtin_operations.inherit_transparency_from_layer_groups],
      "enabled": False,
      "display_name": _("Inherit transparency from layer groups"),
    },
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "ignore_layer_modes",
      "default_value": [builtin_operations.ignore_layer_modes],
      "enabled": False,
      "display_name": _("Ignore layer modes")
    },
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "autocrop",
      "default_value": [builtin_operations.autocrop_layer],
      "enabled": False,
      "display_name": _("Autocrop")
    },
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "autocrop_background",
      "default_value": [builtin_operations.autocrop_tagged_layer, ["background"]],
      "enabled": False,
      "display_name": _("Autocrop background")
    },
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "autocrop_foreground",
      "default_value": [builtin_operations.autocrop_tagged_layer, ["foreground"]],
      "enabled": False,
      "display_name": _("Autocrop foreground")
    },
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "use_file_extensions_in_layer_names",
      "default_value": None,
      "enabled": False,
      "display_name": _("Use file extensions in layer names")
    },
  ])
  
  settings["main/constraints"].add([
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "only_layers_without_tags",
      "default_value": [builtin_constraints.has_no_tags],
      "enabled": False,
      "display_name": _("Only layers without tags")
    },
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "only_layers_with_tags",
      "default_value": [builtin_constraints.has_tags],
      "enabled": False,
      "display_name": _("Only layers with tags")
    },
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "only_layers_matching_file_extension",
      "default_value": [builtin_constraints.has_matching_default_file_extension],
      "enabled": False,
      "display_name": _("Only layers matching file extension")
    },
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "only_toplevel_layers",
      "default_value": [builtin_constraints.is_top_level],
      "enabled": False,
      "display_name": _("Only top-level layers")
    },
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "only_selected_layers",
      "default_value": None,
      "enabled": False,
      "display_name": _("Only layers selected in preview")
    }
  ])
  
  settings["main/constraints/include"].add([
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "include_layers",
      "default_value": [
        builtin_constraints.is_layer, [], {"subfilter": "layer_types"}],
      "enabled": True,
      "display_name": _("Include layers")
    },
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "include_layer_groups",
      "default_value": [
        builtin_constraints.is_nonempty_group, [], {"subfilter": "layer_types"}],
      "enabled": False,
      "display_name": _("Include layer groups")
    },
    {
      "type": pgsetting.SettingTypes.operation,
      "name": "include_empty_layer_groups",
      "default_value": [
        builtin_constraints.is_empty_group, [], {"subfilter": "layer_types"}],
      "enabled": False,
      "display_name": _("Include empty layer groups")
    }
  ])
  
  def on_use_file_extensions_in_layer_names_enabled_changed(
        use_file_extensions_in_layer_names, file_extension):
    if not use_file_extensions_in_layer_names.enabled:
      file_extension.error_messages[pgpath.FileValidatorErrorStatuses.IS_EMPTY] = ""
    else:
      file_extension.error_messages[pgpath.FileValidatorErrorStatuses.IS_EMPTY] = _(
        "You need to specify default file extension for layers with invalid "
        "or no extension.")
  
  settings["main/operations/use_file_extensions_in_layer_names"].connect_event(
    "enabled-changed",
    on_use_file_extensions_in_layer_names_enabled_changed,
    settings["main/file_extension"])
  
  return settings


#===============================================================================


def setup_image_ids_and_filepaths_settings(
      image_ids_dict_setting,
      image_filepaths_dict_setting,
      assign_image_id_to_filepath_func=None,
      assign_image_id_to_filepath_func_args=None,
      assign_filepath_to_image_id_func=None,
      assign_filepath_to_image_id_func_args=None):
  """
  Set up a connection between a setting with a dict of (image ID, value) pairs
  and a setting with a dict of (image file path, value) pairs. This function
  makes the two settings act like one - the former stored in a
  session-persistent setting source, and the latter in a persistent setting
  source.
  
  The rationale behind using two settings is that the IDs of images do not
  change during a GIMP session while the their file paths can.
  
  Optionally, instead of direct assignment of values between the settings, you
  may pass callbacks that convert values (separate callbacks for first setting
  value to second and vice versa) along with optional arguments. The callbacks
  must accept at least four arguments - current image ID, current image file
  path, the first setting and the second setting.
  """
  if assign_image_id_to_filepath_func is None:
    assign_image_id_to_filepath_func = _default_assign_image_id_to_filepath
  
  if assign_image_id_to_filepath_func_args is None:
    assign_image_id_to_filepath_func_args = []
  
  if assign_filepath_to_image_id_func is None:
    assign_filepath_to_image_id_func = _default_assign_image_filepath_to_id
  
  if assign_filepath_to_image_id_func_args is None:
    assign_filepath_to_image_id_func_args = []
  
  image_filepaths_dict_setting.connect_event(
    "after-load-group", _remove_invalid_image_filepaths)
  
  image_filepaths_dict_setting.connect_event(
    "before-save",
    _update_image_filepaths,
    image_ids_dict_setting,
    assign_image_id_to_filepath_func,
    assign_image_id_to_filepath_func_args)
  
  image_ids_dict_setting.connect_event(
    "after-load-group",
    _update_image_ids,
    image_filepaths_dict_setting,
    assign_filepath_to_image_id_func,
    assign_filepath_to_image_id_func_args)


def _default_assign_image_id_to_filepath(
      image_id, image_filepath, image_ids_setting, image_filepaths_setting):
  image_filepaths_setting.value[image_filepath] = image_ids_setting.value[image_id]


def _default_assign_image_filepath_to_id(
      image_id, image_filepath, image_ids_setting, image_filepaths_setting):
  image_ids_setting.value[image_id] = image_filepaths_setting.value[image_filepath]


def _remove_invalid_image_filepaths(image_filepaths_dict_setting):
  for image_filepath, values in list(image_filepaths_dict_setting.value.items()):
    if not(os.path.isfile(image_filepath) and values):
      del image_filepaths_dict_setting.value[image_filepath]


def _update_image_filepaths(
      image_filepaths_dict_setting,
      image_ids_dict_setting,
      assign_image_id_to_filepath_func,
      assign_image_id_to_filepath_func_args):
  current_images = gimp.image_list()
  
  for image in current_images:
    if image.ID in image_ids_dict_setting.value and image.filename:
      assign_image_id_to_filepath_func(
        image.ID,
        os.path.abspath(image.filename),
        image_ids_dict_setting,
        image_filepaths_dict_setting,
        *assign_image_id_to_filepath_func_args)


def _update_image_ids(
      image_ids_dict_setting,
      image_filepaths_dict_setting,
      assign_filepath_to_image_id_func,
      assign_filepath_to_image_id_func_args):
  current_images = gimp.image_list()
  
  for image in current_images:
    if (image.ID not in image_ids_dict_setting.value
        and image.filename in image_filepaths_dict_setting.value):
      assign_filepath_to_image_id_func(
        image.ID,
        os.path.abspath(image.filename),
        image_ids_dict_setting,
        image_filepaths_dict_setting,
        *assign_filepath_to_image_id_func_args)


def convert_set_of_layer_ids_to_names(
      image_id, image_filepath, image_ids_setting, image_filepaths_setting, layer_tree):
  image_filepaths_setting.value[image_filepath] = set(
    [layer_tree[layer_id].orig_name for layer_id in image_ids_setting.value[image_id]
     if layer_id in layer_tree])


def convert_set_of_layer_names_to_ids(
      image_id, image_filepath, image_ids_setting, image_filepaths_setting, layer_tree):
  image_ids_setting.value[image_id] = set(
    [layer_tree[layer_orig_name].item.ID
     for layer_orig_name in image_filepaths_setting.value[image_filepath]
     if layer_orig_name in layer_tree])


def convert_layer_id_to_name(
      image_id, image_filepath, image_ids_setting, image_filepaths_setting, layer_tree):
  layer_id = image_ids_setting.value[image_id]
  image_filepaths_setting.value[image_filepath] = (
    layer_tree[layer_id].orig_name if layer_id in layer_tree else None)


def convert_layer_name_to_id(
      image_id, image_filepath, image_ids_setting, image_filepaths_setting, layer_tree):
  layer_orig_name = image_filepaths_setting.value[image_filepath]
  image_ids_setting.value[image_id] = (
    layer_tree[layer_orig_name].item.ID if layer_orig_name in layer_tree else None)
