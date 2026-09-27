import unittest
from pathlib import Path
from copy import deepcopy
from streamlit.testing.v1 import AppTest
from network_model import load_data, solve, metrics


class NetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data = load_data()

    def test_four_optima(self):
        for case in self.data['scenarios']:
            with self.subTest(case=case['id']):
                solution = solve(self.data, case)
                result = metrics(self.data, solution)
                self.assertEqual(result['errors'], [])
                self.assertAlmostEqual(result['total'], case['workbookCost'], places=3)

    def test_fixed_base_and_delay(self):
        for case in self.data['scenarios'][1:3]:
            result = solve(self.data, case, self.data['scenarios'][0]['modules'])
            expected = metrics(self.data, case['robustness']['solution'])['total']
            self.assertAlmostEqual(metrics(self.data, result)['total'], expected, places=3)
        with self.assertRaisesRegex(ValueError, 'No feasible'):
            solve(self.data, self.data['scenarios'][3], self.data['scenarios'][0]['modules'])

    def test_invalid_and_zero_interest(self):
        case = deepcopy(self.data['scenarios'][0])
        case['demand'] = [0] * 12
        with self.assertRaisesRegex(ValueError, 'positive total'): solve(self.data, case)
        case = deepcopy(self.data['scenarios'][0])
        case['rate'] = 0
        self.assertEqual(metrics(self.data, solve(self.data, case))['errors'], [])

    def test_streamlit_component_boot(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'streamlit_app.py')).run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.get('component_instance')), 1)


if __name__ == '__main__': unittest.main()
