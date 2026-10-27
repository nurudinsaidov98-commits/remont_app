"""Модульные тесты логики приложения (запуск: python -m unittest test_database)."""

import unittest

from database import Database, ValidationError


def sample(**over):
    data = {
        "client_name": "Иванов Иван Иванович",
        "client_phone": "+7 (928) 123-45-67",
        "device_type": "Ноутбук",
        "device_model": "Lenovo IdeaPad 3",
        "serial_number": "PF12AB34",
        "problem": "Не включается после падения",
        "priority": "Обычный",
    }
    data.update(over)
    return data


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def tearDown(self):
        self.db.close()

    def test_add_request_and_number(self):
        r1 = self.db.add_request(sample())
        r2 = self.db.add_request(sample())
        n1 = self.db.get_request(r1)["number"]
        n2 = self.db.get_request(r2)["number"]
        self.assertTrue(n1.endswith("-0001"))
        self.assertTrue(n2.endswith("-0002"))
        self.assertEqual(self.db.get_request(r1)["status"], "Новая")
        self.assertEqual(self.db.get_request(r1)["client_phone"], "+79281234567")

    def test_validation(self):
        with self.assertRaises(ValidationError):
            self.db.add_request(sample(client_name=""))
        with self.assertRaises(ValidationError):
            self.db.add_request(sample(client_phone="12345"))
        with self.assertRaises(ValidationError):
            self.db.add_request(sample(device_type="Холодильник"))
        with self.assertRaises(ValidationError):
            self.db.add_request(sample(problem="abc"))

    def test_status_and_history(self):
        rid = self.db.add_request(sample())
        self.db.change_status(rid, "В работе", "Начат ремонт")
        self.db.change_status(rid, "Выдана")
        r = self.db.get_request(rid)
        self.assertEqual(r["status"], "Выдана")
        self.assertIsNotNone(r["closed_at"])
        self.assertEqual(len(self.db.get_history(rid)), 3)
        with self.assertRaises(ValidationError):
            self.db.change_status(rid, "Потеряна")

    def test_master_assign(self):
        mid = self.db.add_master("Алиев Р.М.", "89280000000", "Ноутбуки")
        rid = self.db.add_request(sample())
        self.db.assign_master(rid, mid)
        self.assertEqual(self.db.get_request(rid)["master_name"], "Алиев Р.М.")
        self.assertEqual(self.db.get_masters()[0]["open_count"], 1)

    def test_filter_and_search(self):
        a = self.db.add_request(sample(client_name="Петров Пётр"))
        self.db.add_request(sample(client_name="Сидоров Сидор", priority="Срочный"))
        self.db.change_status(a, "Готова")
        self.assertEqual(len(self.db.get_requests(status="Готова")), 1)
        self.assertEqual(len(self.db.get_requests(search="Сидоров")), 1)
        # срочная заявка идёт первой
        self.assertEqual(self.db.get_requests()[0]["priority"], "Срочный")

    def test_cost_and_statistics(self):
        rid = self.db.add_request(sample())
        self.assertEqual(self.db.set_cost(rid, "2 500,50"), 2500.5)
        with self.assertRaises(ValidationError):
            self.db.set_cost(rid, "-5")
        self.db.change_status(rid, "Выдана")
        st = self.db.get_statistics()
        self.assertEqual(st["total"], 1)
        self.assertEqual(st["open"], 0)
        self.assertEqual(st["revenue"], 2500.5)

    def test_delete_cascade(self):
        rid = self.db.add_request(sample())
        self.db.delete_request(rid)
        self.assertIsNone(self.db.get_request(rid))
        self.assertEqual(self.db.get_history(rid), [])


if __name__ == "__main__":
    unittest.main()
