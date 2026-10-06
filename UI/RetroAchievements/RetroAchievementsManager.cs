using Mesen.Config;
using Mesen.Interop;
using System;
using System.IO;
using System.Runtime.InteropServices;

namespace Mesen.RetroAchievements
{
	/// <summary>
	/// Owns the RetroAchievements runtime lifecycle for the standalone MesenCE frontend.
	/// NES is the first supported console in this experimental integration.
	/// </summary>
	public sealed class RetroAchievementsManager : IDisposable
	{
		private const uint RaConsoleNintendo = 7;

		public static RetroAchievementsManager Instance { get; } = new();

		private readonly NotificationListener _notifications;
		private readonly MesenRAApi.ReadMemoryCallback _readMemoryCallback;
		private readonly MesenRAApi.EventCallback _eventCallback;
		private bool _gameLoaded;
		private bool _nativeReady;
		private bool _loggedIn;
		private bool _ownsDebugger;

		private RetroAchievementsManager()
		{
			_readMemoryCallback = ReadMemory;
			_eventCallback = OnRetroAchievementsEvent;
			_notifications = new NotificationListener();
			_notifications.OnNotification += OnNotification;
		}

		private bool Enabled => ConfigManager.Config.RetroAchievements.Enabled;

		private bool EnsureNativeClient()
		{
			if(_nativeReady) {
				return true;
			}

			try {
				// Mesen's MemoryDumper is owned by the debugger. Start it silently if the
				// user has not already opened the debugger so rc_client can read NES RAM.
				if(!MesenRAApi.IsDebuggerRunning()) {
					MesenRAApi.InitializeDebugger();
					_ownsDebugger = true;
				}

				_nativeReady = MesenRAApi.MesenRA_Create(_readMemoryCallback, _eventCallback);
				if(_nativeReady) {
					// Hardcore must stay disabled until save states, rewind and cheats are
					// fully blocked according to RetroAchievements rules.
					MesenRAApi.MesenRA_SetHardcore(false);
				} else if(_ownsDebugger) {
					MesenRAApi.ReleaseDebugger();
					_ownsDebugger = false;
				}
				return _nativeReady;
			} catch(Exception ex) {
				EmuApi.WriteLogEntry("RetroAchievements bridge initialization failed: " + ex.Message);
				if(_ownsDebugger) {
					try { MesenRAApi.ReleaseDebugger(); } catch { }
					_ownsDebugger = false;
				}
				return false;
			}
		}

		private bool EnsureLogin()
		{
			if(_loggedIn) {
				return true;
			}

			RetroAchievementsConfig config = ConfigManager.Config.RetroAchievements;
			if(string.IsNullOrWhiteSpace(config.Username) || string.IsNullOrWhiteSpace(config.Token)) {
				EmuApi.WriteLogEntry("RetroAchievements: username/token not configured.");
				return false;
			}

			MesenRAApi.MesenRA_SetHardcore(false);
			_loggedIn = MesenRAApi.MesenRA_LoginWithToken(config.Username, config.Token);
			if(!_loggedIn) {
				string error = MesenRAApi.GetLastError();
				EmuApi.WriteLogEntry("RetroAchievements login failed: " + error);
			}
			return _loggedIn;
		}

		private void OnNotification(NotificationEventArgs e)
		{
			if(!Enabled && e.NotificationType != ConsoleNotificationType.BeforeGameUnload && e.NotificationType != ConsoleNotificationType.EmulationStopped) {
				return;
			}

			switch(e.NotificationType) {
				case ConsoleNotificationType.GameLoaded:
					OnGameLoaded();
					break;

				case ConsoleNotificationType.PpuFrameDone:
					if(_gameLoaded) {
						MesenRAApi.MesenRA_DoFrame();
					}
					break;

				case ConsoleNotificationType.GamePaused:
					if(_gameLoaded) {
						MesenRAApi.MesenRA_Idle();
					}
					break;

				case ConsoleNotificationType.GameReset:
					if(_gameLoaded) {
						MesenRAApi.MesenRA_Reset();
					}
					break;

				case ConsoleNotificationType.BeforeGameUnload:
				case ConsoleNotificationType.EmulationStopped:
					OnGameUnloaded();
					break;
			}
		}

		private void OnGameLoaded()
		{
			_gameLoaded = false;
			if(!Enabled || !EnsureNativeClient() || !EnsureLogin()) {
				return;
			}

			RomInfo romInfo = EmuApi.GetRomInfo();
			if(romInfo.ConsoleType != ConsoleType.Nes) {
				EmuApi.WriteLogEntry("RetroAchievements: console not supported by the experimental bridge yet: " + romInfo.ConsoleType);
				return;
			}

			if(romInfo.Format != RomFormat.iNes && romInfo.Format != RomFormat.Unif && romInfo.Format != RomFormat.VsSystem && romInfo.Format != RomFormat.VsDualSystem) {
				EmuApi.WriteLogEntry("RetroAchievements: this NES file format is not supported yet: " + romInfo.Format);
				return;
			}

			if(!string.IsNullOrWhiteSpace(romInfo.PatchPath)) {
				EmuApi.WriteLogEntry("RetroAchievements: patched ROMs are not supported yet. Load the unpatched ROM for the first test.");
				return;
			}

			if(!File.Exists(romInfo.RomPath)) {
				EmuApi.WriteLogEntry("RetroAchievements: ROM must currently be a plain file on disk: " + romInfo.RomPath);
				return;
			}

			try {
				byte[] romData = File.ReadAllBytes(romInfo.RomPath);
				_gameLoaded = MesenRAApi.MesenRA_LoadGame(RaConsoleNintendo, romInfo.RomPath, romData, (UIntPtr)romData.Length);
				if(_gameLoaded) {
					string title = MesenRAApi.GetGameTitle();
					EmuApi.WriteLogEntry("RetroAchievements game loaded: " + title);
					EmuApi.DisplayMessage("RetroAchievements", "Connected: " + title);
				} else {
					EmuApi.WriteLogEntry("RetroAchievements game load failed: " + MesenRAApi.GetLastError());
				}
			} catch(Exception ex) {
				EmuApi.WriteLogEntry("RetroAchievements game load exception: " + ex.Message);
			}
		}

		private void OnGameUnloaded()
		{
			if(_nativeReady && _gameLoaded) {
				MesenRAApi.MesenRA_UnloadGame();
			}
			_gameLoaded = false;
		}

		private static uint ReadMemory(uint address, IntPtr buffer, uint numBytes)
		{
			ulong endExclusive = (ulong)address + numBytes;
			if(buffer == IntPtr.Zero || numBytes == 0 || endExclusive > 0x10000UL) {
				return 0;
			}

			try {
				if(!MesenRAApi.IsDebuggerRunning()) {
					return 0;
				}

				byte[] values = DebugApi.GetMemoryValues(MemoryType.NesMemory, address, address + numBytes - 1);
				if(values.Length == 0) {
					return 0;
				}
				Marshal.Copy(values, 0, buffer, values.Length);
				return (uint)values.Length;
			} catch {
				return 0;
			}
		}

		private static void OnRetroAchievementsEvent(uint type, IntPtr titlePtr, IntPtr descriptionPtr, uint points)
		{
			string title = Marshal.PtrToStringUTF8(titlePtr) ?? "";
			string description = Marshal.PtrToStringUTF8(descriptionPtr) ?? "";

			// RC_CLIENT_EVENT_ACHIEVEMENT_TRIGGERED
			if(type == 1 && ConfigManager.Config.RetroAchievements.ShowUnlockNotifications) {
				string message = string.IsNullOrWhiteSpace(description)
					? $"{title} (+{points})"
					: $"{title} (+{points}) - {description}";
				EmuApi.DisplayMessage("Achievement unlocked!", message);
			}
		}

		public void Dispose()
		{
			_notifications.OnNotification -= OnNotification;
			_notifications.Dispose();
			if(_nativeReady) {
				MesenRAApi.MesenRA_Destroy();
				_nativeReady = false;
			}
			if(_ownsDebugger) {
				try { MesenRAApi.ReleaseDebugger(); } catch { }
				_ownsDebugger = false;
			}
		}
	}
}
