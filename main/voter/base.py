#!/usr/bin/env python

import abc
import logging

from main.component import base

logger = logging.getLogger(__name__)


class BaseVoter(base.BaseComponent):

    def __init__(self, _id, _config):
        super(BaseVoter, self).__init__(_id, _config)
        self._ldps = []
        self._smls = []
        self._has_receive_structure_from = set([])
        self._structures = []

    @abc.abstractmethod
    def elect_structure(self, structures):
        """Elect a structure or combine them to create a new one

        :param structures: list[numpy.ndarray] -- the list of structure
        learned over the samples.
        :returns: numpy.ndarray -- this should returns one of the structure
        or a combination.
        """
        pass

    def suggest_structure(self, who, structure):
        """Suggest to this voter the given structure.

        :param who: the sml making the proposal
        :param structure: the structure proposed
        :returns: numpy.ndarray
        """
        if who not in self._has_receive_structure_from:
            self._structures.append(structure)
            self._has_receive_structure_from.add(who)
            if len(self._has_receive_structure_from) == len(self._smls):
                candidate = self.elect_structure(self._structures)
                for tr in self._ldps:
                    tr.set_voter_output(candidate)
                # TODO: feed the sinks with candidate.
                self._has_receive_structure_from = set([])
            return
        logger.debug("SML algorithm '{}' already suggested a structure"
                     .format(who))

    def append_sml(self, l):
        """Append a SML to the list of SMLs

        This method is automatically called by the passed sml
        when this voter is connected to it and shouldn't be used directly.

        :param l: main.ml.base.BaseSML -- sml just connected to this.
        """
        self._smls.append(l)

    def remove_sml(self, l):
        """Remove a SML from the list of SMLs

        This method is automatically called by the passed sml
        when this voter is disconnected to it and shouldn't be used
        directly.

        :param l: main.ml.base.BaseSML -- sml just disconnected to this.
        """
        self._smls.remove(l)

    def append_ldp(self, ldp):
        """Add the LDP to the LDPs list"""
        self._ldps.append(ldp)

    def remove_ldp(self, ldp):
        """Remove the LDP from the LDPs list"""
        self._ldps.remove(ldp)
