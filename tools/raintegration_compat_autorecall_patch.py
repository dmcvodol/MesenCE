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


# v14 is diagnostic only. Keep the safe v13 pre-dialog behavior, but add
# RA_DIAG.txt markers around the local saved Test association lookup so we can
# compare what RAIntegration sees before Unknown Title versus inside the dialog.

# ---------------------------------------------------------------------------
# GameIdentifier.cpp: log the pre-dialog lookup result.
# ---------------------------------------------------------------------------
patch(
    'src/services/GameIdentifier.cpp',
    '''#include <rc_hash.h>\n''',
    '''#include <rc_hash.h>\n#include <cstdio>\n''',
    'include cstdio in GameIdentifier')

patch(
    'src/services/GameIdentifier.cpp',
    '''static constexpr const wchar_t* KNOWN_HASHES_KEY = L"Hashes";\n''',
    '''static constexpr const wchar_t* KNOWN_HASHES_KEY = L"Hashes";\n\nstatic void WriteAutoRecallDiag(const char* stage, const std::string& sHash, unsigned nConsoleId, unsigned nGameId)\n{\n    FILE* fp = fopen("RA_DIAG.txt", "a");\n    if (fp)\n    {\n        fprintf(fp, "RA14_%s | hash=%s | console=%u | game_id=%u\\n",\n            stage, sHash.c_str(), nConsoleId, nGameId);\n        fclose(fp);\n    }\n}\n''',
    'add GameIdentifier v14 diagnostic helper')

patch(
    'src/services/GameIdentifier.cpp',
    '''                auto sEstimatedGameTitle = ra::services::ServiceLocator::Get<ra::data::context::EmulatorContext>().GetGameTitle();\n\n                ra::ui::viewmodels::UnknownGameViewModel vmUnknownGame;\n                vmUnknownGame.InitializeGameTitles();\n                vmUnknownGame.SetSystemName(ra::services::ServiceLocator::Get<ra::context::IConsoleContext>().Name());\n                vmUnknownGame.SetChecksum(ra::util::String::Widen(sHash));\n                vmUnknownGame.SetEstimatedGameName(ra::util::String::Widen(sEstimatedGameTitle));\n                vmUnknownGame.SetNewGameName(vmUnknownGame.GetEstimatedGameName());\n\n                if (vmUnknownGame.ShowModal() == ra::ui::DialogResult::OK)\n                {\n                    nGameId = vmUnknownGame.GetSelectedGameId();\n\n                    if (vmUnknownGame.GetTestMode())\n                        m_nPendingMode = ra::data::context::GameContext::Mode::CompatibilityTest;\n                }\n''',
    '''                auto sEstimatedGameTitle = ra::services::ServiceLocator::Get<ra::data::context::EmulatorContext>().GetGameTitle();\n\n                ra::ui::viewmodels::UnknownGameViewModel vmUnknownGame;\n                vmUnknownGame.SetSystemName(ra::services::ServiceLocator::Get<ra::context::IConsoleContext>().Name());\n                vmUnknownGame.SetChecksum(ra::util::String::Widen(sHash));\n                vmUnknownGame.SetEstimatedGameName(ra::util::String::Widen(sEstimatedGameTitle));\n                vmUnknownGame.SetNewGameName(vmUnknownGame.GetEstimatedGameName());\n\n                const auto nConsoleId = static_cast<unsigned>(\n                    ra::services::ServiceLocator::Get<ra::context::IConsoleContext>().Id());\n                const auto nRememberedGameId =\n                    ra::ui::viewmodels::UnknownGameViewModel::GetPreviousAssociation(\n                        ra::util::String::Widen(sHash));\n                WriteAutoRecallDiag("PREDIALOG", sHash, nConsoleId, nRememberedGameId);\n\n                if (nRememberedGameId != 0U)\n                {\n                    nGameId = nRememberedGameId;\n                    m_nPendingMode = ra::data::context::GameContext::Mode::CompatibilityTest;\n                    RA_LOG_INFO("Using saved pre-dialog compatibility test game ID %u for hash %s",\n                        nGameId, sHash);\n                }\n                else\n                {\n                    vmUnknownGame.InitializeGameTitles();\n\n                    if (vmUnknownGame.ShowModal() == ra::ui::DialogResult::OK)\n                    {\n                        nGameId = vmUnknownGame.GetSelectedGameId();\n\n                        if (vmUnknownGame.GetTestMode())\n                            m_nPendingMode = ra::data::context::GameContext::Mode::CompatibilityTest;\n                    }\n                }\n''',
    'keep v13 pre-dialog lookup and log its result')

# ---------------------------------------------------------------------------
# UnknownGameViewModel.cpp: log every saved-association read, including the raw
# encoded mapping and the result seen when the dialog checks it.
# ---------------------------------------------------------------------------
patch(
    'src/ui/viewmodels/UnknownGameViewModel.cpp',
    '''#include <rcheevos\\src\\rc_client_internal.h>\n''',
    '''#include <rcheevos\\src\\rc_client_internal.h>\n#include <cstdio>\n''',
    'include cstdio in UnknownGameViewModel')

patch(
    'src/ui/viewmodels/UnknownGameViewModel.cpp',
    '''unsigned int UnknownGameViewModel::GetPreviousAssociation(const std::wstring& sHash)\n{\n    auto& pLocalStorage = ra::services::ServiceLocator::GetMutable<ra::services::ILocalStorage>();\n    auto sMapping = pLocalStorage.ReadText(ra::services::StorageItemType::HashMapping, sHash);\n\n    std::string sLine;\n    if (sMapping && sMapping->GetLine(sLine))\n    {\n        const auto& pConsoleContext = ra::services::ServiceLocator::Get<ra::context::IConsoleContext>();\n        const unsigned nId = DecodeID(sLine, sHash, pConsoleContext.Id());\n        if (nId > 0)\n            return nId;\n    }\n\n    return 0;\n}\n''',
    '''unsigned int UnknownGameViewModel::GetPreviousAssociation(const std::wstring& sHash)\n{\n    auto& pLocalStorage = ra::services::ServiceLocator::GetMutable<ra::services::ILocalStorage>();\n    auto sMapping = pLocalStorage.ReadText(ra::services::StorageItemType::HashMapping, sHash);\n\n    std::string sLine;\n    unsigned nId = 0;\n    const auto& pConsoleContext = ra::services::ServiceLocator::Get<ra::context::IConsoleContext>();\n    const auto nConsoleId = static_cast<unsigned>(pConsoleContext.Id());\n\n    if (sMapping && sMapping->GetLine(sLine))\n        nId = DecodeID(sLine, sHash, pConsoleContext.Id());\n\n    FILE* fp = fopen("RA_DIAG.txt", "a");\n    if (fp)\n    {\n        fprintf(fp, "RA14_ASSOC_READ | hash=%s | console=%u | has_mapping=%u | raw=%s | decoded=%u\\n",\n            ra::util::String::Narrow(sHash).c_str(), nConsoleId, sMapping ? 1U : 0U,\n            sLine.empty() ? "<empty>" : sLine.c_str(), nId);\n        fclose(fp);\n    }\n\n    return nId;\n}\n''',
    'log raw and decoded saved association')

patch(
    'src/ui/viewmodels/UnknownGameViewModel.cpp',
    '''    const auto nId = GetPreviousAssociation(sHash);\n    if (nId != 0)\n    {\n''',
    '''    const auto nId = GetPreviousAssociation(sHash);\n\n    FILE* fp = fopen("RA_DIAG.txt", "a");\n    if (fp)\n    {\n        fprintf(fp, "RA14_DIALOG_CHECK | hash=%s | console=%u | game_id=%u\\n",\n            ra::util::String::Narrow(sHash).c_str(),\n            static_cast<unsigned>(ra::services::ServiceLocator::Get<ra::context::IConsoleContext>().Id()),\n            nId);\n        fclose(fp);\n    }\n\n    if (nId != 0)\n    {\n''',
    'log association result when Unknown Title checks it')

print('RAIntegration v14 diagnostic compatibility autorecall patch applied.')
