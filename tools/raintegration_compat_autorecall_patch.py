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


# v12 approach:
# The remembered Test association is only auto-completed after the asynchronous
# title-list callback has fully returned. v11 called SetDialogResult(OK) from
# inside that callback, which could destroy the modal/viewmodel while the
# callback still held an AsyncKeepAlive. v12 hops through a detached worker and
# then queues the completion back to the UI thread. If UI dispatch is unavailable,
# the safety check leaves the dialog open instead of closing it from a wrong thread.

patch(
    'src/ui/viewmodels/UnknownGameViewModel.cpp',
    '''#include "services\\ServiceLocator.hh"\n\n#include "ui\\viewmodels\\MessageBoxViewModel.hh"\n''',
    '''#include "services\\ServiceLocator.hh"\n\n#include "ui\\IDesktop.hh"\n#include "ui\\viewmodels\\MessageBoxViewModel.hh"\n''',
    'include IDesktop for deferred UI completion')

patch(
    'src/ui/viewmodels/UnknownGameViewModel.cpp',
    '''#include <rcheevos\\src\\rc_client_internal.h>\n\nnamespace ra {\n''',
    '''#include <rcheevos\\src\\rc_client_internal.h>\n\n#include <thread>\n\nnamespace ra {\n''',
    'include thread for one-shot deferred dispatch')

patch(
    'src/ui/viewmodels/UnknownGameViewModel.cpp',
    '''void UnknownGameViewModel::CheckForPreviousAssociation()\n{\n''',
    '''static void AddClientHash(const std::string& sHash, uint32_t nGameId, bool isUnknown);\n\nvoid UnknownGameViewModel::CheckForPreviousAssociation()\n{\n''',
    'forward declare AddClientHash before previous-association check')

patch(
    'src/ui/viewmodels/UnknownGameViewModel.cpp',
    '''    const auto nId = GetPreviousAssociation(sHash);\n    if (nId != 0)\n    {\n        const auto& sGameName = m_vGameTitles.GetLabelForId(nId);\n        if (!sGameName.empty())\n            SetSelectedGameId(nId);\n    }\n}\n''',
    '''    const auto nId = GetPreviousAssociation(sHash);\n    if (nId != 0)\n    {\n        const auto& sGameName = m_vGameTitles.GetLabelForId(nId);\n        if (!sGameName.empty())\n        {\n            SetSelectedGameId(nId);\n\n            const auto sNarrowHash = ra::util::String::Narrow(sHash);\n            auto pAsyncHandle = CreateAsyncHandle();\n            auto* pThis = this;\n\n            // Do not close the modal from inside the title-list callback.\n            // Hop to a worker first; InvokeOnUIThread will then enqueue the\n            // completion behind the callback that is currently finishing.\n            std::thread([pThis, nId, sNarrowHash, pAsyncHandle]() {\n                auto& pDesktop = ra::services::ServiceLocator::Get<ra::ui::IDesktop>();\n                pDesktop.InvokeOnUIThread([pThis, nId, sNarrowHash, pAsyncHandle]() {\n                    ra::data::AsyncKeepAlive pKeepAlive(*pAsyncHandle);\n                    if (pAsyncHandle->IsDestroyed())\n                        return;\n\n                    const auto& pDesktop2 = ra::services::ServiceLocator::Get<ra::ui::IDesktop>();\n                    if (!pDesktop2.IsOnUIThread())\n                        return;\n\n                    // If the user changed the selection/hash before this queued\n                    // action ran, don't force the remembered mapping.\n                    if (pThis->GetSelectedGameId() != nId ||\n                        ra::util::String::Narrow(pThis->GetChecksum()) != sNarrowHash)\n                    {\n                        return;\n                    }\n\n                    pThis->SetTestMode(true);\n                    AddClientHash(sNarrowHash, nId, true);\n                    pThis->SetDialogResult(ra::ui::DialogResult::OK);\n                });\n            }).detach();\n        }\n    }\n}\n''',
    'defer remembered Test completion until after async callback returns')

print('RAIntegration v12 deferred-UI CompatibilityTest autorecall patch applied.')
