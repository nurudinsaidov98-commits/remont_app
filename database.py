"""
Модуль работы с базой данных системы регистрации и обработки заявок
на ремонт компьютерной техники.

Хранение данных реализовано на SQLite. Модуль не зависит от интерфейса,
поэтому его можно проверять отдельно (см. test_database.py).
"""

import re
import sqlite3
from datetime import datetime

# Справочники системы
STATUSES = [
    "Новая",
    "Диагностика",
    "В работе",
    "Ожидает запчасти",
    "Готова",
    "Выдана",
    "Отменена",
]
# Статусы, при которых заявка считается закрытой
CLOSED_STATUSES = ("Выдана", "Отменена")

DEVICE_TYPES = [
    "Ноутбук",
    "Системный блок",
    "Моноблок",
    "Монитор",
    "Принтер / МФУ",
    "Планшет",
    "Другое",
]

PRIORITIES = ["Обычный", "Срочный"]

DATE_FORMAT = "%d.%m.%Y %H:%M"

PHONE_RE = re.compile(r"^(\+7|8)\d{10}$")


class ValidationError(Exception):
    """Ошибка проверки введённых данных."""


def now_str():
    """Текущие дата и время в формате системы."""
    return datetime.now().strftime(DATE_FORMAT)


def normalize_phone(phone):
    """Убирает из номера пробелы, скобки и дефисы."""
    return re.sub(r"[\s()\-]", "", phone or "")


def validate_request(data):
    """Проверяет поля заявки. Возвращает очищенные данные или вызывает ValidationError."""
    errors = []
    client_name = (data.get("client_name") or "").strip()
    phone = normalize_phone(data.get("client_phone"))
    device_type = (data.get("device_type") or "").strip()
    device_model = (data.get("device_model") or "").strip()
    problem = (data.get("problem") or "").strip()
    priority = (data.get("priority") or "Обычный").strip()

    if len(client_name) < 2:
        errors.append("Укажите ФИО клиента")
    if not PHONE_RE.match(phone):
        errors.append("Телефон в формате +7XXXXXXXXXX или 8XXXXXXXXXX")
    if device_type not in DEVICE_TYPES:
        errors.append("Выберите тип устройства")
    if len(problem) < 5:
        errors.append("Опишите неисправность (не менее 5 символов)")
    if priority not in PRIORITIES:
        errors.append("Неверный приоритет")

    if errors:
        raise ValidationError("\n".join(errors))

    return {
        "client_name": client_name,
        "client_phone": phone,
        "device_type": device_type,
        "device_model": device_model,
        "serial_number": (data.get("serial_number") or "").strip(),
        "problem": problem,
        "priority": priority,
    }


class Database:
    """Класс доступа к данным: заявки, мастера, история изменений."""

    def __init__(self, path="remont.db"):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def close(self):
        self.conn.close()

    # ---------- структура БД ----------
    def create_tables(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS masters (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL,
                phone          TEXT,
                specialization TEXT,
                active         INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS requests (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                number        TEXT UNIQUE NOT NULL,
                created_at    TEXT NOT NULL,
                client_name   TEXT NOT NULL,
                client_phone  TEXT NOT NULL,
                device_type   TEXT NOT NULL,
                device_model  TEXT,
                serial_number TEXT,
                problem       TEXT NOT NULL,
                priority      TEXT NOT NULL DEFAULT 'Обычный',
                status        TEXT NOT NULL DEFAULT 'Новая',
                master_id     INTEGER REFERENCES masters(id) ON DELETE SET NULL,
                cost          REAL NOT NULL DEFAULT 0,
                closed_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id  INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
                changed_at  TEXT NOT NULL,
                status      TEXT NOT NULL,
                comment     TEXT
            );
            """
        )
        self.conn.commit()

    # ---------- мастера ----------
    def add_master(self, name, phone="", specialization=""):
        name = (name or "").strip()
        if len(name) < 2:
            raise ValidationError("Укажите ФИО мастера")
        cur = self.conn.execute(
            "INSERT INTO masters (name, phone, specialization) VALUES (?, ?, ?)",
            (name, normalize_phone(phone), (specialization or "").strip()),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_masters(self, only_active=True):
        sql = """
            SELECT m.*,
                   (SELECT COUNT(*) FROM requests r
                     WHERE r.master_id = m.id
                       AND r.status NOT IN ('Выдана', 'Отменена')) AS open_count
              FROM masters m
        """
        if only_active:
            sql += " WHERE m.active = 1"
        sql += " ORDER BY m.name"
        return [dict(r) for r in self.conn.execute(sql)]

    def deactivate_master(self, master_id):
        self.conn.execute("UPDATE masters SET active = 0 WHERE id = ?", (master_id,))
        self.conn.commit()

    # ---------- заявки ----------
    def _next_number(self):
        year = datetime.now().year
        prefix = f"РЕМ-{year}-"
        row = self.conn.execute(
            "SELECT number FROM requests WHERE number LIKE ? ORDER BY id DESC LIMIT 1",
            (prefix + "%",),
        ).fetchone()
        last = int(row["number"].split("-")[-1]) if row else 0
        return f"{prefix}{last + 1:04d}"

    def add_request(self, data):
        clean = validate_request(data)
        number = self._next_number()
        created = now_str()
        cur = self.conn.execute(
            """INSERT INTO requests (number, created_at, client_name, client_phone,
                   device_type, device_model, serial_number, problem, priority)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                number, created, clean["client_name"], clean["client_phone"],
                clean["device_type"], clean["device_model"], clean["serial_number"],
                clean["problem"], clean["priority"],
            ),
        )
        request_id = cur.lastrowid
        self._add_history(request_id, "Новая", "Заявка зарегистрирована")
        self.conn.commit()
        return request_id

    def update_request(self, request_id, data):
        clean = validate_request(data)
        self.conn.execute(
            """UPDATE requests SET client_name=?, client_phone=?, device_type=?,
                   device_model=?, serial_number=?, problem=?, priority=?
               WHERE id=?""",
            (
                clean["client_name"], clean["client_phone"], clean["device_type"],
                clean["device_model"], clean["serial_number"], clean["problem"],
                clean["priority"], request_id,
            ),
        )
        self.conn.commit()

    def get_request(self, request_id):
        row = self.conn.execute(
            """SELECT r.*, m.name AS master_name
                 FROM requests r LEFT JOIN masters m ON m.id = r.master_id
                WHERE r.id = ?""",
            (request_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_requests(self, status=None, search=""):
        sql = """SELECT r.*, m.name AS master_name
                   FROM requests r LEFT JOIN masters m ON m.id = r.master_id
                  WHERE 1=1"""
        params = []
        if status:
            sql += " AND r.status = ?"
            params.append(status)
        search = (search or "").strip()
        if search:
            like = f"%{search}%"
            sql += """ AND (r.number LIKE ? OR r.client_name LIKE ?
                            OR r.client_phone LIKE ? OR r.device_model LIKE ?)"""
            params += [like, like, like, like]
        # Срочные выше, затем новые сверху
        sql += " ORDER BY (r.priority = 'Срочный') DESC, r.id DESC"
        return [dict(r) for r in self.conn.execute(sql, params)]

    def change_status(self, request_id, status, comment=""):
        if status not in STATUSES:
            raise ValidationError("Неизвестный статус")
        closed_at = now_str() if status in CLOSED_STATUSES else None
        self.conn.execute(
            "UPDATE requests SET status = ?, closed_at = ? WHERE id = ?",
            (status, closed_at, request_id),
        )
        self._add_history(request_id, status, comment)
        self.conn.commit()

    def assign_master(self, request_id, master_id):
        self.conn.execute(
            "UPDATE requests SET master_id = ? WHERE id = ?", (master_id, request_id)
        )
        req = self.get_request(request_id)
        self._add_history(request_id, req["status"], f"Назначен мастер: {req['master_name']}")
        self.conn.commit()

    def set_cost(self, request_id, cost):
        try:
            value = float(str(cost).replace(",", ".").replace(" ", ""))
        except ValueError:
            raise ValidationError("Стоимость должна быть числом")
        if value < 0:
            raise ValidationError("Стоимость не может быть отрицательной")
        self.conn.execute("UPDATE requests SET cost = ? WHERE id = ?", (value, request_id))
        self.conn.commit()
        return value

    def delete_request(self, request_id):
        self.conn.execute("DELETE FROM requests WHERE id = ?", (request_id,))
        self.conn.commit()

    # ---------- история ----------
    def _add_history(self, request_id, status, comment=""):
        self.conn.execute(
            "INSERT INTO history (request_id, changed_at, status, comment) VALUES (?, ?, ?, ?)",
            (request_id, now_str(), status, (comment or "").strip()),
        )

    def add_comment(self, request_id, comment):
        comment = (comment or "").strip()
        if not comment:
            raise ValidationError("Комментарий пуст")
        req = self.get_request(request_id)
        self._add_history(request_id, req["status"], comment)
        self.conn.commit()

    def get_history(self, request_id):
        return [
            dict(r)
            for r in self.conn.execute(
                "SELECT * FROM history WHERE request_id = ? ORDER BY id", (request_id,)
            )
        ]

    # ---------- статистика ----------
    def get_statistics(self):
        by_status = {s: 0 for s in STATUSES}
        for row in self.conn.execute("SELECT status, COUNT(*) AS c FROM requests GROUP BY status"):
            by_status[row["status"]] = row["c"]

        total = sum(by_status.values())
        open_count = total - by_status["Выдана"] - by_status["Отменена"]
        revenue = self.conn.execute(
            "SELECT COALESCE(SUM(cost), 0) FROM requests WHERE status = 'Выдана'"
        ).fetchone()[0]

        # Средний срок ремонта (в днях) по выданным заявкам
        days = []
        for row in self.conn.execute(
            "SELECT created_at, closed_at FROM requests WHERE status = 'Выдана' AND closed_at IS NOT NULL"
        ):
            start = datetime.strptime(row["created_at"], DATE_FORMAT)
            end = datetime.strptime(row["closed_at"], DATE_FORMAT)
            days.append((end - start).total_seconds() / 86400)
        avg_days = round(sum(days) / len(days), 1) if days else 0

        by_device = {}
        for row in self.conn.execute(
            "SELECT device_type, COUNT(*) AS c FROM requests GROUP BY device_type ORDER BY c DESC"
        ):
            by_device[row["device_type"]] = row["c"]

        return {
            "total": total,
            "open": open_count,
            "by_status": by_status,
            "by_device": by_device,
            "revenue": revenue,
            "avg_days": avg_days,
        }
