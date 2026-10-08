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

# Use RAIntegration's compatibility-aware IdentifyHash export when available.
# The custom export auto-recalls only mappings previously saved by the official
# Unknown Title -> Test flow, and explicitly keeps them in CompatibilityTest mode.
# If the custom export is unavailable, fall back to the normal legacy IdentifyHash.
#
# Do NOT start a second RAIntegration login. RetroArch already logs the external
# RAIntegration client in through the normal rcheevos login flow. If an unknown
# ROM is detected before login completes, remember the hash and resume after the
# normal login callback succeeds.
replace_once(
'''static void rcheevos_ra_diag(const char* stage, int result, const char* detail)\n{\n   FILE* fp = fopen("RA_DIAG.txt", "a");\n''',
'''static void rcheevos_ra_diag(const char* stage, int result, const char* detail);\n\ntypedef unsigned int (*rcheevos_ra_identify_hash_t)(const char* hash);\ntypedef unsigned int (*rcheevos_ra_identify_hash_compat_t)(const char* hash);\ntypedef void (*rcheevos_ra_activate_game_t)(unsigned int game_id);\ntypedef const char* (*rcheevos_ra_username_t)(void);\n\nstatic char rcheevos_ra_pending_unknown_hash[128];\n\nstatic unsigned int rcheevos_ra_show_unknown_title(const char* hash)\n{\n   HMODULE module = NULL;\n   rcheevos_ra_identify_hash_t identify_hash = NULL;\n   rcheevos_ra_identify_hash_compat_t identify_hash_compat = NULL;\n   rcheevos_ra_activate_game_t activate_game = NULL;\n   rcheevos_ra_username_t username = NULL;\n   const char* current_user = NULL;\n   unsigned int selected_game_id = 0;\n\n   if (!hash || !hash[0])\n      return 0;\n\n   module = GetModuleHandleW(L"RA_Integration-x64.dll");\n   if (!module)\n      module = GetModuleHandleW(L"RA_Integration.dll");\n   if (!module)\n      return 0;\n\n   identify_hash_compat = (rcheevos_ra_identify_hash_compat_t)GetProcAddress(module, "_RA_IdentifyHashCompatibility");\n   identify_hash = (rcheevos_ra_identify_hash_t)GetProcAddress(module, "_RA_IdentifyHash");\n   activate_game = (rcheevos_ra_activate_game_t)GetProcAddress(module, "_RA_ActivateGame");\n   username = (rcheevos_ra_username_t)GetProcAddress(module, "_RA_UserName");\n   if ((!identify_hash_compat && !identify_hash) || !activate_game || !username)\n      return 0;\n\n   current_user = username();\n   if (!current_user || !current_user[0])\n   {\n      strlcpy(rcheevos_ra_pending_unknown_hash, hash, sizeof(rcheevos_ra_pending_unknown_hash));\n      rcheevos_ra_diag("LEGACY_WAITING_FOR_NORMAL_LOGIN", 0, hash);\n      return 0;\n   }\n\n   rcheevos_ra_pending_unknown_hash[0] = '\\0';\n   if (identify_hash_compat)\n   {\n      selected_game_id = identify_hash_compat(hash);\n      rcheevos_ra_diag("COMPAT_IDENTIFY_HASH", (int)selected_game_id, hash);\n   }\n   else\n   {\n      selected_game_id = identify_hash(hash);\n      rcheevos_ra_diag("LEGACY_IDENTIFY_HASH_FALLBACK", (int)selected_game_id, hash);\n   }\n\n   if (selected_game_id != 0)\n   {\n      char diag[128];\n      snprintf(diag, sizeof(diag), "game_id=%u", selected_game_id);\n      rcheevos_ra_diag("LEGACY_ACTIVATE_BEGIN", (int)selected_game_id, diag);\n      activate_game(selected_game_id);\n      rcheevos_ra_diag("LEGACY_ACTIVATE_END", (int)selected_game_id, diag);\n   }\n\n   return selected_game_id;\n}\n\nstatic void rcheevos_ra_diag(const char* stage, int result, const char* detail)\n{\n   FILE* fp = fopen("RA_DIAG.txt", "a");\n''',
'compatibility-aware IdentifyHash + ActivateGame helper')

# Unknown game: either show Unknown Title / auto-recall a previous Test mapping
# immediately if the normal RetroArch login has completed, or remember the hash.
replace_once(
'''   const settings_t *settings   = config_get_ptr();\n   const rc_client_game_t *game = rc_client_get_game_info(client);\n\n#ifdef HAVE_THREADS\n''',
'''   const settings_t *settings   = config_get_ptr();\n   const rc_client_game_t *game = rc_client_get_game_info(client);\n\n#ifdef RC_CLIENT_SUPPORTS_RAINTEGRATION\n   if (result == RC_NO_GAME_LOADED && game && game->hash[0])\n   {\n      const unsigned int selected_game_id = rcheevos_ra_show_unknown_title(game->hash);\n      char diag[160];\n      snprintf(diag, sizeof(diag), "hash=%s selected_game_id=%u", game->hash, selected_game_id);\n      rcheevos_ra_diag("UNKNOWN_GAME_COMPAT_FLOW", (int)selected_game_id, diag);\n   }\n#endif\n\n#ifdef HAVE_THREADS\n''',
'unknown game compatibility flow')

# After the normal RetroArch/RAIntegration login succeeds, resume any pending
# unknown-ROM flow. This avoids racing a second login against the external client.
replace_once(
'''   user = rc_client_get_user_info(client);\n   if (!user)\n''',
'''   user = rc_client_get_user_info(client);\n#ifdef RC_CLIENT_SUPPORTS_RAINTEGRATION\n   if (user && rcheevos_ra_pending_unknown_hash[0])\n   {\n      char pending_hash[sizeof(rcheevos_ra_pending_unknown_hash)];\n      unsigned int selected_game_id;\n      strlcpy(pending_hash, rcheevos_ra_pending_unknown_hash, sizeof(pending_hash));\n      selected_game_id = rcheevos_ra_show_unknown_title(pending_hash);\n      rcheevos_ra_diag("COMPAT_RESUME_AFTER_LOGIN", (int)selected_game_id, pending_hash);\n   }\n#endif\n   if (!user)\n''',
'resume compatibility flow after normal login')

p.write_text(s, encoding='utf-8')
print('Compatibility-aware Unknown Title fallback applied; no manual RAIntegration login is used.')
