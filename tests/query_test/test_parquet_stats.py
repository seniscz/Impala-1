# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import os
import pytest
import shlex
from subprocess import check_call

from tests.common.file_utils import (
  create_table_from_parquet, create_table_and_copy_files)
from tests.common.test_vector import ImpalaTestDimension
from tests.common.impala_test_suite import ImpalaTestSuite
from tests.util.filesystem_utils import get_fs_path

MT_DOP_VALUES = [0, 1, 2, 8]

class TestParquetStats(ImpalaTestSuite):
  """
  This suite tests runtime optimizations based on Parquet statistics.
  """

  @classmethod
  def get_workload(cls):
    return 'functional-query'

  @classmethod
  def add_test_dimensions(cls):
    super(TestParquetStats, cls).add_test_dimensions()
    cls.ImpalaTestMatrix.add_dimension(ImpalaTestDimension('mt_dop', *MT_DOP_VALUES))
    cls.ImpalaTestMatrix.add_constraint(
        lambda v: v.get_value('table_format').file_format == 'parquet')

  def test_parquet_stats(self, vector, unique_database):
    # The test makes assumptions about the number of row groups that are processed and
    # skipped inside a fragment, so we ensure that the tests run in a single fragment.
    vector.get_value('exec_option')['num_nodes'] = 1
    self.run_test_case('QueryTest/parquet-stats', vector, use_db=unique_database)

  def test_deprecated_stats(self, vector, unique_database):
    """Test that reading parquet files with statistics with deprecated 'min'/'max' fields
    works correctly. The statistics will be used for known-good types (boolean, integral,
    float) and will be ignored for all other types (string, decimal, timestamp)."""

    # We use CTAS instead of "create table like" to convert the partition columns into
    # normal table columns.
    create_table_and_copy_files(self.client, 'create table {db}.{tbl} stored as parquet '
                                             'as select * from functional.alltypessmall '
                                             'limit 0',
                                unique_database, 'deprecated_stats',
                                ['testdata/data/deprecated_statistics.parquet'])
    # The test makes assumptions about the number of row groups that are processed and
    # skipped inside a fragment, so we ensure that the tests run in a single fragment.
    vector.get_value('exec_option')['num_nodes'] = 1
    self.run_test_case('QueryTest/parquet-deprecated-stats', vector, unique_database)

  def test_invalid_stats(self, vector, unique_database):
    """IMPALA-6538" Test that reading parquet files with statistics with invalid
    'min_value'/'max_value' fields works correctly. 'min_value' and 'max_value' are both
    NaNs, therefore we need to ignore them"""
    create_table_from_parquet(self.client, unique_database, 'min_max_is_nan')
    self.run_test_case('QueryTest/parquet-invalid-minmax-stats', vector, unique_database)
