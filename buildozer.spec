[app]
title = Заявки на ремонт ПК
package.name = remontpc
package.domain = ru.kep
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.exclude_patterns = test_*.py
version = 1.0
requirements = python3,kivy==2.3.1,kivymd==1.2.0,pillow,pyjnius,android
orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
