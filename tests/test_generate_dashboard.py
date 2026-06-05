import unittest
from datetime import date

from shed_agent.config import AgentConfig
from shed_agent.generate_dashboard import generate_dashboard_html, observation_window
from shed_agent.sample_data import build_sample_observations


class GenerateDashboardTests(unittest.TestCase):
    def test_observation_window_uses_configured_start_date(self):
        config = AgentConfig(observation_window_start_date="2026-06-02", observation_window_days=7)

        start, end = observation_window(config, date(2026, 6, 3))

        self.assertEqual(start.isoformat(), "2026-06-02")
        self.assertEqual(end.isoformat(), "2026-06-08")

    def test_dashboard_contains_key_sections(self):
        config = AgentConfig(observation_window_start_date="2026-06-02", observation_window_days=7)
        html = generate_dashboard_html(build_sample_observations(config), config)

        self.assertIn("Shed Demand Listener", html)
        self.assertIn("当前建议", html)
        self.assertIn("一句话结论", html)
        self.assertIn("当前主要风险", html)
        self.assertIn("重点目标候选", html)
        self.assertIn("邻近机会观察清单", html)
        self.assertIn("2026-06-02 至 2026-06-08", html)


if __name__ == "__main__":
    unittest.main()
