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


# Public method on GameIdentifier. It only auto-recalls mappings that were
# previously written by UnknownGameViewModel::BeginTest(), so a saved mapping
# is always treated as CompatibilityTest rather than a normal/official hash.
patch(
    'src/services/GameIdentifier.hh',
    '''    unsigned int IdentifyHash(const std::string& sHash);\n\n    /// <summary>\n    /// Activates a game.\n''',
    '''    unsigned int IdentifyHash(const std::string& sHash);\n\n    /// <summary>\n    /// Identifies a game using a previously saved compatibility-test association.\n    /// Falls back to the normal Unknown Title flow when no saved Test mapping exists.\n    /// </summary>\n    unsigned int IdentifyHashCompatibility(const std::string& sHash);\n\n    /// <summary>\n    /// Activates a game.\n''',
    'declare IdentifyHashCompatibility')

patch(
    'src/services/GameIdentifier.cpp',
    '''unsigned int GameIdentifier::IdentifyHash(const std::string& sHash)\n{\n''',
    '''unsigned int GameIdentifier::IdentifyHashCompatibility(const std::string& sHash)\n{\n    // BeginTest() stores an encoded hash -> GameID association in RAIntegration's\n    // HashMapping storage. Reuse only that association and explicitly keep the\n    // pending game in CompatibilityTest mode so achievements/leaderboards cannot\n    // be earned or submitted for an unregistered hash.\n    const auto nGameId = ra::ui::viewmodels::UnknownGameViewModel::GetPreviousAssociation(\n        ra::util::String::Widen(sHash));\n\n    if (nGameId != 0U)\n    {\n        RA_LOG_INFO("Auto-recalling compatibility test game ID %u for hash %s", nGameId, sHash);\n        m_sPendingHash = sHash;\n        m_nPendingGameId = nGameId;\n        m_nPendingMode = ra::data::context::GameContext::Mode::CompatibilityTest;\n        return nGameId;\n    }\n\n    return IdentifyHash(sHash);\n}\n\nunsigned int GameIdentifier::IdentifyHash(const std::string& sHash)\n{\n''',
    'implement IdentifyHashCompatibility')

patch(
    'src/Exports.hh',
    '''    API unsigned int CCONV _RA_IdentifyHash(const char* sHash);\n\n    //  Downloads and activates the achievements for the specified game.\n''',
    '''    API unsigned int CCONV _RA_IdentifyHash(const char* sHash);\n\n    // Gets a previously saved compatibility-test association for the hash,\n    // or falls back to the standard Unknown Title identification flow.\n    API unsigned int CCONV _RA_IdentifyHashCompatibility(const char* sHash);\n\n    //  Downloads and activates the achievements for the specified game.\n''',
    'declare compatibility export')

patch(
    'src/Exports.cpp',
    '''API unsigned int CCONV _RA_IdentifyHash(const char* sHash)\n{\n    return ra::services::ServiceLocator::GetMutable<ra::services::GameIdentifier>().IdentifyHash(sHash);\n}\n\n''',
    '''API unsigned int CCONV _RA_IdentifyHash(const char* sHash)\n{\n    return ra::services::ServiceLocator::GetMutable<ra::services::GameIdentifier>().IdentifyHash(sHash);\n}\n\nAPI unsigned int CCONV _RA_IdentifyHashCompatibility(const char* sHash)\n{\n    return ra::services::ServiceLocator::GetMutable<ra::services::GameIdentifier>().IdentifyHashCompatibility(sHash);\n}\n\n''',
    'implement compatibility export')

print('RAIntegration CompatibilityTest autorecall patch applied.')
