import unittest

from firebase_manager import config_patch_from_stream_message
from scheduler_gui import deep_update_config


class FirebaseStreamUpdateTests(unittest.TestCase):
    def test_leaf_update_is_wrapped_as_config_patch(self):
        message = {"event": "put", "path": "/hybrid", "data": True}

        self.assertEqual(
            config_patch_from_stream_message(message),
            {"hybrid": True},
        )

    def test_false_leaf_update_is_not_dropped(self):
        message = {"event": "put", "path": "/remote", "data": False}

        self.assertEqual(
            config_patch_from_stream_message(message),
            {"remote": False},
        )

    def test_nested_update_is_deep_merged_without_replacing_siblings(self):
        local_config = {
            "checkboxes": {
                "remote": True,
                "driversLicence": True,
            }
        }
        update = {"checkboxes": {"remote": False}}

        deep_update_config(local_config, update)

        self.assertEqual(
            local_config["checkboxes"],
            {"remote": False, "driversLicence": True},
        )


if __name__ == "__main__":
    unittest.main()
