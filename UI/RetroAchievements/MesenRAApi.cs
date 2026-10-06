using Mesen.Interop;
using System;
using System.Runtime.InteropServices;

namespace Mesen.RetroAchievements
{
	internal static class MesenRAApi
	{
		private const string DllName = "MesenRA.dll";

		[UnmanagedFunctionPointer(CallingConvention.Cdecl)]
		internal delegate uint ReadMemoryCallback(uint address, IntPtr buffer, uint numBytes);

		[UnmanagedFunctionPointer(CallingConvention.Cdecl)]
		internal delegate void EventCallback(uint type, IntPtr title, IntPtr description, uint points);

		[DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
		[return: MarshalAs(UnmanagedType.I1)]
		internal static extern bool MesenRA_Create(ReadMemoryCallback readMemory, EventCallback eventCallback);

		[DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
		internal static extern void MesenRA_Destroy();

		[DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
		internal static extern void MesenRA_SetHardcore([MarshalAs(UnmanagedType.I1)] bool enabled);

		[DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
		[return: MarshalAs(UnmanagedType.I1)]
		internal static extern bool MesenRA_LoginWithToken(
			[MarshalAs(UnmanagedType.LPUTF8Str)] string username,
			[MarshalAs(UnmanagedType.LPUTF8Str)] string token);

		[DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
		[return: MarshalAs(UnmanagedType.I1)]
		internal static extern bool MesenRA_LoadGame(
			uint consoleId,
			[MarshalAs(UnmanagedType.LPUTF8Str)] string filePath,
			byte[] data,
			UIntPtr dataSize);

		[DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
		internal static extern void MesenRA_UnloadGame();

		[DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
		internal static extern void MesenRA_DoFrame();

		[DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
		internal static extern void MesenRA_Idle();

		[DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
		internal static extern void MesenRA_Reset();

		[DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
		[return: MarshalAs(UnmanagedType.I1)]
		internal static extern bool MesenRA_IsGameLoaded();

		[DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
		private static extern IntPtr MesenRA_GetLastError();

		[DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
		private static extern IntPtr MesenRA_GetGameTitle();

		[DllImport(EmuApi.DllName)]
		[return: MarshalAs(UnmanagedType.I1)]
		internal static extern bool IsDebuggerRunning();

		[DllImport(EmuApi.DllName)]
		internal static extern void InitializeDebugger();

		[DllImport(EmuApi.DllName)]
		internal static extern void ReleaseDebugger();

		internal static string GetLastError() => Marshal.PtrToStringUTF8(MesenRA_GetLastError()) ?? "";
		internal static string GetGameTitle() => Marshal.PtrToStringUTF8(MesenRA_GetGameTitle()) ?? "";
	}
}
