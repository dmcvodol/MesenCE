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
    print(f'[fallback] {label}')

# Call RAIntegration's legacy login + IdentifyHash exports.
# IdentifyHash owns the classic "Unknown Title" dialog used by RALibretro.
replace_once(
'''static void rcheevos_ra_diag(const char* stage, int result, const char* detail)\n{\n   FILE* fp = fopen("RA_DIAG.txt", "a");\n''',
'''static void rcheevos_ra_diag(const char* stage, int result, const char* detail);\n\ntypedef unsigned int (*rcheevos_ra_identify_hash_t)(const char* hash);\ntypedef void (*rcheevos_ra_attempt_login_t)(int blocking);\ntypedef const char* (*rcheevos_ra_username_t)(void);\n\nstatic unsigned int rcheevos_ra_show_unknown_title(const char* hash)\n{\n   HMODULE module;\n   rcheevos_ra_identify_hash_t identify_hash;\n   rcheevos_ra_attempt_login_t attempt_login;\n   rcheevos_ra_username_t username;\n   const char* current_user = NULL;\n\n   if (!hash || !hash[0])\n      return 0;\n\n   module = GetModuleHandleW(L"RA_Integration-x64.dll");\n   if (!module)\n      module = GetModuleHandleW(L"RA_Integration.dll");\n   if (!module)\n      return 0;\n\n   identify_hash = (rcheevos_ra_identify_hash_t)GetProcAddress(module, "_RA_IdentifyHash");\n   if (!identify_hash)\n      return 0;\n\n   attempt_login = (rcheevos_ra_attempt_login_t)GetProcAddress(module, "_RA_AttemptLogin");\n   username = (rcheevos_ra_username_t)GetProcAddress(module, "_RA_UserName");\n\n   if (username)\n      current_user = username();\n\n   if ((!current_user || !current_user[0]) && attempt_login)\n   {\n      rcheevos_ra_diag("LEGACY_LOGIN_BEGIN", 0, "_RA_AttemptLogin(1)");\n      attempt_login(1);\n      if (username)\n         current_user = username();\n      rcheevos_ra_diag("LEGACY_LOGIN_END", (current_user && current_user[0]) ? 1 : 0,\n            (current_user && current_user[0]) ? current_user : "not logged in");\n   }\n\n   if (!current_user || !current_user[0])\n      return 0;\n\n   return identify_hash(hash);\n}\n\nstatic void rcheevos_ra_diag(const char* stage, int result, const char* detail)\n{\n   FILE* fp = fopen("RA_DIAG.txt", "a");\n''',
'legacy login + IdentifyHash helper')

replace_once(
'''   const settings_t *settings   = config_get_ptr();\n   const rc_client_game_t *game = rc_client_get_game_info(client);\n\n#ifdef HAVE_THREADS\n''',
'''   const settings_t *settings   = config_get_ptr();\n   const rc_client_game_t *game = rc_client_get_game_info(client);\n\n#ifdef RC_CLIENT_SUPPORTS_RAINTEGRATION\n   if (result == RC_NO_GAME_LOADED && game && game->hash[0])\n   {\n      const unsigned int selected_game_id = rcheevos_ra_show_unknown_title(game->hash);\n      char diag[128];\n      snprintf(diag, sizeof(diag), "hash=%s selected_game_id=%u", game->hash, selected_game_id);\n      rcheevos_ra_diag("LEGACY_IDENTIFY_HASH", (int)selected_game_id, diag);\n   }\n#endif\n\n#ifdef HAVE_THREADS\n''',
'unknown game legacy fallback')

p.write_text(s, encoding='utf-8', newline='\n')
print('Legacy Unknown Title fallback with RAIntegration login applied.')
