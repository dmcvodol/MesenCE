from pathlib import Path

root = Path('RetroArch')
makefile = root / 'Makefile.common'
cheevos = root / 'cheevos' / 'cheevos.c'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f'[skip] {label} already applied')
        return text
    if old not in text:
        raise RuntimeError(f'anchor not found: {label}')
    print(f'[patch] {label}')
    return text.replace(old, new, 1)

m = makefile.read_text(encoding='utf-8')
m = replace_once(m,
'''   # RetroAchievements\n   ifeq ($(HAVE_CHEEVOS), 1)\n      DEFINES += -DHAVE_CHEEVOS -DRC_CLIENT_SUPPORTS_HASH\n      INCLUDE_DIRS += -Ideps/rcheevos/include\n''',
'''   # RetroAchievements\n   ifeq ($(HAVE_CHEEVOS), 1)\n      DEFINES += -DHAVE_CHEEVOS -DRC_CLIENT_SUPPORTS_HASH\n      INCLUDE_DIRS += -Ideps/rcheevos/include\n\n      ifneq ($(findstring Win32,$(OS)),)\n         DEFINES += -DRC_CLIENT_SUPPORTS_EXTERNAL -DRC_CLIENT_SUPPORTS_RAINTEGRATION\n      endif\n''', 'enable RAIntegration macros')
m = replace_once(m,
'''             deps/rcheevos/src/rapi/rc_api_info.o \\\n             deps/rcheevos/src/rapi/rc_api_runtime.o \\\n             deps/rcheevos/src/rapi/rc_api_user.o \\\n\n      # RVZ/WIA disc image support for RetroAchievements\n''',
'''             deps/rcheevos/src/rapi/rc_api_info.o \\\n             deps/rcheevos/src/rapi/rc_api_runtime.o \\\n             deps/rcheevos/src/rapi/rc_api_user.o \\\n\n      ifneq ($(findstring Win32,$(OS)),)\n         OBJ += deps/rcheevos/src/rc_client_external.o \\\n                deps/rcheevos/src/rc_client_raintegration.o\n      endif\n\n      # RVZ/WIA disc image support for RetroAchievements\n''', 'add RAIntegration objects')
makefile.write_text(m, encoding='utf-8', newline='\n')

c = cheevos.read_text(encoding='utf-8')
c = replace_once(c, '#include <file/file_path.h>\n',
'#include <file/file_path.h>\n#ifdef RC_CLIENT_SUPPORTS_RAINTEGRATION\n#include <encodings/utf.h>\n#endif\n', 'UTF include')
c = replace_once(c, '#include "../audio/audio_driver.h"\n',
'#include "../audio/audio_driver.h"\n#ifdef RC_CLIENT_SUPPORTS_RAINTEGRATION\n#include "../gfx/video_driver.h"\n#include "../deps/rcheevos/include/rc_client_raintegration.h"\n#endif\n', 'RAIntegration includes')
c = replace_once(c,
'''   false /* badges_loading */\n};\n\nrcheevos_locals_t* get_rcheevos_locals(void)\n''',
'''   false /* badges_loading */\n};\n\n#ifdef RC_CLIENT_SUPPORTS_RAINTEGRATION\nstatic bool rcheevos_raintegration_attempted;\nstatic bool rcheevos_raintegration_pending;\nstatic char rcheevos_raintegration_pending_path[PATH_MAX_LENGTH];\n#endif\n\nrcheevos_locals_t* get_rcheevos_locals(void)\n''', 'RAIntegration state')
c = replace_once(c,
'''static rc_clock_t rcheevos_client_get_time_millisecs(const rc_client_t* client)\n{\n   return cpu_features_get_time_usec() / 1000;\n}\n\nbool rcheevos_load(const void *data)\n''',
'''static rc_clock_t rcheevos_client_get_time_millisecs(const rc_client_t* client)\n{\n   return cpu_features_get_time_usec() / 1000;\n}\n\n#ifdef RC_CLIENT_SUPPORTS_RAINTEGRATION\nstatic void rcheevos_raintegration_load_callback(int result,\n   const char* error_message, rc_client_t* client, void* userdata)\n{\n   struct retro_game_info info;\n   (void)client;\n   (void)userdata;\n\n   rcheevos_raintegration_pending = false;\n   rcheevos_raintegration_attempted = true;\n\n   if (result != RC_OK)\n      CHEEVOS_LOG(RCHEEVOS_TAG "RAIntegration unavailable: %s\\n",\n         error_message ? error_message : rc_error_str(result));\n   else\n      CHEEVOS_LOG(RCHEEVOS_TAG "RAIntegration initialized\\n");\n\n   if (!rcheevos_raintegration_pending_path[0])\n      return;\n\n   memset(&info, 0, sizeof(info));\n   info.path = rcheevos_raintegration_pending_path;\n   rcheevos_load(&info);\n}\n#endif\n\nbool rcheevos_load(const void *data)\n''', 'RAIntegration callback')
c = replace_once(c,
'''   rcheevos_locals.hardcore_requires_reload = false;\n   rcheevos_validate_config_settings();\n\n   CHEEVOS_LOG(RCHEEVOS_TAG "Load started, hardcore %sactive\\n", rcheevos_hardcore_active() ? "" : "not ");\n''',
'''   rcheevos_locals.hardcore_requires_reload = false;\n   rcheevos_validate_config_settings();\n\n#ifdef RC_CLIENT_SUPPORTS_RAINTEGRATION\n   if (!rcheevos_raintegration_attempted)\n   {\n      const char *pending_path = info->path;\n      if (!pending_path || !pending_path[0])\n         pending_path = path_get(RARCH_PATH_CONTENT);\n      if (pending_path)\n         strlcpy(rcheevos_raintegration_pending_path, pending_path,\n            sizeof(rcheevos_raintegration_pending_path));\n\n      if (rcheevos_raintegration_pending)\n         return true;\n\n      {\n         char app_dir[PATH_MAX_LENGTH] = {0};\n         wchar_t *app_dir_wide = NULL;\n         HWND hwnd = (HWND)video_driver_window_get();\n         fill_pathname_application_dir(app_dir, sizeof(app_dir));\n         if (app_dir[0])\n            app_dir_wide = utf8_to_utf16_string_alloc(app_dir);\n\n         if (hwnd && app_dir_wide)\n         {\n            rcheevos_raintegration_pending = true;\n            rc_client_begin_load_raintegration(rcheevos_locals.client,\n               app_dir_wide, hwnd, "RetroArch", PACKAGE_VERSION,\n               rcheevos_raintegration_load_callback, NULL);\n            free(app_dir_wide);\n            return true;\n         }\n\n         free(app_dir_wide);\n         rcheevos_raintegration_attempted = true;\n         CHEEVOS_LOG(RCHEEVOS_TAG "RAIntegration skipped: no HWND or app directory\\n");\n      }\n   }\n   else\n      rc_client_raintegration_update_main_window_handle(\n         rcheevos_locals.client, (HWND)video_driver_window_get());\n#endif\n\n   CHEEVOS_LOG(RCHEEVOS_TAG "Load started, hardcore %sactive\\n", rcheevos_hardcore_active() ? "" : "not ");\n''', 'RAIntegration gate')
cheevos.write_text(c, encoding='utf-8', newline='\n')
print('RetroArch RAIntegration patch applied.')
