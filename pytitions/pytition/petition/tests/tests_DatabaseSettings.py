import importlib
import os
from unittest import mock

from django.test import SimpleTestCase

import pytition.settings.base


class DatabaseConnMaxAgeTest(SimpleTestCase):
    """DATABASE_CONN_MAX_AGE (BE-09): read from the environment, 0 by default."""

    def load(self, env):
        with mock.patch.dict(os.environ, env, clear=False):
            for name in ("USE_POSTGRESQL", "DATABASE_CONN_MAX_AGE"):
                if name not in env:
                    os.environ.pop(name, None)
            return importlib.reload(pytition.settings.base)

    def tearDown(self):
        importlib.reload(pytition.settings.base)

    def test_default_keeps_one_connection_per_request(self):
        base = self.load({"USE_POSTGRESQL": "1"})
        self.assertEqual(base.DATABASE_CONN_MAX_AGE, 0)
        self.assertEqual(base.DATABASES["default"]["CONN_MAX_AGE"], 0)

    def test_value_from_environment(self):
        base = self.load({"USE_POSTGRESQL": "1", "DATABASE_CONN_MAX_AGE": "60"})
        self.assertEqual(base.DATABASE_CONN_MAX_AGE, 60)
        self.assertEqual(base.DATABASES["default"]["CONN_MAX_AGE"], 60)
        self.assertTrue(base.DATABASES["default"]["CONN_HEALTH_CHECKS"])

