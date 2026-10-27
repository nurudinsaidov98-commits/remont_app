# Как собрать APK

Приложение написано на Python (Kivy + KivyMD). APK собирается утилитой Buildozer только под Linux, поэтому ниже два бесплатных способа без установки чего-либо на компьютер.

## Способ 1. Google Colab (проще всего)

1. Откройте https://colab.research.google.com и создайте новый блокнот.
2. Слева нажмите значок папки и загрузите файлы `main.py`, `database.py`, `buildozer.spec`.
3. Вставьте в ячейку и запустите (кнопка ▶):

```
!sudo apt-get update -qq
!sudo apt-get install -y -qq zip unzip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev cmake libffi-dev libssl-dev automake openjdk-17-jdk
!pip install -q buildozer cython==0.29.36
!yes | buildozer -v android debug
```

4. Первая сборка идёт 20–30 минут. Готовый файл появится в папке `bin/` (например `remontpc-1.0-arm64-v8a_armeabi-v7a-debug.apk`). Нажмите на него правой кнопкой → «Скачать».

## Способ 2. GitHub Actions

1. Создайте репозиторий на github.com и загрузите в него все файлы проекта вместе с папкой `.github`.
2. Откройте вкладку **Actions**: сборка запустится сама.
3. Когда она завершится (зелёная галочка), внизу страницы в разделе **Artifacts** скачайте `remontpc-apk`.

## Установка на телефон

Скопируйте APK на телефон и откройте. Android попросит разрешить установку из неизвестных источников: разрешите для файлового менеджера или браузера.

## Запуск на компьютере (для проверки)

```
pip install kivy==2.3.1 kivymd==1.2.0
python main.py
```

Тесты логики: `python -m unittest test_database`
