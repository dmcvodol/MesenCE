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


# v11 approach:
# Do not try to recall the saved Test mapping early from GameIdentifier::IdentifyHash.
# On the user's working 1.4.2 DLL, the Unknown Title dialog already proves that
# CheckForPreviousAssociation() can successfully read the saved hash->GameID mapping.
# When that association resolves to an actual title, automatically convert the
# dialog into the same Compatibility Test result as pressing Test manually.

patch(
    'src/ui/viewmodels/UnknownGameViewModel.cpp',
    '''void UnknownGameViewModel::CheckForPreviousAssociation()\n{\n''',
    '''static void AddClientHash(const std::string& sHash, uint32_t nGameId, bool isUnknown);\n\nvoid UnknownGameViewModel::CheckForPreviousAssociation()\n{\n''',
    'forward declare AddClientHash before previous-association check')

patch(
    'src/ui/viewmodels/UnknownGameViewModel.cpp',
    '''    const auto nId = GetPreviousAssociation(sHash);\n    if (nId != 0)\n    {\n        const auto& sGameName = m_vGameTitles.GetLabelForId(nId);\n        if (!sGameName.empty())\n            SetSelectedGameId(nId);\n    }\n}\n''',
    '''    const auto nId = GetPreviousAssociation(sHash);\n    if (nId != 0)\n    {\n        const auto& sGameName = m_vGameTitles.GetLabelForId(nId);\n        if (!sGameName.empty())\n        {\n            // The user previously chose Unknown Title -> Test for this exact hash.\n            // At this point the title list and console context are fully initialized,\n            // so reproduce the non-earning compatibility-test path automatically.\n            SetSelectedGameId(nId);\n            SetTestMode(true);\n            AddClientHash(ra::util::String::Narrow(sHash), nId, true);\n            SetDialogResult(ra::ui::DialogResult::OK);\n        }\n    }\n}\n''',
    'auto-complete remembered Unknown Title mapping as Compatibility Test')

print('RAIntegration v11 late-dialog CompatibilityTest autorecall patch applied.')
