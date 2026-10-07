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

# Use RAIntegration's legacy IdentifyHash + ActivateGame exports, but do NOT
# start a second RAIntegration login. RetroArch already logs the external
# RAIntegration client in through the normal rcheevos login flow.
#
# If an unknown ROM is detected before that login completes, remember the hash.
# rcheevos_client_login_callback() will resume the legacy Unknown Title flow as
# soon as the normal RetroArch login succeeds.
replace_once(
'''static void rcheevos_ra_diag(const char* stage, int result, const char* detail)\n{\n   FILE* fp = fopen("RA_DIAG.txt", "a");\n''',
'''static void rcheevos_ra_diag(const char* stage, int result, const char* detail);\n\ntypedef unsigned int (*rcheevos_ra_identify_hash_t)(const char* hash);\ntypedef void (*rcheevos_ra_activate_game_t)(unsigned int game_id);\ntypedef const char* (*rcheevos_ra_username_t)(void);\n\nstatic char rcheevos_ra_pending_unknown_hash[128];\n\nstatic unsigned int rcheevos_ra_show_unknown_title(const char* hash)\n{\n   HMODULE module = NULL;\n   rcheevos_ra_identify_hash_t identify_hash = NULL;\n   rcheevos_ra_activate_game_t activate_game = NULL;\n   rcheevos_ra_username_t username = NULL;\n   const char* current_user = NULL;\n   unsigned int selected_game_id = 0;\n\n   if (!hash || !hash[0])\n      return 0;\n\n   module = GetModuleHandleW(L"RA_Integration-x64.dll");\n   if (!module)\n      module = GetModuleHandleW(L"RA_Integration.dll");\n   if (!module)\n      return 0;\n\n   identify_hash = (rcheevos_ra_identify_hash_t)GetProcAddress(module, "_RA_IdentifyHash");\n   activate_game = (rcheevos_ra_activate_game_t)GetProcAddress(module, "_RA_ActivateGame");\n   username = (rcheevos_ra_username_t)GetProcAddress(module, "_RA_UserName");\n   if (!identify_hash || !activate_game || !username)\n      return 0;\n\n   current_user = username();\n   if (!current_user || !current_user[0])\n   {\n      strlcpy(rcheevos_ra_pending_unknown_hash, hash, sizeof(rcheevos_ra_pending_unknown_hash));\n      rcheevos_ra_diag("LEGACY_WAITING_FOR_NORMAL_LOGIN", 0, hash);\n      return 0;\n   }\n\n   rcheevos_ra_pending_unknown_hash[0] = '\\0';\n   selected_game_id = identify_hash(hash);\n   if (selected_game_id != 0)\n   {\n      char diag[128];\n      snprintf(diag, sizeof(diag), "game_id=%u", selected_game_id);\n      rcheevos_ra_diag("LEGACY_ACTIVATE_BEGIN", (int)selected_game_id, diag);\n      activate_game(selected_game_id);\n      rcheevos_ra_diag("LEGACY_ACTIVATE_END", (int)selected_game_id, diag);\n   }\n\n   return selected_game_id;\n}\n\nstatic void rcheevos_ra_diag(const char* stage, int result, const char* detail)\n{\n   FILE* fp = fopen("RA_DIAG.txt", "a");\n''',
'deferred IdentifyHash + ActivateGame helper')

# Unknown game: either show Unknown Title immediately if the normal RetroArch
# login has already completed, or remember the hash until login callback fires.
replace_once(
'''   const settings_t *settings   = config_get_ptr();\n   const rc_client_game_t *game = rc_client_get_game_info(client);\n\n#ifdef HAVE_THREADS\n''',
'''   const settings_t *settings   = config_get_ptr();\n   const rc_client_game_t *game = rc_client_get_game_info(client);\n\n#ifdef RC_CLIENT_SUPPORTS_RAINTEGRATION\n   if (result == RC_NO_GAME_LOADED && game && game->hash[0])\n   {\n      const unsigned int selected_game_id = rcheevos_ra_show_unknown_title(game->hash);\n      char diag[160];\n      snprintf(diag, sizeof(diag), "hash=%s selected_game_id=%u", game->hash, selected_game_id);\n      rcheevos_ra_diag("LEGACY_IDENTIFY_HASH", (int)selected_game_id, diag);\n   }\n#endif\n\n#ifdef HAVE_THREADS\n''',
'unknown game deferred legacy fallback')

# After the normal RetroArch/RAIntegration login succeeds, resume any pending
# unknown-ROM dialog. This avoids racing a second _RA_AttemptLogin call against
# the external client's login request.
replace_once(
'''   user = rc_client_get_user_info(client);\n   if (!user)\n''',
'''   user = rc_client_get_user_info(client);\n#ifdef RC_CLIENT_SUPPORTS_RAINTEGRATION\n   if (user && rcheevos_ra_pending_unknown_hash[0])\n   {\n      char pending_hash[sizeof(rcheevos_ra_pending_unknown_hash)];\n      unsigned int selected_game_id;\n      strlcpy(pending_hash, rcheevos_ra_pending_unknown_hash, sizeof(pending_hash));\n      selected_game_id = rcheevos_ra_show_unknown_title(pending_hash);\n      rcheevos_ra_diag("LEGACY_RESUME_AFTER_LOGIN", (int)selected_game_id, pending_hash);\n   }\n#endif\n   if (!user)\n''',
'resume Unknown Title after normal login')

p.write_text(s, encoding='utf-8')
print('Deferred Unknown Title fallback applied; no manual RAIntegration login is used.')
