import os
import subprocess
import sys

from django.test import SimpleTestCase


class SecretKeySettingsTests(SimpleTestCase):
    def test_secret_key_is_loaded_from_environment(self):
        expected_secret = "test-secret-from-environment"
        environment = os.environ.copy()
        environment["SECRET_KEY"] = expected_secret

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from config.settings import SECRET_KEY; print(SECRET_KEY)",
            ],
            capture_output=True,
            check=False,
            env=environment,
            text=True,
        )

        self.assertEqual(result.returncode, 0, "Django settings were not imported")
        self.assertTrue(
            result.stdout.strip() == expected_secret,
            "Django settings ignored SECRET_KEY from the environment",
        )
