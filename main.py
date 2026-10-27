"""
Система регистрации и обработки заявок на ремонт компьютерной техники.
Мобильное приложение для Android (Python + Kivy + KivyMD).

Точка входа приложения. Логика хранения данных вынесена в database.py.
"""

import os

from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.utils import platform

from kivymd.app import MDApp
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem, ThreeLineListItem, TwoLineListItem
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.textfield import MDTextField

from database import (
    Database, ValidationError, STATUSES, DEVICE_TYPES, PRIORITIES,
)

KV = """
<MainScreen>:
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            id: top_bar
            title: "Сервис-центр"
            elevation: 2

        MDBottomNavigation:
            id: bottom_nav
            selected_color_background: app.theme_cls.primary_light
            text_color_active: app.theme_cls.primary_dark

            MDBottomNavigationItem:
                name: "requests"
                text: "Заявки"
                icon: "clipboard-list-outline"
                on_tab_press: root.refresh_requests()

                MDFloatLayout:
                    MDBoxLayout:
                        orientation: "vertical"
                        padding: dp(8)
                        spacing: dp(4)

                        MDBoxLayout:
                            size_hint_y: None
                            height: dp(64)
                            spacing: dp(8)

                            MDTextField:
                                id: search_field
                                hint_text: "Поиск: номер, клиент, телефон"
                                mode: "rectangle"
                                on_text: root.refresh_requests()

                            MDIconButton:
                                icon: "filter-variant"
                                pos_hint: {"center_y": .5}
                                on_release: root.open_filter_menu(self)

                        MDLabel:
                            id: filter_label
                            text: "Все заявки"
                            size_hint_y: None
                            height: dp(24)
                            theme_text_color: "Secondary"
                            font_style: "Caption"

                        ScrollView:
                            MDList:
                                id: request_list

                    MDFloatingActionButton:
                        icon: "plus"
                        pos_hint: {"right": .95, "y": .03}
                        on_release: app.open_form()

            MDBottomNavigationItem:
                name: "masters"
                text: "Мастера"
                icon: "account-wrench-outline"
                on_tab_press: root.refresh_masters()

                MDBoxLayout:
                    orientation: "vertical"
                    padding: dp(8)
                    spacing: dp(8)

                    ScrollView:
                        MDList:
                            id: master_list

                    MDRaisedButton:
                        text: "Добавить мастера"
                        size_hint_x: 1
                        on_release: root.show_master_dialog()

            MDBottomNavigationItem:
                name: "stats"
                text: "Статистика"
                icon: "chart-box-outline"
                on_tab_press: root.refresh_stats()

                ScrollView:
                    MDBoxLayout:
                        id: stats_box
                        orientation: "vertical"
                        adaptive_height: True
                        padding: dp(12)
                        spacing: dp(12)


<FormScreen>:
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            id: form_bar
            title: "Новая заявка"
            elevation: 2
            left_action_items: [["arrow-left", lambda x: app.go_back()]]

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                adaptive_height: True
                padding: dp(16)
                spacing: dp(14)

                MDLabel:
                    text: "Клиент"
                    font_style: "Subtitle1"
                    adaptive_height: True

                MDTextField:
                    id: client_name
                    hint_text: "ФИО клиента *"
                    mode: "rectangle"

                MDTextField:
                    id: client_phone
                    hint_text: "Телефон * (+7XXXXXXXXXX)"
                    mode: "rectangle"
                    input_filter: lambda text, from_undo: "".join(c for c in text if c in "+0123456789")

                MDLabel:
                    text: "Устройство"
                    font_style: "Subtitle1"
                    adaptive_height: True

                MDRectangleFlatIconButton:
                    id: device_btn
                    icon: "laptop"
                    text: "Тип устройства: выберите *"
                    size_hint_x: 1
                    on_release: root.open_device_menu(self)

                MDTextField:
                    id: device_model
                    hint_text: "Производитель и модель"
                    mode: "rectangle"

                MDTextField:
                    id: serial_number
                    hint_text: "Серийный номер"
                    mode: "rectangle"

                MDTextField:
                    id: problem
                    hint_text: "Описание неисправности *"
                    mode: "rectangle"
                    multiline: True

                MDRectangleFlatIconButton:
                    id: priority_btn
                    icon: "flag-outline"
                    text: "Приоритет: Обычный"
                    size_hint_x: 1
                    on_release: root.open_priority_menu(self)

                MDRaisedButton:
                    text: "Сохранить заявку"
                    size_hint_x: 1
                    on_release: root.save()


<DetailScreen>:
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            id: detail_bar
            title: "Заявка"
            elevation: 2
            left_action_items: [["arrow-left", lambda x: app.go_back()]]
            right_action_items: [["pencil", lambda x: root.edit()], ["delete", lambda x: root.confirm_delete()]]

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                adaptive_height: True
                padding: dp(12)
                spacing: dp(12)

                MDCard:
                    orientation: "vertical"
                    padding: dp(12)
                    spacing: dp(4)
                    adaptive_height: True
                    elevation: 1
                    radius: [dp(10)]

                    MDLabel:
                        id: info_label
                        markup: True
                        adaptive_height: True

                MDRaisedButton:
                    id: status_btn
                    text: "Статус"
                    size_hint_x: 1
                    on_release: root.open_status_menu(self)

                MDRectangleFlatIconButton:
                    id: master_btn
                    icon: "account-wrench"
                    text: "Мастер: не назначен"
                    size_hint_x: 1
                    on_release: root.open_master_menu(self)

                MDBoxLayout:
                    adaptive_height: True
                    spacing: dp(8)

                    MDTextField:
                        id: cost_field
                        hint_text: "Стоимость ремонта, руб."
                        mode: "rectangle"
                        input_filter: "float"

                    MDIconButton:
                        icon: "content-save"
                        pos_hint: {"center_y": .5}
                        on_release: root.save_cost()

                MDBoxLayout:
                    adaptive_height: True
                    spacing: dp(8)

                    MDTextField:
                        id: comment_field
                        hint_text: "Комментарий"
                        mode: "rectangle"

                    MDIconButton:
                        icon: "send"
                        pos_hint: {"center_y": .5}
                        on_release: root.add_comment()

                MDLabel:
                    text: "История заявки"
                    font_style: "Subtitle1"
                    adaptive_height: True

                MDList:
                    id: history_list
"""


class MainScreen(Screen):
    """Главный экран: список заявок, мастера, статистика."""

    status_filter = None
    master_dialog = None

    # ----- заявки -----
    def refresh_requests(self, *args):
        db = MDApp.get_running_app().db
        box = self.ids.request_list
        box.clear_widgets()
        rows = db.get_requests(self.status_filter, self.ids.search_field.text)
        self.ids.filter_label.text = (
            f"{self.status_filter or 'Все заявки'}: {len(rows)}"
        )
        if not rows:
            box.add_widget(OneLineListItem(text="Заявок нет"))
        for r in rows:
            urgent = "СРОЧНО  •  " if r["priority"] == "Срочный" else ""
            model = f" {r['device_model']}" if r["device_model"] else ""
            item = ThreeLineListItem(
                text=f"{urgent}{r['number']}  •  {r['status']}",
                secondary_text=f"{r['client_name']}  •  {r['client_phone']}",
                tertiary_text=f"{r['device_type']}{model}: {r['problem']}",
            )
            item.bind(on_release=lambda x, rid=r["id"]: MDApp.get_running_app().open_detail(rid))
            box.add_widget(item)

    def open_filter_menu(self, caller):
        items = [{"text": "Все заявки", "viewclass": "OneLineListItem",
                  "on_release": lambda: self.set_filter(None)}]
        items += [{"text": s, "viewclass": "OneLineListItem",
                   "on_release": lambda s=s: self.set_filter(s)} for s in STATUSES]
        self.menu = MDDropdownMenu(caller=caller, items=items, width_mult=4)
        self.menu.open()

    def set_filter(self, status):
        self.menu.dismiss()
        self.status_filter = status
        self.refresh_requests()

    # ----- мастера -----
    def refresh_masters(self, *args):
        db = MDApp.get_running_app().db
        box = self.ids.master_list
        box.clear_widgets()
        masters = db.get_masters()
        if not masters:
            box.add_widget(OneLineListItem(text="Мастера не добавлены"))
        for m in masters:
            spec = m["specialization"] or "без специализации"
            box.add_widget(TwoLineListItem(
                text=m["name"],
                secondary_text=f"{spec}  •  заявок в работе: {m['open_count']}",
            ))

    def show_master_dialog(self):
        content = MDBoxLayout(orientation="vertical", spacing=dp(8),
                              size_hint_y=None, height=dp(200))
        self.m_name = MDTextField(hint_text="ФИО мастера *")
        self.m_phone = MDTextField(hint_text="Телефон")
        self.m_spec = MDTextField(hint_text="Специализация")
        for w in (self.m_name, self.m_phone, self.m_spec):
            content.add_widget(w)
        self.master_dialog = MDDialog(
            title="Новый мастер", type="custom", content_cls=content,
            buttons=[
                MDFlatButton(text="ОТМЕНА", on_release=lambda x: self.master_dialog.dismiss()),
                MDRaisedButton(text="ДОБАВИТЬ", on_release=lambda x: self.save_master()),
            ],
        )
        self.master_dialog.open()

    def save_master(self):
        db = MDApp.get_running_app().db
        try:
            db.add_master(self.m_name.text, self.m_phone.text, self.m_spec.text)
        except ValidationError as e:
            toast(str(e))
            return
        self.master_dialog.dismiss()
        toast("Мастер добавлен")
        self.refresh_masters()

    # ----- статистика -----
    def refresh_stats(self, *args):
        db = MDApp.get_running_app().db
        st = db.get_statistics()
        box = self.ids.stats_box
        box.clear_widgets()

        def card(title, lines):
            c = MDCard(orientation="vertical", padding=dp(12), spacing=dp(4),
                       adaptive_height=True, elevation=1, radius=[dp(10)])
            c.add_widget(MDLabel(text=title, font_style="H6", adaptive_height=True))
            for line in lines:
                c.add_widget(MDLabel(text=line, adaptive_height=True))
            box.add_widget(c)

        card("Общие показатели", [
            f"Всего заявок: {st['total']}",
            f"В работе (не закрыто): {st['open']}",
            f"Выручка по выданным: {st['revenue']:,.0f} руб.".replace(",", " "),
            f"Средний срок ремонта: {st['avg_days']} дн.",
        ])
        card("По статусам", [f"{s}: {n}" for s, n in st["by_status"].items()])
        card("По типам устройств",
             [f"{d}: {n}" for d, n in st["by_device"].items()] or ["Нет данных"])


class FormScreen(Screen):
    """Экран создания и редактирования заявки."""

    request_id = NumericProperty(0)  # 0 — новая заявка
    device_type = ""
    priority = "Обычный"

    def load(self, request_id=0):
        self.request_id = request_id
        ids = self.ids
        if request_id:
            r = MDApp.get_running_app().db.get_request(request_id)
            ids.form_bar.title = f"Редактирование {r['number']}"
            ids.client_name.text = r["client_name"]
            ids.client_phone.text = r["client_phone"]
            ids.device_model.text = r["device_model"] or ""
            ids.serial_number.text = r["serial_number"] or ""
            ids.problem.text = r["problem"]
            self.set_device(r["device_type"])
            self.set_priority(r["priority"])
        else:
            ids.form_bar.title = "Новая заявка"
            for f in ("client_name", "client_phone", "device_model", "serial_number", "problem"):
                ids[f].text = ""
            self.device_type = ""
            ids.device_btn.text = "Тип устройства: выберите *"
            self.set_priority("Обычный")

    def open_device_menu(self, caller):
        items = [{"text": d, "viewclass": "OneLineListItem",
                  "on_release": lambda d=d: self.set_device(d)} for d in DEVICE_TYPES]
        self.menu = MDDropdownMenu(caller=caller, items=items, width_mult=4)
        self.menu.open()

    def set_device(self, device):
        if getattr(self, "menu", None):
            self.menu.dismiss()
        self.device_type = device
        self.ids.device_btn.text = f"Тип устройства: {device}"

    def open_priority_menu(self, caller):
        items = [{"text": p, "viewclass": "OneLineListItem",
                  "on_release": lambda p=p: self.set_priority(p)} for p in PRIORITIES]
        self.menu = MDDropdownMenu(caller=caller, items=items, width_mult=3)
        self.menu.open()

    def set_priority(self, priority):
        if getattr(self, "menu", None):
            self.menu.dismiss()
        self.priority = priority
        self.ids.priority_btn.text = f"Приоритет: {priority}"

    def save(self):
        app = MDApp.get_running_app()
        ids = self.ids
        data = {
            "client_name": ids.client_name.text,
            "client_phone": ids.client_phone.text,
            "device_type": self.device_type,
            "device_model": ids.device_model.text,
            "serial_number": ids.serial_number.text,
            "problem": ids.problem.text,
            "priority": self.priority,
        }
        try:
            if self.request_id:
                app.db.update_request(self.request_id, data)
                toast("Изменения сохранены")
                app.open_detail(self.request_id, back=True)
            else:
                new_id = app.db.add_request(data)
                toast(f"Заявка {app.db.get_request(new_id)['number']} создана")
                app.go_back()
        except ValidationError as e:
            app.show_message("Проверьте данные", str(e))


class DetailScreen(Screen):
    """Карточка заявки: статус, мастер, стоимость, история."""

    request_id = NumericProperty(0)

    def load(self, request_id):
        self.request_id = request_id
        db = MDApp.get_running_app().db
        r = db.get_request(request_id)
        ids = self.ids
        ids.detail_bar.title = r["number"]
        lines = [
            f"[b]Статус:[/b] {r['status']}",
            f"[b]Принята:[/b] {r['created_at']}",
            f"[b]Приоритет:[/b] {r['priority']}",
            "",
            f"[b]Клиент:[/b] {r['client_name']}",
            f"[b]Телефон:[/b] {r['client_phone']}",
            "",
            f"[b]Устройство:[/b] {r['device_type']} {r['device_model'] or ''}",
            f"[b]Серийный номер:[/b] {r['serial_number'] or '—'}",
            f"[b]Неисправность:[/b] {r['problem']}",
        ]
        if r["closed_at"]:
            lines.append(f"[b]Закрыта:[/b] {r['closed_at']}")
        ids.info_label.text = "\n".join(lines)
        ids.status_btn.text = f"Статус: {r['status']}  (изменить)"
        ids.master_btn.text = f"Мастер: {r['master_name'] or 'не назначен'}"
        ids.cost_field.text = f"{r['cost']:.0f}" if r["cost"] else ""
        ids.comment_field.text = ""

        hl = ids.history_list
        hl.clear_widgets()
        for h in reversed(db.get_history(request_id)):
            hl.add_widget(TwoLineListItem(
                text=f"{h['changed_at']}  •  {h['status']}",
                secondary_text=h["comment"] or "—",
            ))

    def open_status_menu(self, caller):
        items = [{"text": s, "viewclass": "OneLineListItem",
                  "on_release": lambda s=s: self.set_status(s)} for s in STATUSES]
        self.menu = MDDropdownMenu(caller=caller, items=items, width_mult=4)
        self.menu.open()

    def set_status(self, status):
        self.menu.dismiss()
        db = MDApp.get_running_app().db
        db.change_status(self.request_id, status, self.ids.comment_field.text)
        toast(f"Статус: {status}")
        self.load(self.request_id)

    def open_master_menu(self, caller):
        masters = MDApp.get_running_app().db.get_masters()
        if not masters:
            toast("Сначала добавьте мастера")
            return
        items = [{"text": m["name"], "viewclass": "OneLineListItem",
                  "on_release": lambda mid=m["id"]: self.set_master(mid)} for m in masters]
        self.menu = MDDropdownMenu(caller=caller, items=items, width_mult=4)
        self.menu.open()

    def set_master(self, master_id):
        self.menu.dismiss()
        MDApp.get_running_app().db.assign_master(self.request_id, master_id)
        toast("Мастер назначен")
        self.load(self.request_id)

    def save_cost(self):
        try:
            MDApp.get_running_app().db.set_cost(self.request_id, self.ids.cost_field.text or 0)
            toast("Стоимость сохранена")
        except ValidationError as e:
            toast(str(e))

    def add_comment(self):
        try:
            MDApp.get_running_app().db.add_comment(self.request_id, self.ids.comment_field.text)
            self.load(self.request_id)
        except ValidationError as e:
            toast(str(e))

    def edit(self):
        MDApp.get_running_app().open_form(self.request_id)

    def confirm_delete(self):
        self.dialog = MDDialog(
            title="Удалить заявку?",
            text="Заявка и её история будут удалены без возможности восстановления.",
            buttons=[
                MDFlatButton(text="ОТМЕНА", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="УДАЛИТЬ", on_release=lambda x: self.delete()),
            ],
        )
        self.dialog.open()

    def delete(self):
        self.dialog.dismiss()
        MDApp.get_running_app().db.delete_request(self.request_id)
        toast("Заявка удалена")
        MDApp.get_running_app().go_back()


class RemontApp(MDApp):
    """Главный класс приложения."""

    def build(self):
        self.title = "Заявки на ремонт ПК"
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.accent_palette = "Amber"
        self.theme_cls.material_style = "M2"

        from kivy.core.window import Window
        if platform != "android":
            Window.size = (400, 780)
        else:
            # клавиатура не должна перекрывать поля ввода
            Window.softinput_mode = "below_target"
        # системная кнопка «Назад» Android (код 27)
        Window.bind(on_keyboard=self.on_back_key)

        db_path = os.environ.get("REMONT_DB") or os.path.join(self.user_data_dir, "remont.db")
        self.db = Database(db_path)

        Builder.load_string(KV)
        self.sm = ScreenManager(transition=SlideTransition())
        self.main_screen = MainScreen(name="main")
        self.form_screen = FormScreen(name="form")
        self.detail_screen = DetailScreen(name="detail")
        for s in (self.main_screen, self.form_screen, self.detail_screen):
            self.sm.add_widget(s)
        return self.sm

    def on_start(self):
        self.main_screen.refresh_requests()
        self.main_screen.refresh_masters()
        self.main_screen.refresh_stats()

    def on_stop(self):
        self.db.close()

    def on_back_key(self, window, key, *args):
        if key == 27 and self.sm.current != "main":
            self.go_back()
            return True  # не закрывать приложение
        return False

    # ----- навигация -----
    def open_form(self, request_id=0):
        self.form_screen.load(request_id)
        self.sm.transition.direction = "left"
        self.sm.current = "form"

    def open_detail(self, request_id, back=False):
        self.detail_screen.load(request_id)
        self.sm.transition.direction = "right" if back else "left"
        self.sm.current = "detail"

    def go_back(self):
        self.sm.transition.direction = "right"
        self.sm.current = "main"
        self.main_screen.refresh_requests()
        self.main_screen.refresh_masters()
        self.main_screen.refresh_stats()

    def show_message(self, title, text):
        dlg = MDDialog(title=title, text=text,
                       buttons=[MDFlatButton(text="ОК", on_release=lambda x: dlg.dismiss())])
        dlg.open()


if __name__ == "__main__":
    RemontApp().run()
