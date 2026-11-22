"""Check independent checkpoint execution using isolated, synthetic fixtures."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import dashboard


class DashboardIndependenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cwd = Path.cwd()
        os.chdir(self.root)
        self.root_patch = patch.object(dashboard, "ROOT", self.root)
        self.root_patch.start()
        for state in dashboard.STATE["checkpoints"].values():
            state.update(busy=False, message="Ready to test")
        dashboard.STATE["cloud"] = {"error": "VM deliberately unavailable"}

    def tearDown(self):
        self.root_patch.stop()
        os.chdir(self.cwd)
        self.temp.cleanup()

    def test_checkpoint1_works_while_watch_is_busy_and_vm_unavailable(self):
        # No device or previous checkpoint result is present.
        fixture = ([[0.0] * 128] * 6, 0, "WALKING")
        dashboard.DEVICE_LOCK.acquire()
        try:
            with patch("har_dataset.UCIHARSignals", return_value=[fixture]), \
                 patch("har_gemini.classify", return_value={"label": "WALKING", "output": "WALKING"}):
                dashboard.perform("unreachable", "uci", None, None)
            record = json.loads((self.root / "results/checkpoint1_demo.jsonl").read_text())
            self.assertEqual(record["shape"], [6, 128])
            self.assertEqual(record["cot"]["label"], record["direct"]["label"])
        finally:
            dashboard.DEVICE_LOCK.release()

    def test_checkpoint2_does_not_need_cloud_or_checkpoint1(self):
        result = {"label": "SITTING", "oled_response": "Displaying: SITTING"}
        dashboard.DEVICE_LOCK.acquire()
        with patch("lab6_dt2811_ms7635_rnb2135_check2_app.classify_HAR", return_value=json.dumps(result)) as capture, \
             patch.object(dashboard.time, "sleep"), patch.dict(sys.modules, {"har_normwear": None}):
            dashboard.perform("watch", "capture", "SITTING", "wrist")
        capture.assert_called_once_with("watch", truth="SITTING", location="wrist")
        self.assertIn("SITTING", dashboard.STATE["checkpoints"]["2"]["message"])
        self.assertFalse(dashboard.DEVICE_LOCK.locked())

    def check_cloud_checkpoint(self, action, response, expected_command):
        dashboard.DEVICE_LOCK.acquire()
        with patch("record_cloud_demo.SmartwatchClient") as client, \
             patch.dict(sys.modules, {"har_gemini": None, "har_normwear": None}):
            client.return_value.send_command.return_value = response
            dashboard.perform("watch", action, None, None)
        client.return_value.send_command.assert_called_once_with(expected_command)
        records = [json.loads(r) for r in (self.root / "results/esp32_cloud_demo.jsonl").read_text().splitlines()]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["stage"], action)
        self.assertTrue(records[0]["ok"])
        self.assertFalse(dashboard.DEVICE_LOCK.locked())

    def test_checkpoint3_needs_no_gemini_or_inference(self):
        self.check_cloud_checkpoint("storage", {"id": "fixture-storage", "stored": True}, "store_HAR")

    def test_checkpoint4_can_run_first_without_storage_or_gemini(self):
        self.check_cloud_checkpoint("prediction", {"id": "fixture-prediction", "label": "STANDING"}, "classify_HAR")


if __name__ == "__main__":
    unittest.main(verbosity=2)
