import json
from logging import config as log_cfg
import os
import unittest

from main.exception import monanas as err
import main.monanas as mnn
import main.spark.driver as driver
import main.util.common_util as cu
from test.mocks import sml_mocks
from test.mocks import spark_mocks


class MonanasTest(unittest.TestCase):

    def setup_logging(self):
        current_dir = os.path.dirname(__file__)
        logging_config_file = os.path.join(current_dir,
                                           "resources/logging.json")
        with open(logging_config_file, "rt") as f:
            config = json.load(f)
        log_cfg.dictConfig(config)

    def setUp(self):
        """
        Keep a copy of the original functions that will be mocked, then
        mock them, reset variables, and initialize ML_Framework.
        """
        self.setup_logging()
        self._backup_functions()
        self._mock_functions()
        sml_mocks.sml_mocks.reset()
        self.init_sml_config()

    def tearDown(self):
        """
        Restore the potentially mocked functions to the original ones
        """
        self._restore_functions()

    def _backup_functions(self):
        self.original_kill = mnn.os.kill
        self.original_get_class_by_name = cu.get_class_by_name
        self.original_SparkContext = driver.pyspark.SparkContext
        self.original_StreamingContext = driver.streaming.StreamingContext
        self.original_Aggregator = driver.agg.Aggregator

    def _restore_functions(self):
        cu.get_class_by_name = self.original_get_class_by_name
        mnn.os.kill = self.original_kill
        driver.pyspark.SparkContext = self.original_SparkContext
        driver.streaming.StreamingContext = self.original_StreamingContext
        driver.agg.Aggregator = self.original_Aggregator

    def _mock_functions(self):
        cu.get_class_by_name = sml_mocks.mock_get_class_by_name
        mnn.os.kill = sml_mocks.mock_kill
        driver.pyspark.SparkContext = spark_mocks.MockSparkContext
        driver.streaming.StreamingContext = spark_mocks.MockStreamingContext
        driver.agg.Aggregator = sml_mocks.MockClass_aggr_module

    def init_sml_config(self):
        """
        Initialize the ML_Framework object with the test_json config
        """
        current_dir = os.path.dirname(__file__)
        test_json_file = os.path.join(current_dir, "resources/test_json.json")
        config = cu.parse_json_file(test_json_file)
        self.mlf = mnn.Monanas(config)

    def test_is_streaming(self):
        self.assertFalse(self.mlf.is_streaming())
        self.mlf._is_streaming = True
        self.assertTrue(self.mlf.is_streaming())
        self.mlf._is_streaming = False
        self.assertFalse(self.mlf.is_streaming())

    def test_start_streaming_no_param(self):
        self.mlf.start_streaming()
        self.assertTrue(self.mlf.is_streaming())

    def assert_stopped_streaming_state(self, ssc=None):
        if ssc:
            self.assertEqual(1, ssc.stopped_cnt)
        self.assertFalse(self.mlf.is_streaming())

    def test_stop_streaming(self):
        self.mlf.start_streaming()
        self.mlf.stop_streaming()

    def test_stop_streaming_no_streaming(self):
        self.mlf.start_streaming()
        self.mlf.stop_streaming()
        self.assertRaises(err.MonanasAlreadyStoppedStreaming,
                          self.mlf.stop_streaming)

    def test_stop_streaming_and_terminate_from_init_state(self):
        self.assertFalse(sml_mocks.sml_mocks.killed)
        self.mlf.stop_streaming_and_terminate()
        self.assertTrue(sml_mocks.sml_mocks.killed)
        self.assert_stopped_streaming_state()

    def test_stop_streaming_and_terminate_from_streaming_state(self):
        self.assertFalse(sml_mocks.sml_mocks.killed)
        self.mlf.start_streaming()
        self.mlf.stop_streaming_and_terminate()
        self.assertTrue(sml_mocks.sml_mocks.killed)

    def test_stop_streaming_and_terminate_from_stopped_state(self):
        self.assertFalse(sml_mocks.sml_mocks.killed)
        self.mlf.start_streaming()
        self.mlf.stop_streaming()
        self.mlf.stop_streaming_and_terminate()
        self.assertTrue(sml_mocks.sml_mocks.killed)
