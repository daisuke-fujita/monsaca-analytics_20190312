#!/usr/bin/env python

import abc
import logging

import numpy as np

logger = logging.getLogger(__name__)


class Aggregator(object):
    """Aggregator that accumulates data and sends it to SMLs"""
    __metaclass__ = abc.ABCMeta

    def __init__(self, driver):
        """BaseAggregator constructor.

        :param driver: main.spark.driver.DriverExecutor -- The driver that
        manages spark
        """
        self._combined_stream = None
        self._smls = []
        self._samples = None
        self._driver = driver

    def append_sml(self, l):
        """The given sml will now be owned and receive the accumulated data

        :param l: main.sml.base.BaseSML -- the sml to connect to.
        """
        self._smls.append(l)

    def accumulate_dstream_samples(self, stream):
        """Accumulate the samples coming from a stream

        The first time this function is called it sets the _aggregated_stream
        to be the _stream parameter, and the _output_stream to be the
        transformed version (according to the logic implemented by children
        of this class) of the _aggregated_stream.
        The consecutive times, it joins the _stream to the aggregated stream,
        so at runtime _aggregated_stream is a funnel of all streams passed
        to this function.

        :param stream: pyspark.streaming.DStream -- stream to be aggregated
        """
        if self._combined_stream is None:
            self._combined_stream = stream
        else:
            self._combined_stream = self._combined_stream.union(stream)

    def prepare_final_accumulate_stream_step(self):
        """Accumulate each sample into an ndarray.

        This can only be called once accumulate_dstream_samples has been
        called on every stream that need to be accumulated together.
        """
        if self._combined_stream is not None:
            self._combined_stream.foreachRDD(
                lambda _, rdd: self._processRDD(rdd))

    def _processRDD(self, rdd):
        """Process the RDD

        :param rdd: pyspark.RDD
        """
        if len(self._smls) > 0:
            rdd_entries = rdd.collect()
            for rdd_entry in rdd_entries:
                if self._samples is not None:
                    self._samples = np.vstack([self._samples, rdd_entry])
                else:
                    self._samples = rdd_entry
            self._check_smls()
        else:
            self._samples = None

    def _check_smls(self):
        """Detect if a SML is ready to learn from the set.

        If it is, for simplicity we remove it from the list of SMLs.
        """
        if self._samples is None:
            return

        def has_learn(sml, samples):
            nb_samples = samples.shape[0]
            tst = sml.number_of_samples_required() <= nb_samples
            if tst:
                sml.learn(samples)
            return not tst

        logger.debug(self._samples.shape)
        self._smls[:] = [l for l in self._smls if has_learn(l, self._samples)]
        if len(self._smls) == 0:
            self._driver.move_to_phase2()
