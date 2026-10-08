from pathlib import Path

ROOT = Path('RAIntegrationSDK')


def patch(path, old, new, label):
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if new in s:
        print(f'[skip] {label}')
        return
    if old not in s:
        raise RuntimeError(f'anchor not found for {label}: {path}')
    p.write_text(s.replace(old, new, 1), encoding='utf-8')
    print(f'[RAIntegration] {label}')


# Safer v9 approach:
# keep RetroArch on the standard _RA_IdentifyHash export and only teach
# RAIntegration's existing IdentifyHash() path to recall a mapping that was
# previously created by Unknown Title -> Test.
#
# BeginTest() is the only path that writes these per-hash mappings, and the
# existing IdentifyHash() code already marks any FindCompatibilityMatch result
# as CompatibilityTest mode before _RA_ActivateGame is called.
patch(
    'src/services/GameIdentifier.cpp',
    '''static unsigned int FindCompatibilityMatch(const std::string& sHash)\n{\n    const auto& pGameContext = ra::services::ServiceLocator::Get<ra::data::context::GameContext>();\n    if (pGameContext.GetMode() != ra::data::context::GameContext::Mode::CompatibilityTest)\n        return 0;\n\n    const auto nGameId = ra::ui::viewmodels::UnknownGameViewModel::GetPreviousAssociation(ra::util::String::Widen(sHash));\n    if (nGameId != pGameContext.GameId())\n        return 0;\n\n    return nGameId;\n}\n''',
    '''static unsigned int FindCompatibilityMatch(const std::string& sHash)\n{\n    // Unknown Title -> Test stores an encoded per-hash association locally.\n    // Recalling it here is safe because IdentifyHash() handles this return value\n    // by explicitly setting m_nPendingMode to CompatibilityTest.\n    const auto nGameId = ra::ui::viewmodels::UnknownGameViewModel::GetPreviousAssociation(\n        ra::util::String::Widen(sHash));\n\n    if (nGameId != 0U)\n        RA_LOG_INFO("Auto-recalling saved compatibility test game ID %u for hash %s", nGameId, sHash);\n\n    return nGameId;\n}\n''',
    'autorecall saved Test mapping inside standard IdentifyHash')

print('RAIntegration v9 standard IdentifyHash CompatibilityTest autorecall patch applied.')
