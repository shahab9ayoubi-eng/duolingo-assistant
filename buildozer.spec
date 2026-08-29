[app]
title = Duolingo Assistant
package.name = duolingoassistant
package.domain = org.shahab

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy,requests,arabic_reshaper,python-bidi==0.4.2,google-genai

orientation = portrait
android.accept_sdk_license = True
fullscreen = 0

android.permissions = INTERNET,READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

[buildozer]
log_level = 2
warn_on_root = 1
