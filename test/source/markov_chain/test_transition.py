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

import monasca_analytics.source.markov_chain.prob_checks as pck
import monasca_analytics.source.markov_chain.state_check as dck
import monasca_analytics.source.markov_chain.transition as t
from test.util_for_testing import MonanasTestCase


class DummyState(object):

    def __init__(self, state=0):
        self.state = state
        self.dependencies = []


class MarkovChainTransitionsTest(MonanasTestCase):

    def setUp(self):
        super(MarkovChainTransitionsTest, self).setUp()

    def tearDown(self):
        super(MarkovChainTransitionsTest, self).tearDown()

    def test_first_order_dep_check(self):
        state = DummyState()
        state.dependencies.append(DummyState(1))
        dc = dck.DepCheck(dck.EqCheck(1))
        self.assertTrue(dc(state))
        state = DummyState()
        self.assertFalse(dc(state))
        state = DummyState()
        state.dependencies.append(DummyState(2))
        self.assertFalse(dc(state))

    def test_second_order_dep_check(self):
        state = DummyState()
        state1 = DummyState()
        state.dependencies.append(state1)
        state1.dependencies.append(DummyState(1))
        dc = dck.DepCheck(dck.DepCheck(dck.EqCheck(1)))
        self.assertTrue(dc(state))
        state = DummyState()
        self.assertFalse(dc(state))
        self.assertFalse(dc(state1))

    def test_combiner_and_dep_check(self):
        state = DummyState()
        state1 = DummyState(1)
        state.dependencies.append(state1)
        state1.dependencies.append(DummyState(2))
        dc = dck.AndCheck(c1=dck.DepCheck(dck.EqCheck(1)),
                          c2=dck.DepCheck(dck.DepCheck(dck.EqCheck(2))))
        self.assertTrue(dc(state))
        self.assertFalse(dc(state1))
        state1.state = 2
        self.assertFalse(dc(state))
        state1.state = 1
        state1.dependencies[0].state = 1
        self.assertFalse(dc(state))
        state = DummyState()
        self.assertFalse(dc(state))

    def test_combiner_or_dep_check(self):
        state = DummyState()
        state1 = DummyState(1)
        state.dependencies.append(state1)
        state1.dependencies.append(DummyState(2))
        dc = dck.OrCheck(c1=dck.DepCheck(dck.EqCheck(1)),
                         c2=dck.DepCheck(dck.DepCheck(dck.EqCheck(2))))
        self.assertTrue(dc(state))
        self.assertFalse(dc(state1))
        state1.dependencies[0].state = 1
        self.assertTrue(dc(state))
        self.assertTrue(dc(state1))
        state1.state = 2
        self.assertFalse(dc(state))
        state = DummyState()
        self.assertFalse(dc(state))

    def test_prob_check(self):
        pc = pck.ProbCheck(0.5)
        i = 0
        while i < 30:
            if pc(0):
                break
            i += 1
        self.assertTrue(i < 30)

    def test_prob_check_interpolate(self):
        pc = pck.ProbCheck({0: 0.0, 1: 0.0, 24: 1.0})
        self.assertFalse(pc(0))
        self.assertFalse(pc(1))
        self.assertTrue(pc(24))
        i = 0
        while i < 30:
            if pc(12):
                break
            i += 1
        self.assertTrue(i < 30)

    def test_transition(self):
        tr = t.Transition(0, 1, pck.ProbCheck(1.0))
        state = DummyState(0)
        self.assertTrue(tr(state, 1))
        self.assertEqual(state.state, 1)
        state = DummyState(2)
        self.assertFalse(tr(state, 1))
        self.assertEqual(state.state, 2)

    def test_transition_with_true_check(self):
        tr = t.Transition(0, 1, pck.NoProbCheck(), dck.TrueCheck())
        state = DummyState(0)
        self.assertFalse(tr(state, 1))
        state1 = DummyState(123456)
        state.dependencies.append(state1)
        self.assertTrue(tr(state, 1))
        self.assertEqual(state.state, 1)

    def test_markov_chain(self):
        tr1 = t.Transition(0, 1, pck.ProbCheck(1.0))
        tr2 = t.Transition(1, 2, pck.ProbCheck(1.0))
        mc = t.MarkovChain([tr1, tr2])
        state1 = DummyState(0)
        state2 = DummyState(1)
        mc.apply_on(state1, 1)
        mc.apply_on(state2, 1)
        self.assertEqual(state1.state, 1)
        self.assertEqual(state2.state, 2)
        mc.apply_on(state1, 1)
        mc.apply_on(state2, 1)
        self.assertEqual(state1.state, 2)
        self.assertEqual(state2.state, 2)
