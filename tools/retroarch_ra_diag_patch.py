from pathlib import Path

p = Path('RetroArch/cheevos/cheevos.c')
s = p.read_text(encoding='utf-8')

def replace_once(old, new, label):
    global s
    if new in s:
        print(f'[skip] {label}')
        return
    if old not in s:
        raise RuntimeError(f'anchor not found: {label}')
    s = s.replace(old, new, 1)
    print(f'[diag] {label}')

replace_once(
'''#ifdef RC_CLIENT_SUPPORTS_RAINTEGRATION\nstatic bool rcheevos_raintegration_attempted;\nstatic bool rcheevos_raintegration_pending;\nstatic char rcheevos_raintegration_pending_path[PATH_MAX_LENGTH];\n#endif\n''',
'''#ifdef RC_CLIENT_SUPPORTS_RAINTEGRATION\nstatic bool rcheevos_raintegration_attempted;\nstatic bool rcheevos_raintegration_pending;\nstatic char rcheevos_raintegration_pending_path[PATH_MAX_LENGTH];\n\nstatic void rcheevos_ra_diag(const char* stage, int result, const char* detail)\n{\n   FILE* fp = fopen("RA_DIAG.txt", "a");\n   if (!fp)\n      return;\n\n   fprintf(fp, "%s | result=%d", stage ? stage : "(null)", result);\n   if (detail && detail[0])\n      fprintf(fp, " | %s", detail);\n   fputc('\\n', fp);\n   fclose(fp);\n}\n#endif\n''',
'diagnostic helper')

replace_once(
'''   rcheevos_raintegration_pending = false;\n   rcheevos_raintegration_attempted = true;\n\n   if (result != RC_OK)\n''',
'''   rcheevos_raintegration_pending = false;\n   rcheevos_raintegration_attempted = true;\n   rcheevos_ra_diag("RAINTEGRATION_CALLBACK", result, error_message);\n\n   if (result != RC_OK)\n''',
'RAIntegration callback diagnostic')

replace_once(
'''   memset(&info, 0, sizeof(info));\n   info.path = rcheevos_raintegration_pending_path;\n   rcheevos_load(&info);\n''',
'''   memset(&info, 0, sizeof(info));\n   info.path = rcheevos_raintegration_pending_path;\n   rcheevos_ra_diag("RESUME_RCHEEVOS_LOAD", result, info.path);\n   rcheevos_load(&info);\n''',
'resume diagnostic')

replace_once(
'''         if (hwnd && app_dir_wide)\n         {\n            rcheevos_raintegration_pending = true;\n            rc_client_begin_load_raintegration(rcheevos_locals.client,\n''',
'''         if (hwnd && app_dir_wide)\n         {\n            rcheevos_raintegration_pending = true;\n            rcheevos_ra_diag("BEGIN_LOAD_RAINTEGRATION", 0, app_dir);\n            rc_client_begin_load_raintegration(rcheevos_locals.client,\n''',
'begin-load diagnostic')

replace_once(
'''static void rcheevos_client_load_game_callback(int result,\n   const char* error_message, rc_client_t* client, void* userdata)\n{\n   char msg[256];\n''',
'''static void rcheevos_client_load_game_callback(int result,\n   const char* error_message, rc_client_t* client, void* userdata)\n{\n   char msg[256];\n#ifdef RC_CLIENT_SUPPORTS_RAINTEGRATION\n   rcheevos_ra_diag("GAME_LOAD_CALLBACK", result, error_message);\n#endif\n''',
'game-load callback diagnostic')

p.write_text(s, encoding='utf-8', newline='\n')
print('RA diagnostic instrumentation applied.')
