#include <windows.h>
#include <winhttp.h>
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include "rc_client.h"
#include "rc_consoles.h"

#pragma comment(lib, "winhttp.lib")

typedef uint32_t (__cdecl* MesenRAReadMemoryCallback)(uint32_t address, uint8_t* buffer, uint32_t numBytes);
typedef void (__cdecl* MesenRAEventCallback)(uint32_t type, const char* title, const char* description, uint32_t points);

static rc_client_t* g_client = nullptr;
static MesenRAReadMemoryCallback g_readMemory = nullptr;
static MesenRAEventCallback g_eventCallback = nullptr;
static uint32_t g_consoleId = RC_CONSOLE_UNKNOWN;
static int g_lastResult = 0;
static std::string g_lastError;

static std::wstring Utf8ToWide(const char* text)
{
	if(text == nullptr || *text == '\0') {
		return L"";
	}

	int length = MultiByteToWideChar(CP_UTF8, 0, text, -1, nullptr, 0);
	if(length <= 1) {
		return L"";
	}

	std::wstring result((size_t)length, L'\0');
	if(MultiByteToWideChar(CP_UTF8, 0, text, -1, result.data(), length) == 0) {
		return L"";
	}
	if(!result.empty() && result.back() == L'\0') {
		result.pop_back();
	}
	return result;
}

static const rc_memory_region_t* FindMemoryRegion(uint32_t address)
{
	if(g_consoleId == RC_CONSOLE_UNKNOWN) {
		return nullptr;
	}

	const rc_memory_regions_t* regions = rc_console_memory_regions(g_consoleId);
	if(regions == nullptr || regions->region == nullptr) {
		return nullptr;
	}

	for(uint32_t i = 0; i < regions->num_regions; i++) {
		const rc_memory_region_t& region = regions->region[i];
		if(address >= region.start_address && address <= region.end_address) {
			return &region;
		}
	}
	return nullptr;
}

static uint32_t RC_CCONV ReadMemory(uint32_t address, uint8_t* buffer, uint32_t numBytes, rc_client_t*)
{
	if(g_readMemory == nullptr || buffer == nullptr || numBytes == 0) {
		return 0;
	}

	uint32_t totalRead = 0;
	while(totalRead < numBytes) {
		uint32_t logicalAddress = address + totalRead;
		const rc_memory_region_t* region = FindMemoryRegion(logicalAddress);
		if(region == nullptr) {
			break;
		}

		uint32_t availableInRegion = region->end_address - logicalAddress + 1;
		uint32_t chunkSize = std::min(numBytes - totalRead, availableInRegion);
		if(region->type == RC_MEMORY_TYPE_UNUSED) {
			std::memset(buffer + totalRead, 0, chunkSize);
			totalRead += chunkSize;
			continue;
		}

		uint32_t realAddress = region->real_address + (logicalAddress - region->start_address);
		uint32_t read = g_readMemory(realAddress, buffer + totalRead, chunkSize);
		totalRead += read;
		if(read != chunkSize) {
			break;
		}
	}

	return totalRead;
}

static void RC_CCONV ServerCall(const rc_api_request_t* request, rc_client_server_callback_t callback, void* callbackData, rc_client_t*)
{
	rc_api_server_response_t response{};
	response.http_status_code = RC_API_SERVER_RESPONSE_CLIENT_ERROR;

	if(request == nullptr || request->url == nullptr || callback == nullptr) {
		if(callback != nullptr) {
			callback(&response, callbackData);
		}
		return;
	}

	std::wstring url = Utf8ToWide(request->url);
	URL_COMPONENTS parts{};
	parts.dwStructSize = sizeof(parts);
	parts.dwSchemeLength = (DWORD)-1;
	parts.dwHostNameLength = (DWORD)-1;
	parts.dwUrlPathLength = (DWORD)-1;
	parts.dwExtraInfoLength = (DWORD)-1;

	if(url.empty() || !WinHttpCrackUrl(url.c_str(), (DWORD)url.size(), 0, &parts)) {
		callback(&response, callbackData);
		return;
	}

	std::wstring host(parts.lpszHostName, parts.dwHostNameLength);
	std::wstring path(parts.lpszUrlPath, parts.dwUrlPathLength);
	if(parts.dwExtraInfoLength > 0) {
		path.append(parts.lpszExtraInfo, parts.dwExtraInfoLength);
	}

	HINTERNET session = WinHttpOpen(L"MesenCE RetroAchievements/0.1", WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,
		WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
	if(session == nullptr) {
		callback(&response, callbackData);
		return;
	}

	DWORD decompression = WINHTTP_DECOMPRESSION_FLAG_GZIP | WINHTTP_DECOMPRESSION_FLAG_DEFLATE;
	WinHttpSetOption(session, WINHTTP_OPTION_DECOMPRESSION, &decompression, sizeof(decompression));

	HINTERNET connection = WinHttpConnect(session, host.c_str(), parts.nPort, 0);
	if(connection == nullptr) {
		WinHttpCloseHandle(session);
		callback(&response, callbackData);
		return;
	}

	const wchar_t* verb = request->post_data != nullptr ? L"POST" : L"GET";
	DWORD flags = parts.nScheme == INTERNET_SCHEME_HTTPS ? WINHTTP_FLAG_SECURE : 0;
	HINTERNET httpRequest = WinHttpOpenRequest(connection, verb, path.c_str(), nullptr,
		WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, flags);
	if(httpRequest == nullptr) {
		WinHttpCloseHandle(connection);
		WinHttpCloseHandle(session);
		callback(&response, callbackData);
		return;
	}

	std::wstring headers;
	if(request->content_type != nullptr && *request->content_type != '\0') {
		headers = L"Content-Type: " + Utf8ToWide(request->content_type);
	}

	const char* postData = request->post_data;
	DWORD postSize = postData != nullptr ? (DWORD)std::strlen(postData) : 0;
	BOOL sent = WinHttpSendRequest(httpRequest,
		headers.empty() ? WINHTTP_NO_ADDITIONAL_HEADERS : headers.c_str(),
		headers.empty() ? 0 : (DWORD)-1L,
		postSize > 0 ? (LPVOID)postData : WINHTTP_NO_REQUEST_DATA,
		postSize, postSize, 0);

	std::vector<char> body;
	if(sent && WinHttpReceiveResponse(httpRequest, nullptr)) {
		DWORD status = 0;
		DWORD statusSize = sizeof(status);
		if(WinHttpQueryHeaders(httpRequest, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
			WINHTTP_HEADER_NAME_BY_INDEX, &status, &statusSize, WINHTTP_NO_HEADER_INDEX)) {
			response.http_status_code = (int)status;
		}

		for(;;) {
			DWORD available = 0;
			if(!WinHttpQueryDataAvailable(httpRequest, &available) || available == 0) {
				break;
			}

			size_t oldSize = body.size();
			body.resize(oldSize + available);
			DWORD read = 0;
			if(!WinHttpReadData(httpRequest, body.data() + oldSize, available, &read)) {
				body.resize(oldSize);
				break;
			}
			body.resize(oldSize + read);
		}
	}

	response.body = body.empty() ? nullptr : body.data();
	response.body_length = body.size();
	callback(&response, callbackData);

	WinHttpCloseHandle(httpRequest);
	WinHttpCloseHandle(connection);
	WinHttpCloseHandle(session);
}

static void RC_CCONV EventHandler(const rc_client_event_t* event, rc_client_t*)
{
	if(event == nullptr || g_eventCallback == nullptr) {
		return;
	}

	const char* title = nullptr;
	const char* description = nullptr;
	uint32_t points = 0;
	if(event->achievement != nullptr) {
		title = event->achievement->title;
		description = event->achievement->description;
		points = event->achievement->points;
	} else if(event->leaderboard != nullptr) {
		title = event->leaderboard->title;
		description = event->leaderboard->description;
	} else if(event->server_error != nullptr) {
		title = "RetroAchievements server error";
		description = event->server_error->error_message;
	}

	g_eventCallback(event->type, title, description, points);
}

static void RC_CCONV AsyncResult(int result, const char* errorMessage, rc_client_t*, void*)
{
	g_lastResult = result;
	g_lastError = errorMessage != nullptr ? errorMessage : "";
}

extern "C"
{
	__declspec(dllexport) bool __cdecl MesenRA_Create(MesenRAReadMemoryCallback readMemory, MesenRAEventCallback eventCallback)
	{
		if(g_client != nullptr) {
			return true;
		}

		g_readMemory = readMemory;
		g_eventCallback = eventCallback;
		g_client = rc_client_create(ReadMemory, ServerCall);
		if(g_client == nullptr) {
			return false;
		}

		rc_client_set_event_handler(g_client, EventHandler);
		// Keep softcore until Mesen-side hardcore restrictions are fully enforced.
		rc_client_set_hardcore_enabled(g_client, 0);
		return true;
	}

	__declspec(dllexport) void __cdecl MesenRA_Destroy()
	{
		if(g_client != nullptr) {
			rc_client_destroy(g_client);
			g_client = nullptr;
		}
		g_readMemory = nullptr;
		g_eventCallback = nullptr;
		g_consoleId = RC_CONSOLE_UNKNOWN;
		g_lastResult = 0;
		g_lastError.clear();
	}

	__declspec(dllexport) void __cdecl MesenRA_SetHardcore(bool enabled)
	{
		if(g_client != nullptr) {
			rc_client_set_hardcore_enabled(g_client, enabled ? 1 : 0);
		}
	}

	__declspec(dllexport) bool __cdecl MesenRA_LoginWithToken(const char* username, const char* token)
	{
		if(g_client == nullptr || username == nullptr || token == nullptr || *username == '\0' || *token == '\0') {
			return false;
		}
		g_lastResult = -1;
		g_lastError.clear();
		rc_client_begin_login_with_token(g_client, username, token, AsyncResult, nullptr);
		return g_lastResult == 0;
	}

	__declspec(dllexport) bool __cdecl MesenRA_LoadGame(uint32_t consoleId, const char* filePath, const uint8_t* data, size_t dataSize)
	{
		if(g_client == nullptr || data == nullptr || dataSize == 0) {
			return false;
		}
		g_consoleId = consoleId;
		g_lastResult = -1;
		g_lastError.clear();
		rc_client_begin_identify_and_load_game(g_client, consoleId, filePath, data, dataSize, AsyncResult, nullptr);
		if(g_lastResult == 0 && rc_client_is_game_loaded(g_client) != 0) {
			return true;
		}
		g_consoleId = RC_CONSOLE_UNKNOWN;
		return false;
	}

	__declspec(dllexport) void __cdecl MesenRA_UnloadGame()
	{
		if(g_client != nullptr) {
			rc_client_unload_game(g_client);
		}
		g_consoleId = RC_CONSOLE_UNKNOWN;
	}

	__declspec(dllexport) void __cdecl MesenRA_DoFrame()
	{
		if(g_client != nullptr && rc_client_is_game_loaded(g_client)) {
			rc_client_do_frame(g_client);
		}
	}

	__declspec(dllexport) void __cdecl MesenRA_Idle()
	{
		if(g_client != nullptr) {
			rc_client_idle(g_client);
		}
	}

	__declspec(dllexport) void __cdecl MesenRA_Reset()
	{
		if(g_client != nullptr) {
			rc_client_reset(g_client);
		}
	}

	__declspec(dllexport) bool __cdecl MesenRA_IsGameLoaded()
	{
		return g_client != nullptr && rc_client_is_game_loaded(g_client) != 0;
	}

	__declspec(dllexport) const char* __cdecl MesenRA_GetLastError()
	{
		return g_lastError.c_str();
	}

	__declspec(dllexport) const char* __cdecl MesenRA_GetGameTitle()
	{
		if(g_client == nullptr) {
			return "";
		}
		const rc_client_game_t* game = rc_client_get_game_info(g_client);
		return game != nullptr && game->title != nullptr ? game->title : "";
	}
}
