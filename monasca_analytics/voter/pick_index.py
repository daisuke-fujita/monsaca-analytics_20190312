#!/usr/bin/env python

# Copyright (c) 2016 Hewlett Packard Enterprise Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import math
import voluptuous

import monasca_analytics.banana.typeck.type_util as type_util
import monasca_analytics.component.params as params
from monasca_analytics.voter import base

import six


logger = logging.getLogger(__name__)


class PickIndexVoter(base.BaseVoter):

    def __init__(self, _id, _config):
        super(PickIndexVoter, self).__init__(_id, _config)
        self._index = _config["index"]

    @staticmethod
    def validate_config(_config):
        pick_schema = voluptuous.Schema({
            "module": voluptuous.And(
                six.string_types[0],
                lambda i: not any(c.isspace() for c in i)),
            "index": voluptuous.And(
                voluptuous.Or(float, int),
                lambda i: i >= 0 and math.ceil(i) == math.floor(i)
            )
        }, required=True)
        return pick_schema(_config)

    @staticmethod
    def get_default_config():
        return {
            "module": PickIndexVoter.__name__,
            "index": 0
        }

    @staticmethod
    def get_params():
        return [
            params.ParamDescriptor('index', type_util.Number(), 0),
        ]

    def elect_structure(self, structures):
        return structures[
            min(len(structures) - 1,
                self._index)]
