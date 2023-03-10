# Copyright 2018 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Executes Keras benchmarks and accuracy tests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

from absl import flags
from absl.testing import flagsaver
import tensorflow as tf  # pylint: disable=g-bad-import-order

FLAGS = flags.FLAGS


class KerasBenchmark(object):
  """Base benchmark class with methods to simplify testing."""
  local_flags = None

  def __init__(self, output_dir=None, default_flags=None, flag_methods=None):
    self.oss_report_object = None
    self.output_dir = output_dir
    self.default_flags = default_flags or {}
    self.flag_methods = flag_methods or {}

  def _get_model_dir(self, folder_name):
    return os.path.join(self.output_dir, folder_name)

  def _setup(self):
    """Sets up and resets flags before each test."""
    tf.logging.set_verbosity(tf.logging.DEBUG)
    if KerasBenchmark.local_flags is None:
      for flag_method in self.flag_methods:
        flag_method()
      # Loads flags to get defaults to then override. List cannot be empty.
      flags.FLAGS(['foo'])
      # Overrides flag values with defaults for the class of tests.
      for k, v in self.default_flags.items():
        setattr(FLAGS, k, v)
      saved_flag_values = flagsaver.save_flag_values()
      KerasBenchmark.local_flags = saved_flag_values
    else:
      flagsaver.restore_flag_values(KerasBenchmark.local_flags)

  def fill_report_object(self, stats, top_1_max=None, top_1_min=None,
                         log_steps=None, total_batch_size=None, warmup=1):
    """Fills report object to report results.

    Args:
      stats: dict returned from keras models with known entries.
      top_1_max: highest passing level for top_1 accuracy.
      top_1_min: lowest passing level for top_1 accuracy.
      log_steps: How often the log was created for stats['step_timestamp_log'].
      total_batch_size: Global batch-size.
      warmup: number of entries in stats['step_timestamp_log'] to ignore.
    """
    if self.oss_report_object:

      if 'accuracy_top_1' in stats:
        self.oss_report_object.add_top_1(stats['accuracy_top_1'],
                                         expected_min=top_1_min,
                                         expected_max=top_1_max)
        self.oss_report_object.add_other_quality(
            stats['training_accuracy_top_1'],
            'top_1_train_accuracy')
      if (warmup and
          'step_timestamp_log' in stats and
          len(stats['step_timestamp_log']) > warmup):
        # first entry in the time_log is start of step 1. The rest of the
        # entries are the end of each step recorded
        time_log = stats['step_timestamp_log']
        elapsed = time_log[-1].timestamp - time_log[warmup].timestamp
        num_examples = (total_batch_size * log_steps * (len(time_log)-warmup-1))
        examples_per_sec = num_examples / elapsed
        self.oss_report_object.add_examples_per_second(examples_per_sec)

      if 'avg_exp_per_second' in stats:
        self.oss_report_object.add_result(stats['avg_exp_per_second'],
                                          'avg_exp_per_second',
                                          'exp_per_second')
    else:
      raise ValueError('oss_report_object has not been set.')
