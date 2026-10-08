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


# v13 approach:
# Do not touch the Unknown Title modal asynchronously at all.
# Let the normal ResolveHash request finish. If the server says the hash is
# unknown, check the locally saved Unknown Title -> Test association immediately
# before creating/showing the modal. If one exists, return that GameID in
# CompatibilityTest mode and completely skip the dialog/title-list async path.
# This preserves the no-earn/no-submit behavior without any UI lifetime races.

patch(
    'src/services/GameIdentifier.cpp',
    '''                auto sEstimatedGameTitle = ra::services::ServiceLocator::Get<ra::data::context::EmulatorContext>().GetGameTitle();\n\n                ra::ui::viewmodels::UnknownGameViewModel vmUnknownGame;\n                vmUnknownGame.InitializeGameTitles();\n                vmUnknownGame.SetSystemName(ra::services::ServiceLocator::Get<ra::context::IConsoleContext>().Name());\n                vmUnknownGame.SetChecksum(ra::util::String::Widen(sHash));\n                vmUnknownGame.SetEstimatedGameName(ra::util::String::Widen(sEstimatedGameTitle));\n                vmUnknownGame.SetNewGameName(vmUnknownGame.GetEstimatedGameName());\n\n                if (vmUnknownGame.ShowModal() == ra::ui::DialogResult::OK)\n                {\n                    nGameId = vmUnknownGame.GetSelectedGameId();\n\n                    if (vmUnknownGame.GetTestMode())\n                        m_nPendingMode = ra::data::context::GameContext::Mode::CompatibilityTest;\n                }\n''',
    '''                auto sEstimatedGameTitle = ra::services::ServiceLocator::Get<ra::data::context::EmulatorContext>().GetGameTitle();\n\n                ra::ui::viewmodels::UnknownGameViewModel vmUnknownGame;\n                vmUnknownGame.SetSystemName(ra::services::ServiceLocator::Get<ra::context::IConsoleContext>().Name());\n                vmUnknownGame.SetChecksum(ra::util::String::Widen(sHash));\n                vmUnknownGame.SetEstimatedGameName(ra::util::String::Widen(sEstimatedGameTitle));\n                vmUnknownGame.SetNewGameName(vmUnknownGame.GetEstimatedGameName());\n\n                // A previous Unknown Title -> Test stores a local encoded mapping\n                // for this exact hash/console. Check it only after ResolveHash has\n                // completed and the UnknownGame VM/context have been initialized,\n                // but before starting the async title-list/modal path.\n                const auto nRememberedGameId =\n                    ra::ui::viewmodels::UnknownGameViewModel::GetPreviousAssociation(\n                        ra::util::String::Widen(sHash));\n\n                if (nRememberedGameId != 0U)\n                {\n                    nGameId = nRememberedGameId;\n                    m_nPendingMode = ra::data::context::GameContext::Mode::CompatibilityTest;\n                    RA_LOG_INFO(\"Using saved pre-dialog compatibility test game ID %u for hash %s\",\n                        nGameId, sHash);\n                }\n                else\n                {\n                    vmUnknownGame.InitializeGameTitles();\n\n                    if (vmUnknownGame.ShowModal() == ra::ui::DialogResult::OK)\n                    {\n                        nGameId = vmUnknownGame.GetSelectedGameId();\n\n                        if (vmUnknownGame.GetTestMode())\n                            m_nPendingMode = ra::data::context::GameContext::Mode::CompatibilityTest;\n                    }\n                }\n''',
    'recall saved Test mapping after ResolveHash but before Unknown Title modal')

print('RAIntegration v13 pre-dialog CompatibilityTest autorecall patch applied.')
