import unittest

import parameterized

from src import placeholders


class TestPlaceHolderSetting(unittest.TestCase):
  
  @parameterized.parameterized.expand([
    ('placeholder', placeholders.PlaceholderSetting, []),
    ('image_placeholder', placeholders.PlaceholderImageSetting, ['current_image']),
  ])
  def test_get_allowed_placeholder_names(
        self, test_case_suffix, placeholder_setting_type, expected_result):
    self.assertListEqual(
      placeholder_setting_type.get_allowed_placeholder_names(), expected_result)
  
  @parameterized.parameterized.expand([
    ('placeholder', placeholders.PlaceholderSetting, 0),
    ('image_placeholder', placeholders.PlaceholderImageSetting, 1),
  ])
  def test_get_allowed_placeholders(
        self, test_case_suffix, placeholder_setting_type, expected_length):
    self.assertEqual(len(placeholder_setting_type.get_allowed_placeholders()), expected_length)
